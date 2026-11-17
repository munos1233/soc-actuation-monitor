"""Harness-only mediator mutants. Production neither contains nor imports this.

Eighteen weakenings of TEI predicates, applied with ``unittest.mock.patch``
for the duration of one FULL matrix pass. A mutant is killed when an attack
case that FULL prevents becomes harmed (harm-kill) or a golden case that
FULL closes is refused (over-strict-kill). A3 substrate mechanisms are
intentionally absent: the substrate ablation already speaks for them.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

from sqlalchemy import select

from app.core.errors import ValidationError
from app.models.agent_io import EffectStatus
from app.models.enums import ActionExecutionPhase, ActionStatus, ConfirmationEvidence


@dataclass(frozen=True)
class Mutant:
    mutant_id: str
    family: str
    kind: str
    description: str
    apply: Callable[[], Iterator[None]]
    killers: tuple[str, ...]
    expected_survivor: bool = False


def _bind_planner_fingerprint() -> Iterator[None]:
    from app.core.errors import ValidationError as VE
    from app.eval_monitor import eval_disable_fingerprint_recheck
    from app.services import playbook_approval_binding as binding

    def column_only(action: Any, detail: dict[str, Any] | None) -> None:
        if eval_disable_fingerprint_recheck():
            return
        if not isinstance(detail, dict):
            raise VE("approval binding missing", details={"reason": "binding_detail_missing"})
        bound = detail.get("action_fingerprint")
        if bound != action.action_fingerprint:
            raise VE(
                "approval binding stale: action fingerprint changed",
                details={"reason": "action_fingerprint_mismatch"},
            )

    with patch.object(binding, "_validate_approval_binding", column_only):
        yield


def _bind_partial_fingerprint() -> Iterator[None]:
    from app.agents.response_agent import (
        compute_action_fingerprint,
        compute_source_locator_hash,
    )
    from app.services import playbook_approval_binding as binding

    def partial(action: Any) -> str:
        locator = action.disposition_source_ref
        return compute_action_fingerprint(
            event_id=action.event_id,
            plan_revision=action.plan_revision,
            tool_name=action.tool_name,
            target_type=action.target_type,
            canonical_target=action.target,
            normalized_params_hash="",
            execution_owner=None,
            source_locator_hash=compute_source_locator_hash(locator) if locator else "",
            execution_phase=action.execution_phase,
            approved_template_hash=action.approved_operation_template_hash or "",
            playbook_binding_hash=binding.compute_playbook_binding_hash(
                playbook_ref=action.playbook_ref,
                template_snapshot=action.action_template_snapshot,
            ),
        )

    with patch.object(binding, "recompute_action_content_fingerprint", partial):
        yield


def _close_copy(ctx: Any, **updates: Any) -> Any:
    terminal = ctx.terminal_event_writeback
    if "terminal" in updates:
        terminal = updates.pop("terminal")
        updates["terminal_event_writeback"] = terminal
    return ctx.model_copy(update=updates)


def _close_planner_cycle() -> Iterator[None]:
    from app.models import workflow

    original = workflow._validate_closed_gate

    def wrapped(ctx: Any) -> None:
        terminal = ctx.terminal_event_writeback
        if terminal is not None and ctx.current_plan_revision is not None:
            terminal = terminal.model_copy(update={"plan_revision": ctx.current_plan_revision})
            ctx = _close_copy(ctx, terminal=terminal)
        original(ctx)

    with patch.object(workflow, "_validate_closed_gate", wrapped):
        yield


def _close_skip_report() -> Iterator[None]:
    from app.models import workflow

    original = workflow._validate_closed_gate

    def wrapped(ctx: Any) -> None:
        original(_close_copy(ctx, report_exists=True))

    with patch.object(workflow, "_validate_closed_gate", wrapped):
        yield


def _close_weak_evidence_ok() -> Iterator[None]:
    from app.models import workflow

    original = workflow._validate_closed_gate

    def wrapped(ctx: Any) -> None:
        terminal = ctx.terminal_event_writeback
        if terminal is not None:
            terminal = terminal.model_copy(
                update={"confirmation_evidence": ConfirmationEvidence.READBACK_VERIFIED}
            )
            ctx = _close_copy(ctx, terminal=terminal)
        original(ctx)

    with patch.object(workflow, "_validate_closed_gate", wrapped):
        yield


def _simulated_receipt_ok() -> Iterator[None]:
    from app.models import workflow

    original = workflow._validate_closed_gate

    def wrapped(ctx: Any) -> None:
        terminal = ctx.terminal_event_writeback
        if terminal is not None:
            terminal = terminal.model_copy(update={"simulated": False})
            ctx = _close_copy(ctx, terminal=terminal)
        original(ctx)

    with patch.object(workflow, "_validate_closed_gate", wrapped):
        yield


def _verify_echo_verified() -> Iterator[None]:
    from app.agents import verify_agent as va

    original = va.classify_verification_observation

    def wrapped(data_dict: dict[str, Any], *, action: Any) -> tuple[EffectStatus, str]:
        if "echo" in data_dict or data_dict.get("detail") == "observation complete":
            return EffectStatus.VERIFIED, "effect_verified"
        return original(data_dict, action=action)

    with patch.object(va, "classify_verification_observation", wrapped):
        yield


def _verify_missing_field_verified() -> Iterator[None]:
    from app.agents import verify_agent as va

    original = va.classify_verification_observation

    def wrapped(data_dict: dict[str, Any], *, action: Any) -> tuple[EffectStatus, str]:
        if "is_verified" not in data_dict:
            return EffectStatus.VERIFIED, "effect_verified"
        return original(data_dict, action=action)

    with patch.object(va, "classify_verification_observation", wrapped):
        yield


def _verify_false_negative() -> Iterator[None]:
    from app.agents import verify_agent as va

    original = va.classify_verification_observation

    def wrapped(data_dict: dict[str, Any], *, action: Any) -> tuple[EffectStatus, str]:
        if data_dict.get("is_verified") is False:
            return EffectStatus.VERIFIED, "effect_verified"
        return original(data_dict, action=action)

    with patch.object(va, "classify_verification_observation", wrapped):
        yield


def _egress_self_witness() -> Iterator[None]:
    from app.services import disposition_sync_service as sync

    with patch.object(sync, "_trusted_event_locator", lambda event_row: None):
        yield


def _egress_no_content_scan() -> Iterator[None]:
    from app.core import guardrails

    with patch.object(guardrails, "_scan_analysis_content", lambda *args, **kwargs: []):
        yield


def _template_unchanged_revert() -> Iterator[None]:
    from app.services import event_disposition_service as eds

    with (
        patch.object(eds, "_template_unchanged", lambda action: True),
        patch.object(eds, "validate_approval_binding", lambda action, detail: None),
    ):
        yield


def _locator_creation_source() -> Iterator[None]:
    from app.services import disposition_sync_service as sync

    def creation(event_row: Any) -> dict[str, Any] | None:
        candidate = getattr(event_row, "creation_source_ref", None)
        if isinstance(candidate, dict) and candidate:
            return candidate
        return None

    with patch.object(sync, "_trusted_event_locator", creation):
        yield


def _bind_first_approval() -> Iterator[None]:
    from app.db.orm.approval import ApprovalRecordORM
    from app.services import action_execution_service as aes

    async def earliest(self: Any, session: Any, action_id: str) -> dict[str, Any] | None:
        row = await session.scalar(
            select(ApprovalRecordORM.detail)
            .where(
                ApprovalRecordORM.action_id == action_id,
                ApprovalRecordORM.decided_at.is_not(None),
            )
            .order_by(ApprovalRecordORM.decided_at.asc())
            .limit(1)
        )
        return row if isinstance(row, dict) else None

    with patch.object(aes.ActionExecutionService, "_latest_approval_detail", earliest):
        yield


def _level_first_approval() -> Iterator[None]:
    from app.db.orm.approval import ApprovalRecordORM
    from app.services import action_execution_service as aes

    original = aes.ActionExecutionService._latest_approval_detail

    async def mixed(self: Any, session: Any, action_id: str) -> dict[str, Any] | None:
        latest = await original(self, session, action_id)
        first = await session.scalar(
            select(ApprovalRecordORM.detail)
            .where(
                ApprovalRecordORM.action_id == action_id,
                ApprovalRecordORM.decided_at.is_not(None),
            )
            .order_by(ApprovalRecordORM.decided_at.asc())
            .limit(1)
        )
        if isinstance(latest, dict) and isinstance(first, dict) and first.get("required_level"):
            merged = dict(latest)
            merged["required_level"] = first["required_level"]
            return merged
        return latest

    with patch.object(aes.ActionExecutionService, "_latest_approval_detail", mixed):
        yield


def _one_immediate_action_per_event() -> Iterator[None]:
    from app.db import models as orm
    from app.services import action_execution_service as aes

    original = aes.ActionExecutionService.execute_action

    async def wrapped(self: Any, action_id: str, *, operator: str = "system") -> Any:
        current = await self._load_action(action_id)
        async with self._session_factory() as session:
            rows = list(
                await session.scalars(
                    select(orm.Action).where(orm.Action.event_id == current.event_id)
                )
            )
        taken = [
            row
            for row in rows
            if row.action_id != action_id
            and row.execution_phase == ActionExecutionPhase.IMMEDIATE.value
            and row.status
            in {ActionStatus.EXECUTING.value, ActionStatus.SUCCESS.value}
        ]
        if taken:
            raise ValidationError(
                "one immediate action per event",
                details={"reason": "one_immediate_action_per_event"},
            )
        return await original(self, action_id, operator=operator)

    with patch.object(aes.ActionExecutionService, "execute_action", wrapped):
        yield


def _verify_no_recovery() -> Iterator[None]:
    from app.services import disposition_sync_service as sync

    async def refuse(self: Any, writeback_id: str, **kwargs: Any) -> Any:
        raise ValidationError(
            "writeback recovery disabled",
            details={"reason": "verify_no_recovery", "writeback_id": writeback_id},
        )

    with patch.object(sync.DispositionSyncService, "retry_writeback", refuse):
        yield


def _outbox_no_retry() -> Iterator[None]:
    from app.models.enums import OutboxDeliveryStatus
    from app.services import disposition_sync_service as sync

    original = sync.DispositionSyncService._release_leased_outbox_after_failure

    def dead(self: Any, outbox: Any, **kwargs: Any) -> Any:
        result = original(self, outbox, **kwargs)
        if outbox.delivery_status == OutboxDeliveryStatus.WAITING_RETRY.value:
            outbox.delivery_status = OutboxDeliveryStatus.DEAD_LETTER.value
            outbox.next_retry_at = None
            return OutboxDeliveryStatus.DEAD_LETTER
        return result

    with patch.object(
        sync.DispositionSyncService, "_release_leased_outbox_after_failure", dead
    ):
        yield


MUTANTS: tuple[Mutant, ...] = (
    Mutant(
        "m1_bind_planner_fingerprint",
        "M1",
        "harm",
        "Binding compares the planner-written fingerprint column only.",
        _bind_planner_fingerprint,
        ("a2_target_swap", "a2_tool_escalation", "a2_stale_plan_revision", "a2_level_downgrade"),
    ),
    Mutant(
        "m1_bind_partial_fingerprint",
        "M1",
        "harm",
        "Content hash drops execution_owner and parameters.",
        _bind_partial_fingerprint,
        ("b2_t1b_execution_owner_rewrite",),
    ),
    Mutant(
        "m1_close_planner_cycle",
        "M1",
        "harm",
        "Closure accepts the planner-aligned plan revision on the view.",
        _close_planner_cycle,
        (),
        expected_survivor=True,
    ),
    Mutant(
        "m1_close_skip_report",
        "M1",
        "harm",
        "Closure skips the investigation-report requirement.",
        _close_skip_report,
        ("a1_missing_report",),
    ),
    Mutant(
        "m1_close_weak_evidence_ok",
        "M1",
        "harm",
        "Closure accepts ACK-strength confirmation evidence.",
        _close_weak_evidence_ok,
        ("a1_weak_receipt",),
    ),
    Mutant(
        "m1_simulated_receipt_ok",
        "M1",
        "harm",
        "Closure accepts a simulated receipt on a live writeback path.",
        _simulated_receipt_ok,
        ("a1_simulated_receipt",),
    ),
    Mutant(
        "m1_verify_echo_verified",
        "M1",
        "harm",
        "An observation that only echoes the request counts as verified.",
        _verify_echo_verified,
        ("a5_echo_observation",),
    ),
    Mutant(
        "m1_verify_missing_field_verified",
        "M1",
        "harm",
        "A SUCCESS observation without is_verified counts as verified.",
        _verify_missing_field_verified,
        ("a5_empty_observation",),
    ),
    Mutant(
        "m1_verify_false_negative",
        "M1",
        "harm",
        "is_verified=False is treated as an applied effect.",
        _verify_false_negative,
        ("b2_t6b_honest_negative_observation",),
    ),
    Mutant(
        "m1_egress_self_witness",
        "M1",
        "harm",
        "Object identity is witnessed by the command's own locator.",
        _egress_self_witness,
        ("b2_t4b_pre_approval_locator_swap",),
    ),
    Mutant(
        "m1_egress_no_content_scan",
        "M1",
        "harm",
        "Outbound payloads are not scanned for analysis narrative.",
        _egress_no_content_scan,
        ("a4_narrative_in_target",),
    ),
    Mutant(
        "m1_template_unchanged_revert",
        "M1",
        "harm",
        "Terminal activation skips bind and treats the template hash as tautological.",
        _template_unchanged_revert,
        ("b2_t1a_terminal_template_rewrite",),
    ),
    Mutant(
        "m4_locator_creation_source",
        "M4",
        "over_strict",
        "Object identity is witnessed by the ingest creation source.",
        _locator_creation_source,
        ("g5_compensating_retarget",),
    ),
    Mutant(
        "m4_bind_first_approval",
        "M4",
        "over_strict",
        "Binding compares against the earliest approval, not the latest.",
        _bind_first_approval,
        ("g6_retarget_with_reapproval",),
    ),
    Mutant(
        "m4_level_first_approval",
        "M4",
        "over_strict",
        "Level check compares against the earliest approval's required_level.",
        _level_first_approval,
        ("g11_level_raise_reapproval",),
    ),
    Mutant(
        "m4_one_immediate_action_per_event",
        "M4",
        "over_strict",
        "A second approved immediate action on the same event is refused.",
        _one_immediate_action_per_event,
        ("g7_multi_stage_disposition",),
    ),
    Mutant(
        "m4_verify_no_recovery",
        "M4",
        "over_strict",
        "Operator writeback retry after verification is refused.",
        _verify_no_recovery,
        ("g10_writeback_operator_retry",),
    ),
    Mutant(
        "m4_outbox_no_retry",
        "M4",
        "over_strict",
        "A proven pre-egress transient is dead-lettered instead of retried.",
        _outbox_no_retry,
        ("g9_retry_after_timeout",),
    ),
)

MUTANTS_BY_ID: dict[str, Mutant] = {item.mutant_id: item for item in MUTANTS}

if len(MUTANTS_BY_ID) != 18:  # pragma: no cover - authoring guard
    raise RuntimeError(f"expected 18 mutants, found {len(MUTANTS_BY_ID)}")


@contextmanager
def apply_mutant(mutant: Mutant) -> Iterator[None]:
    yield from mutant.apply()


__all__ = ["MUTANTS", "MUTANTS_BY_ID", "Mutant", "apply_mutant"]
