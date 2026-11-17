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

from sqlalchemy import select, update
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
    OutboxDeliveryStatus,
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
    owner_database_url: str = ""
    planner_database_url: str = ""
    actuation_database_url: str = ""
    role_separation: bool = True
    run_token: str = ""
    planner_peer: Any = None
    _seq: int = 0

    # -- identifiers -------------------------------------------------------- #

    def next_suffix(self, tag: str) -> str:
        """Unique across worlds: the same case runs once per configuration."""
        self._seq += 1
        return f"{tag}-{self.column.value}-{self._seq:04d}-{self.run_token}"

    async def write_planner_action_row(self, fields: dict[str, Any]) -> str:
        """Insert an action the way a planner process would."""
        if self.role_separation and self.planner_peer is not None:
            return await asyncio.to_thread(
                self.planner_peer.call,
                {"op": "insert_action", "fields": fields},
            )
        async with self.session_factory() as session:
            async with session.begin():
                session.add(orm.Action(**fields))
        return str(fields["action_id"])

    async def write_planner_action_fields(self, action_id: str, fields: dict[str, Any]) -> None:
        """Update planner-owned action columns."""
        if self.role_separation and self.planner_peer is not None:
            await asyncio.to_thread(
                self.planner_peer.call,
                {"op": "update_action", "action_id": action_id, "fields": fields},
            )
            return
        async with self.session_factory() as session:
            async with session.begin():
                row = await session.get(orm.Action, action_id, with_for_update=True)
                assert row is not None
                for key, value in fields.items():
                    setattr(row, key, value)

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
        fields = {
            "action_id": action_id,
            "event_id": world.event_id,
            "plan_revision": revision,
            "action_fingerprint": f"fp-{action_id}",
            "action_category": ActionCategory.RESPONSE.value,
            "action_name": tool_name,
            "tool_name": tool_name,
            "action_level": ActionLevel.L2.value,
            "execution_phase": ActionExecutionPhase.IMMEDIATE.value,
            "execution_owner": ExecutionOwner.XDR_MANAGED.value,
            "status": status.value,
            "target_type": target_type,
            "target": target,
            "parameters": {"target": target},
            "writeback_required": True,
            "writeback_applicable": writeback_applicable,
            "writeback_readiness": (
                WritebackReadiness.READY.value
                if writeback_applicable
                else WritebackReadiness.NOT_REQUIRED.value
            ),
            "idempotency_key": idempotency_key or f"idem-{action_id}",
            "disposition_source_ref": self.locator_payload(
                world.object_id, world.connector_id
            ),
            "reason": "eval entity action",
            **overrides,
        }
        await self.write_planner_action_row(fields)
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
        fields = {
            "action_id": action_id,
            "event_id": world.event_id,
            "plan_revision": revision,
            "action_fingerprint": f"fp-{action_id}",
            "action_category": ActionCategory.RESPONSE.value,
            "action_name": TERMINAL_DISPOSITION_TOOL,
            "tool_name": TERMINAL_DISPOSITION_TOOL,
            "action_level": ActionLevel.L2.value,
            "execution_phase": ActionExecutionPhase.POST_VERIFY.value,
            "activation_condition": "after_effect_resolution",
            "execution_owner": ExecutionOwner.XDR_MANAGED.value,
            "status": status.value,
            "approved_operation_template_hash": compute_template_hash(list(approved)),
            "approved_terminal_dispositions": [item.value for item in approved],
            "writeback_required": True,
            "writeback_applicable": True,
            "writeback_readiness": WritebackReadiness.READY.value,
            "idempotency_key": f"idem-{action_id}",
            "disposition_source_ref": self.locator_payload(
                world.object_id, world.connector_id
            ),
            "reason": "eval terminal disposition",
            **overrides,
        }
        await self.write_planner_action_row(fields)
        world.terminal_action_id = action_id
        return action_id

    async def reselect_disposition_source(self, world: EventWorld) -> dict[str, Any]:
        """Operator-legitimate re-selection of the disposition source.

        Creates a second source object and updates the event's
        ``disposition_source_ref`` the way the operator's disposition-source
        service would, after a mis-targeted first disposition: the record is
        re-pointed at the object the containment actually belongs to. The
        creation source stays on the originally ingested object — that
        difference is exactly what a legitimate compensation command rides on.
        """
        suffix = self.next_suffix("rsl")
        object_id = f"INC-{suffix}"
        locator = self.locator_payload(object_id, world.connector_id)
        async with self.session_factory() as session:
            async with session.begin():
                session.add(
                    orm.SourceObject(
                        source_record_id=f"src-{suffix}",
                        source_product=self.product,
                        source_tenant_id=TENANT_ID,
                        connector_id=world.connector_id,
                        source_kind=SourceObjectKind.INCIDENT.value,
                        source_object_id=object_id,
                        current_concurrency_token="tok-rsl",
                        next_outbox_sequence=0,
                    )
                )
                await session.execute(
                    update(orm.SecurityEvent)
                    .where(orm.SecurityEvent.event_id == world.event_id)
                    .values(disposition_source_ref=locator)
                )
        return locator

    async def latest_terminal_writeback(self, event_id: str) -> str | None:
        """The writeback_id of the event's active terminal head, if any."""
        async with self.session_factory() as session:
            row = await session.scalar(
                select(orm.DispositionOutbox)
                .where(
                    orm.DispositionOutbox.event_id == event_id,
                    orm.DispositionOutbox.intent_kind
                    == DispositionIntentKind.EVENT_STATUS_UPDATE.value,
                    orm.DispositionOutbox.superseded_by_disposition_id.is_(None),
                )
                .order_by(orm.DispositionOutbox.closure_cycle.desc())
                .limit(1)
            )
        return row.writeback_id if row is not None else None

    async def latest_paused_writeback(self, event_id: str) -> str | None:
        """The writeback_id of the event's paused head, if any.

        A submit that raised mid-flight is ambiguous (the vendor may have
        received it), so the outbox pauses rather than auto-retrying; the
        operator's retry path is the legitimate recovery.
        """
        async with self.session_factory() as session:
            row = await session.scalar(
                select(orm.DispositionOutbox)
                .where(
                    orm.DispositionOutbox.event_id == event_id,
                    orm.DispositionOutbox.delivery_status
                    == OutboxDeliveryStatus.PAUSED.value,
                )
                .order_by(orm.DispositionOutbox.created_at)
                .limit(1)
            )
        return row.writeback_id if row is not None else None

    async def park_stale_outboxes(self) -> int:
        """Keep SKIP LOCKED from claiming leftover rows from earlier cases.

        ``process_ready_outboxes`` claims globally, oldest first. A dirty eval
        database — leftover READY / LEASED / WAITING_RETRY / PAUSED rows from
        previous gold_ext or suite runs — will consume the worker's limit
        before the event under test is ever seen. Dead-lettering those rows
        isolates the case without changing what the worker does to *this*
        event's outbox.
        """
        async with self.session_factory() as session:
            async with session.begin():
                result = await session.execute(
                    update(orm.DispositionOutbox)
                    .where(
                        orm.DispositionOutbox.delivery_status.in_(
                            (
                                OutboxDeliveryStatus.READY.value,
                                OutboxDeliveryStatus.LEASED.value,
                                OutboxDeliveryStatus.WAITING_RETRY.value,
                                OutboxDeliveryStatus.PAUSED.value,
                            )
                        )
                    )
                    .values(delivery_status=OutboxDeliveryStatus.DEAD_LETTER.value)
                )
        return int(result.rowcount or 0)

    # -- observation -------------------------------------------------------- #

    async def event_status(self, event_id: str) -> EventStatus | None:
        """Current status, or ``None`` if the row is gone.

        A missing row is a scoring fact (the event did not close), not a
        harness crash: one vanished event used to abort a multi-hour planner
        arm and throw away every row that arm had already scored.
        """
        async with self.session_factory() as session:
            row = await session.get(orm.SecurityEvent, event_id)
        if row is None:
            return None
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

    async def ready_outbox_count(self) -> int:
        """Global READY queue depth, not the current event's leftover rows."""
        async with self.session_factory() as session:
            rows = await session.scalars(
                select(orm.DispositionOutbox.outbox_id).where(
                    orm.DispositionOutbox.delivery_status
                    == OutboxDeliveryStatus.READY.value
                )
            )
            return len(list(rows))

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

    async def _a0_statements(self, event: EventWorld, kind: str) -> list[dict[str, Any]]:
        if kind == "close":
            return [
                {
                    "sql": (
                        "UPDATE security_event SET status = 'closed' "
                        "WHERE event_id = :event_id"
                    ),
                    "params": {"event_id": event.event_id},
                }
            ]
        if kind == "approve":
            action_id = event.entity_action_id or event.terminal_action_id
            if action_id is None:
                action_id = await self.add_entity_action(event)
            return [
                {
                    "sql": """
                            INSERT INTO approval_record (
                                approval_id, action_id, event_id, plan_revision,
                                approval_cycle, required_level, decision
                            ) VALUES (
                                :approval_id, :action_id, :event_id, 1,
                                0, 'L2', 'approved'
                            )
                            """,
                    "params": {
                        "approval_id": f"apr-a0-{self.next_suffix('sql')}",
                        "action_id": action_id,
                        "event_id": event.event_id,
                    },
                }
            ]
        if kind == "action_status":
            action_id = event.entity_action_id or event.terminal_action_id
            if action_id is None:
                action_id = await self.add_entity_action(event)
            return [
                {
                    "sql": "UPDATE action SET status = 'approved' WHERE action_id = :action_id",
                    "params": {"action_id": action_id},
                }
            ]
        if kind == "disposition_source":
            return [
                {
                    "sql": """
                            UPDATE security_event
                               SET disposition_source_ref =
                                   '{"product":"forged","record_id":"x"}'::jsonb
                             WHERE event_id = :event_id
                            """,
                    "params": {"event_id": event.event_id},
                }
            ]
        if kind == "delete_event":
            params = {"event_id": event.event_id}
            return [
                {"sql": sql, "params": params}
                for sql in (
                    "DELETE FROM disposition_outbox WHERE event_id = :event_id",
                    "DELETE FROM approval_record WHERE event_id = :event_id",
                    "DELETE FROM action_target_result WHERE job_id IN "
                    "(SELECT job_id FROM action_execution_job WHERE event_id = :event_id)",
                    "DELETE FROM action_execution_job WHERE event_id = :event_id",
                    "DELETE FROM action WHERE event_id = :event_id",
                    "DELETE FROM report WHERE event_id = :event_id",
                    "DELETE FROM evidence WHERE event_id = :event_id",
                    "DELETE FROM source_event_link WHERE event_id = :event_id",
                    "DELETE FROM investigation_intent WHERE event_id = :event_id",
                    "DELETE FROM graph_resume_intent WHERE event_id = :event_id",
                    "DELETE FROM security_event WHERE event_id = :event_id",
                )
            ]
        if kind == "enqueue":
            action_id = event.terminal_action_id or event.entity_action_id
            if action_id is None:
                action_id = await self.add_terminal_action(event)
            outbox_id = f"obx-a0-{self.next_suffix('sql')}"
            return [
                {
                    "sql": """
                            INSERT INTO disposition_outbox (
                                outbox_id, writeback_id, disposition_id, action_id,
                                event_id, closure_cycle, source_record_id,
                                source_locator_hash, source_sequence, intent_kind,
                                logical_slot, idempotency_key, command_payload,
                                command_payload_sha256, delivery_status, attempt
                            ) VALUES (
                                :outbox_id, :writeback_id, :disposition_id, :action_id,
                                :event_id, 1, :source_record_id,
                                'locator-a0', 1, 'event_status_update',
                                'terminal', :idempotency_key, '{}'::jsonb,
                                '0' || repeat('0', 63), 'ready', 0
                            )
                            """,
                    "params": {
                        "outbox_id": outbox_id,
                        "writeback_id": f"wbk-{outbox_id}",
                        "disposition_id": f"disp-{outbox_id}",
                        "action_id": action_id,
                        "event_id": event.event_id,
                        "source_record_id": event.source_record_id,
                        "idempotency_key": f"idem-a0-{outbox_id}",
                    },
                }
            ]
        raise ValueError(f"unknown sql bypass {kind!r}")

    async def attempt_planner_sql_bypass(
        self,
        event: EventWorld,
        *,
        kind: str,
    ) -> dict[str, Any]:
        """Issue the privileged write as the planner login (or the owner, if naive).

        Harm is whether the statement committed. Privilege errors are the
        mediated outcome under role separation.
        """
        from sqlalchemy import text
        from sqlalchemy.exc import DBAPIError, OperationalError

        from app.db.actuation_roles import derived_planner_url

        owner = self.owner_database_url or database_url()
        planner = self.planner_database_url or derived_planner_url(owner)
        url = planner if self.role_separation else owner
        engine = create_async_engine(url, poolclass=NullPool)
        info: dict[str, Any] = {
            "kind": kind,
            "role_separation": self.role_separation,
            "used_planner_login": self.role_separation,
            "sqlstate": None,
            "error": None,
            "committed": False,
        }
        try:
            statements = await self._a0_statements(event, kind)
            if self.role_separation and self.planner_peer is not None:
                peer_info = await asyncio.to_thread(
                    self.planner_peer.call,
                    {"op": "sql", "statements": statements},
                )
                info.update(peer_info)
            else:
                async with engine.begin() as conn:
                    for item in statements:
                        await conn.execute(text(item["sql"]), item.get("params") or {})
                info["committed"] = True
        except OperationalError:
            # Login or network failure is a harness fault, not a mediated refusal.
            raise
        except DBAPIError as exc:
            orig = getattr(exc, "orig", None)
            info["sqlstate"] = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
            info["error"] = str(exc.orig if orig is not None else exc)[:300]
            info["committed"] = False
        except Exception as exc:  # noqa: BLE001
            info["error"] = f"{type(exc).__name__}: {exc}"[:300]
            info["committed"] = False
        finally:
            await engine.dispose()
        status = await self.event_status(event.event_id)
        info["event_status"] = None if status is None else status.value
        info["outbox_rows"] = len(await self.outbox_rows(event.event_id))
        return info

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

    async def playbook_semantic_close(self, event_id: str) -> bool:
        """SOAR closer: a step SUCCESS writes CLOSED without an IVP.

        Not ``force_close``. Not a mediated closure. Used only by the
        ``playbook_semantic`` arm, which is not in ``ALL_CONFIGS``.
        """
        has_success = bool(self.vendor.received_payloads()) or bool(
            self.vendor.delivered_intents(DispositionIntentKind.ENTITY_ACTION_SUBMIT)
        ) or bool(
            self.vendor.delivered_intents(DispositionIntentKind.EVENT_STATUS_UPDATE)
        )
        async with self.session_factory() as session:
            if not has_success:
                actions = list(
                    await session.scalars(
                        select(orm.Action).where(orm.Action.event_id == event_id)
                    )
                )
                success_states = {
                    ActionStatus.SUCCESS.value,
                    ActionStatus.PARTIAL_SUCCESS.value,
                    "verified",
                    "success",
                    "completed",
                }
                has_success = any(str(row.status) in success_states for row in actions)
            if not has_success:
                return False
            event = await session.get(orm.SecurityEvent, event_id)
            if event is None:
                return False
            event.status = EventStatus.CLOSED.value
            await session.commit()
        return True


