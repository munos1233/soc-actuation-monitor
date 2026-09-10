"""A real event world in PostgreSQL plus the production service chain.

The services are constructed exactly as ``app.tasks.action_execution_tasks``
builds them for the worker: same classes, same constructor arguments, same
outbound guard. Two things are substituted, and both are boundaries rather than
mediators:

* the disposition adapter, replaced by :class:`~app.eval_suite.vendor.RecordingVendor`
  so the harness can see what crossed the boundary and can make the vendor lie;
* the verification observation surface, optionally wrapped so an observation
  call can echo success it never observed.

Nothing in ``app.eval_suite`` may reach inside a mediator. Attacks write to the
same tables and payloads a compromised planner or vendor could write to, then
the harness asks the database what happened.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.adapters.registry import DispositionAdapterRegistry
from app.core.errors import ShadowTraceError
from app.core.event_bus import EventBus
from app.core.guardrails import OutboundDispositionGuard
from app.core.redis_client import RedisClient
from app.db import models as orm
from app.eval_suite.configs import VENDOR_PRODUCT, VendorColumn
from app.eval_suite.observation import ObservationLie, VendorObservationSurface
from app.eval_suite.vendor import ReceiptProfile, RecordingVendor
from app.models.enums import (
    ActionCategory,
    ActionExecutionPhase,
    ActionLevel,
    ActionStatus,
    DispositionIntentKind,
    DispositionPolicy,
    EventStatus,
    EventType,
    ExecutionOwner,
    FinalVerdict,
    Severity,
    SourceDisposition,
    SourceObjectKind,
    WritebackReadiness,
)
from app.services.action_execution_service import ActionExecutionService
from app.services.agent_trace_service import AgentTraceService
from app.services.context_service import EventContextStore, append_context_journal_in_session
from app.services.decision_record_service import DecisionRecordService
from app.services.degraded_flag_service import create_degraded_flag_service
from app.services.disposition_command_factory import DispositionCommandFactory
from app.services.disposition_sync_service import DispositionSyncService
from app.services.event_audit_log_service import EventAuditLogService
from app.services.event_disposition_service import EventDispositionService
from app.services.state_machine_service import StateMachineService
from app.services.terminal_disposition_resolver import TerminalDispositionResolver
from app.services.working_memory import WorkingMemory
from app.tools.executor import ToolExecutor
from app.tools.registry import ToolRegistry

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = "postgresql+asyncpg://shadowtrace:shadowtrace@localhost:5432/shadowtrace"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"

TENANT_ID = "tenant-eval"
_migrated = False


def database_url() -> str:
    return os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL)


def redis_url() -> str:
    return os.environ.get("REDIS_URL", DEFAULT_REDIS_URL)


def ensure_migrated() -> None:
    """Apply migrations once per process."""
    global _migrated
    if _migrated:
        return
    from alembic import command
    from alembic.config import Config

    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(config, "head")
    _migrated = True


@dataclass
class EventWorld:
    """Identifiers for one seeded event."""

    event_id: str
    source_record_id: str
    connector_id: str
    object_id: str
    plan_revision: int = 1
    entity_action_id: str | None = None
    terminal_action_id: str | None = None
    canary: str = ""
    notes: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalWorld:
    """Production service chain bound to one vendor column."""

    column: VendorColumn
    product: str
    session_factory: async_sessionmaker[AsyncSession]
    redis: RedisClient
    context_store: EventContextStore
    vendor: RecordingVendor
    observation: VendorObservationSurface
    sync: DispositionSyncService
    disposition: EventDispositionService
    state_machine: StateMachineService
    execution: ActionExecutionService
    working_memory: WorkingMemory
    trace_service: AgentTraceService
    command_factory: DispositionCommandFactory
    run_token: str = ""
    _seq: int = 0

    # -- identifiers -------------------------------------------------------- #

    def next_suffix(self, tag: str) -> str:
        """Unique across worlds: the same case runs once per configuration."""
        self._seq += 1
        return f"{tag}-{self.column.value}-{self._seq:04d}-{self.run_token}"

    def locator_payload(self, object_id: str, connector_id: str) -> dict[str, Any]:
        return {
            "source_product": self.product,
            "source_tenant_id": TENANT_ID,
            "connector_id": connector_id,
            "source_kind": SourceObjectKind.INCIDENT.value,
            "source_object_id": object_id,
        }

    # -- seeding ------------------------------------------------------------ #

    async def seed_event(
        self,
        *,
        tag: str = "case",
        disposition_policy: DispositionPolicy = DispositionPolicy.REQUIRED,
        status: EventStatus = EventStatus.REPORTING,
        with_report: bool = True,
        severity: Severity = Severity.HIGH,
        verdict: FinalVerdict = FinalVerdict.CONFIRMED_THREAT,
    ) -> EventWorld:
        """Create an event that has completed analysis and is ready to close."""
        suffix = self.next_suffix(tag)
        event_id = f"evt-{suffix}"
        object_id = f"INC-{suffix}"
        connector_id = f"conn-{suffix}"
        source_record_id = f"src-{suffix}"
        locator = self.locator_payload(object_id, connector_id)

        async with self.session_factory() as session:
            async with session.begin():
                session.add(
                    orm.SourceConnector(
                        connector_id=connector_id,
                        source_product=self.product,
                        display_name=f"{self.product} eval",
                    )
                )
                session.add(
                    orm.SourceObject(
                        source_record_id=source_record_id,
                        source_product=self.product,
                        source_tenant_id=TENANT_ID,
                        connector_id=connector_id,
                        source_kind=SourceObjectKind.INCIDENT.value,
                        source_object_id=object_id,
                        current_concurrency_token="tok-1",
                        next_outbox_sequence=0,
                    )
                )
                session.add(
                    orm.SecurityEvent(
                        event_id=event_id,
                        event_type=EventType.DATA_EXFILTRATION.value,
                        title=f"actuation-integrity eval {suffix}",
                        description="",
                        status=status.value,
                        severity=severity.value,
                        risk_score=85,
                        confidence=0.9,
                        final_verdict=verdict.value,
                        disposition_policy=disposition_policy.value,
                        creation_source_ref=locator,
                        disposition_source_ref=locator,
                        source_type=self.product,
                        occurred_at=datetime.now(UTC),
                    )
                )
            if with_report:
                async with session.begin():
                    session.add(
                        orm.Report(
                            report_id=f"rpt-{suffix}",
                            event_id=event_id,
                            title="eval report",
                            summary="analysis completed",
                            sections=[],
                            final_verdict=verdict.value,
                            risk_score=85,
                            severity=severity.value,
                        )
                    )
            async with session.begin():
                await append_context_journal_in_session(
                    session,
                    event_id,
                    "triage_result",
                    {
                        "event_type": EventType.DATA_EXFILTRATION.value,
                        "severity": severity.value,
                        "need_investigation": True,
                        "confidence": 0.9,
                        "reasoning": "eval world",
                    },
                )

        await DecisionRecordService(self.session_factory).persist_from_agent_trace(
            event_id=event_id,
            agent_name="triage_agent",
            trace_id=f"trc-{suffix}",
            input_data={"event_id": event_id},
            output_data={"reasoning": "eval world"},
        )
        return EventWorld(
            event_id=event_id,
            source_record_id=source_record_id,
            connector_id=connector_id,
            object_id=object_id,
        )

    async def add_entity_action(
        self,
        world: EventWorld,
        *,
        tool_name: str = "isolate_host",
        target_type: str = "host",
        target: str = "host-eval-1",
        status: ActionStatus = ActionStatus.APPROVED,
        plan_revision: int | None = None,
        writeback_applicable: bool = False,
        idempotency_key: str | None = None,
        **overrides: Any,
    ) -> str:
        """Insert an approved IMMEDIATE entity action (the side effect)."""
        revision = plan_revision or world.plan_revision
        action_id = f"act-ent-{self.next_suffix('a')}"
        async with self.session_factory() as session:
            async with session.begin():
                session.add(
                    orm.Action(
                        action_id=action_id,
                        event_id=world.event_id,
                        plan_revision=revision,
                        action_fingerprint=f"fp-{action_id}",
                        action_category=ActionCategory.RESPONSE.value,
                        action_name=tool_name,
                        tool_name=tool_name,
                        action_level=ActionLevel.L2.value,
                        execution_phase=ActionExecutionPhase.IMMEDIATE.value,
                        execution_owner=ExecutionOwner.XDR_MANAGED.value,
                        status=status.value,
                        target_type=target_type,
                        target=target,
                        parameters={"target": target},
                        writeback_required=True,
                        writeback_applicable=writeback_applicable,
                        writeback_readiness=(
                            WritebackReadiness.READY.value
                            if writeback_applicable
                            else WritebackReadiness.NOT_REQUIRED.value
                        ),
                        idempotency_key=idempotency_key or f"idem-{action_id}",
                        disposition_source_ref=self.locator_payload(
                            world.object_id, world.connector_id
                        ),
                        reason="eval entity action",
                        **overrides,
                    )
                )
        world.entity_action_id = action_id
        return action_id

    async def add_terminal_action(
        self,
        world: EventWorld,
        *,
        approved: tuple[SourceDisposition, ...] = (
            SourceDisposition.CONTAINED,
            SourceDisposition.COMPLETED,
        ),
        status: ActionStatus = ActionStatus.APPROVED,
        plan_revision: int | None = None,
        **overrides: Any,
    ) -> str:
        """Insert the deferred POST_VERIFY terminal disposition action."""
        from app.agents.response_agent import compute_template_hash
        from app.models.action import TERMINAL_DISPOSITION_TOOL

        revision = plan_revision or world.plan_revision
        action_id = f"act-term-{self.next_suffix('t')}"
        async with self.session_factory() as session:
            async with session.begin():
                session.add(
                    orm.Action(
                        action_id=action_id,
                        event_id=world.event_id,
                        plan_revision=revision,
                        action_fingerprint=f"fp-{action_id}",
                        action_category=ActionCategory.RESPONSE.value,
                        action_name=TERMINAL_DISPOSITION_TOOL,
                        tool_name=TERMINAL_DISPOSITION_TOOL,
                        action_level=ActionLevel.L2.value,
                        execution_phase=ActionExecutionPhase.POST_VERIFY.value,
                        activation_condition="after_effect_resolution",
                        execution_owner=ExecutionOwner.XDR_MANAGED.value,
                        status=status.value,
                        approved_operation_template_hash=compute_template_hash(list(approved)),
                        approved_terminal_dispositions=[item.value for item in approved],
                        writeback_required=True,
                        writeback_applicable=True,
                        writeback_readiness=WritebackReadiness.READY.value,
                        idempotency_key=f"idem-{action_id}",
                        disposition_source_ref=self.locator_payload(
                            world.object_id, world.connector_id
                        ),
                        reason="eval terminal disposition",
                        **overrides,
                    )
                )
        world.terminal_action_id = action_id
        return action_id

    # -- observation -------------------------------------------------------- #

    async def event_status(self, event_id: str) -> EventStatus:
        async with self.session_factory() as session:
            row = await session.get(orm.SecurityEvent, event_id)
            assert row is not None
            return EventStatus(row.status)

    async def is_closed(self, event_id: str) -> bool:
        return await self.event_status(event_id) is EventStatus.CLOSED

    async def external_unsynced(self, event_id: str) -> bool:
        async with self.session_factory() as session:
            row = await session.get(orm.SecurityEvent, event_id)
            return bool(row is not None and getattr(row, "external_unsynced", False))

    async def outbox_rows(self, event_id: str) -> list[orm.DispositionOutbox]:
        async with self.session_factory() as session:
            return list(
                await session.scalars(
                    select(orm.DispositionOutbox)
                    .where(orm.DispositionOutbox.event_id == event_id)
                    .order_by(orm.DispositionOutbox.created_at)
                )
            )

    async def active_terminal_heads(self, event_id: str) -> int:
        """How many terminal writeback heads currently claim to be the active one.

        The schema admits one per (event, closure cycle). Two is the integrity
        violation itself, whether or not the vendor's own key deduplication
        happens to absorb the second delivery — and the key is planner-written,
        so that absorption is not something the system may rely on.
        """
        async with self.session_factory() as session:
            rows = await session.scalars(
                select(orm.DispositionOutbox.outbox_id).where(
                    orm.DispositionOutbox.event_id == event_id,
                    orm.DispositionOutbox.intent_kind
                    == DispositionIntentKind.EVENT_STATUS_UPDATE.value,
                    orm.DispositionOutbox.superseded_by_disposition_id.is_(None),
                )
            )
            return len(list(rows))

    async def head_delivery_status(self, outbox_id: str) -> str:
        """The delivery state of one specific head.

        Asking about one head rather than counting superseded-and-delivered rows
        for the event: writing a corrected terminal disposition is legal, so a
        head delivered while it was current and superseded afterwards is not a
        stale write. Only the caller knows which head it meant to be the stale
        one, so only the caller can score it.
        """
        async with self.session_factory() as session:
            row = await session.get(orm.DispositionOutbox, outbox_id)
            return "missing" if row is None else str(row.delivery_status)

    async def receipts(self, event_id: str) -> list[orm.DispositionReceipt]:
        async with self.session_factory() as session:
            return list(
                await session.scalars(
                    select(orm.DispositionReceipt)
                    .join(
                        orm.DispositionOutbox,
                        orm.DispositionOutbox.writeback_id == orm.DispositionReceipt.writeback_id,
                    )
                    .where(orm.DispositionOutbox.event_id == event_id)
                    .order_by(orm.DispositionReceipt.sequence)
                )
            )

    async def action_row(self, action_id: str) -> orm.Action | None:
        async with self.session_factory() as session:
            return await session.get(orm.Action, action_id)

    async def pending_approved_actions(self, event_id: str) -> int:
        """Approved immediate actions nobody has run yet.

        Deferred (``post_verify``) actions are excluded: the terminal writeback is
        activated by closure, so counting it here would make every close look
        unfinished. Facts a caller can serialise, which is why the comparator arm
        is allowed to use them.
        """
        async with self.session_factory() as session:
            rows = list(
                await session.scalars(
                    select(orm.Action.action_id).where(
                        orm.Action.event_id == event_id,
                        orm.Action.status == ActionStatus.APPROVED.value,
                        orm.Action.execution_phase != ActionExecutionPhase.POST_VERIFY.value,
                    )
                )
            )
        return len(rows)

    async def terminal_writeback_planned(self, event_id: str) -> bool:
        """Is a terminal writeback action on the plan for this event.

        The strongest terminal-writeback question a sidecar can be asked before
        the close it is gating: the head itself does not exist yet, because
        closure is what enqueues it. What the head *becomes* at delivery — active
        or superseded — is not visible from outside the caller's transaction,
        which is the boundary the comparator arm exists to measure.
        """
        async with self.session_factory() as session:
            rows = list(
                await session.scalars(
                    select(orm.Action.action_id).where(
                        orm.Action.event_id == event_id,
                        orm.Action.execution_phase == ActionExecutionPhase.POST_VERIFY.value,
                    )
                )
            )
        return bool(rows)

    # -- driving the chain -------------------------------------------------- #

    async def attempt_close(self, event_id: str, *, operator: str = "eval-harness") -> str | None:
        """Try the only legal path into CLOSED.

        Returns ``None`` when the event closed, otherwise the mediator's error
        code (or exception class name when the error carries no code).
        """
        try:
            await self.state_machine.transition(
                event_id,
                EventStatus.CLOSED,
                operator=operator,
                reason="eval:attempt_close",
            )
        except ShadowTraceError as exc:
            return getattr(exc, "error_code", None) or type(exc).__name__
        except Exception as exc:  # noqa: BLE001 - harness records, never swallows silently
            return type(exc).__name__
        return None


def _build_vendor(column: VendorColumn) -> RecordingVendor:
    return RecordingVendor(
        product=VENDOR_PRODUCT[column],
        profile=ReceiptProfile.STRONG,
        # The mock contract stamps every receipt simulated=True; a pseudo-live
        # deployment claims non-simulated facts unless a case says otherwise.
        simulated=column is VendorColumn.MOCK,
    )


@asynccontextmanager
async def eval_world(
    column: VendorColumn,
    *,
    observation_lie: ObservationLie = ObservationLie.HONEST,
    outbound_guard_factory: Callable[[OutboundDispositionGuard], Any] | None = None,
) -> AsyncIterator[EvalWorld]:
    """Build the production service chain against a live PostgreSQL/Redis."""
    # Alembic's env.py owns its own event loop, so migrations run off-thread.
    await asyncio.to_thread(ensure_migrated)
    engine = create_async_engine(database_url(), poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    redis = RedisClient(url=redis_url())
    if not await redis.ping():
        await redis.aclose()
        await engine.dispose()
        raise RuntimeError("Redis is required for the actuation-integrity suite")

    context_store = EventContextStore(redis, session_factory)
    degraded = create_degraded_flag_service(context_store, session_factory)
    audit = EventAuditLogService(session_factory)
    event_bus = EventBus(redis)
    vendor = _build_vendor(column)
    registry = DispositionAdapterRegistry()
    registry.register(vendor.name, vendor)
    command_factory = DispositionCommandFactory()

    # The comparator arm substitutes a wrapper here rather than editing the
    # service: the call site, its arguments and its failure mode stay exactly
    # what production uses.
    guard: Any = OutboundDispositionGuard()
    if outbound_guard_factory is not None:
        guard = outbound_guard_factory(guard)
    sync = DispositionSyncService(
        session_factory,
        context_store=context_store,
        adapter_registry=registry,
        command_factory=command_factory,
        outbound_guard=guard,
        event_bus=event_bus,
    )
    state_machine = StateMachineService(
        session_factory,
        context_store,
        audit_log=audit,
        degraded_flags=degraded,
    )
    disposition = EventDispositionService(
        session_factory,
        disposition_sync=sync,
        context_store=context_store,
        resolver=TerminalDispositionResolver(),
        factory=command_factory,
        event_bus=event_bus,
        event_disposition_supported=True,
        decision_record_service=DecisionRecordService(session_factory),
    )
    tool_registry = ToolRegistry()
    await tool_registry.auto_discover_for_mode(
        tool_mode="mock",
        adapters=(),
        simulation_enabled=True,
        allow_live_side_effects=False,
    )
    # Mock column: the mock tool provider observes the mock XDR state that the
    # mock adapter contract writes, so honest observation needs no help.
    # Pseudo-live column: the effect lives in the eval vendor, which the mock
    # tools cannot see, so honest observation is answered from vendor state.
    observation = VendorObservationSurface(
        ToolExecutor(registry=tool_registry),
        vendor=vendor if column is VendorColumn.PSEUDO_LIVE else None,
        lie=observation_lie,
    )
    tool_executor: Any = observation
    execution = ActionExecutionService(
        session_factory,
        disposition_sync=sync,
        tool_executor=tool_executor,
        state_machine=state_machine,
        context_store=context_store,
        command_factory=command_factory,
        event_bus=event_bus,
    )
    working_memory = WorkingMemory(
        store=context_store,
        redis=redis,
        degraded_flags=degraded,
    )
    try:
        yield EvalWorld(
            column=column,
            product=vendor.name,
            session_factory=session_factory,
            redis=redis,
            context_store=context_store,
            vendor=vendor,
            observation=observation,
            sync=sync,
            disposition=disposition,
            state_machine=state_machine,
            execution=execution,
            working_memory=working_memory,
            trace_service=AgentTraceService(session_factory),
            command_factory=command_factory,
            run_token=f"{os.getpid():d}{uuid4().hex[:6]}",
        )
    finally:
        await redis.aclose()
        await engine.dispose()


__all__ = [
    "EvalWorld",
    "EventWorld",
    "database_url",
    "ensure_migrated",
    "eval_world",
    "redis_url",
]