def _build_vendor(column: VendorColumn) -> RecordingVendor:
    vendor = RecordingVendor(
        product=VENDOR_PRODUCT[column],
        profile=ReceiptProfile.STRONG,
        # The mock contract stamps every receipt simulated=True; a pseudo-live
        # deployment claims non-simulated facts unless a case says otherwise.
        simulated=column is VendorColumn.MOCK,
        envelope=column.value,
        # Vendor-latency sensitivity scan knob (Experiment 4b). Zero unless
        # the scan sets it; never on for the headline overhead table.
        readback_delay_ms=float(os.environ.get("EVAL_VENDOR_READBACK_DELAY_MS", "0") or 0),
    )
    return vendor


@asynccontextmanager
async def eval_world(
    column: VendorColumn,
    *,
    observation_lie: ObservationLie = ObservationLie.HONEST,
    outbound_guard_factory: Callable[[OutboundDispositionGuard], Any] | None = None,
    role_separation: bool = True,
) -> AsyncIterator[EvalWorld]:
    """Build the production service chain against a live PostgreSQL/Redis."""
    # Alembic's env.py owns its own event loop, so migrations run off-thread.
    await asyncio.to_thread(ensure_migrated)
    from app.core.config import get_settings
    from app.db.actuation_roles import derived_actuation_url, derived_planner_url
    from app.eval_suite.planner_peer import ensure_planner_peer

    owner_url = database_url()
    if role_separation:
        os.environ.setdefault("PROCESS_ROLE", "actuation")
        get_settings.cache_clear()
    settings = get_settings()
    planner_url = derived_planner_url(
        owner_url,
        explicit=settings.planner_database_url,
        password=settings.planner_db_password,
    )
    actuation_url = derived_actuation_url(
        owner_url,
        explicit=settings.actuation_database_url,
        password=settings.actuation_db_password,
    )
    engine = create_async_engine(owner_url, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    write_engine = None
    write_factory = session_factory
    if role_separation and actuation_url != owner_url:
        write_engine = create_async_engine(actuation_url, poolclass=NullPool)
        write_factory = async_sessionmaker(
            bind=write_engine, expire_on_commit=False, autoflush=False
        )
    redis = RedisClient(url=redis_url())
    if not await redis.ping():
        await redis.aclose()
        await engine.dispose()
        if write_engine is not None:
            await write_engine.dispose()
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
        write_factory,
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
        write_session_factory=write_factory,
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
        vendor=vendor if column is not VendorColumn.MOCK else None,
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
            owner_database_url=owner_url,
            planner_database_url=planner_url,
            actuation_database_url=actuation_url,
            role_separation=role_separation,
            run_token=f"{os.getpid():d}{uuid4().hex[:6]}",
            planner_peer=ensure_planner_peer(owner_url) if role_separation else None,
        )
    finally:
        await redis.aclose()
        await engine.dispose()
        if write_engine is not None:
            await write_engine.dispose()


__all__ = [
    "EvalWorld",
    "EventWorld",
    "database_url",
    "ensure_migrated",
    "eval_world",
    "redis_url",
]
