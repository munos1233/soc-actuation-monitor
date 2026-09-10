"""Eval-switch wiring: production defaults stay fail-closed."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.core.config import get_settings
from app.core.errors import GuardrailViolationError, InvalidStateTransitionError, ValidationError
from app.eval_monitor import eval_switch_context
from app.models.action import Action
from app.models.agent_io import EffectStatus
from app.models.enums import (
    ActionCategory,
    ActionExecutionPhase,
    ActionLevel,
    ActionStatus,
    ConfirmationEvidence,
    DispositionPolicy,
    ExecutionOwner,
    WritebackReadiness,
    WritebackStatus,
)
from app.models.side_effect_convergence import SideEffectConvergenceSummary
from app.models.tool_meta import ToolResult, ToolResultStatus
from app.models.workflow import (
    ClosedGateActionView,
    TerminalEventWritebackView,
    TransitionContext,
    validate_closed_gate,
)
from app.services.playbook_approval_binding import (
    build_approval_binding_detail,
    validate_approval_binding,
)
from tests.test_agents.test_verify_agent import (
    FakeTraceService,
    FakeWorkingMemory,
    _action,
    _input,
    _job,
    _mock_executor,
)


def _response_action() -> Action:
    return Action(
        action_id="act-001",
        event_id="evt-001",
        plan_revision=1,
        action_fingerprint="fp-original",
        action_category=ActionCategory.RESPONSE,
        action_name="Block IP",
        tool_name="block_ip",
        action_level=ActionLevel.L2,
        execution_owner=ExecutionOwner.XDR_MANAGED,
    )


def test_eval_switches_default_off() -> None:
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.eval_disable_closed_gate is False
    assert settings.eval_disable_fingerprint_recheck is False
    assert settings.eval_disable_verify_phase_split is False
    assert settings.eval_disable_outbound_guard is False


def _closed_ctx(**overrides: object) -> TransitionContext:
    from app.models.enums import SourceDisposition

    base: dict[str, object] = {
        "disposition_policy": DispositionPolicy.REQUIRED,
        "disposition_is_mock": False,
        "report_exists": False,
        "applicable_required_actions": [
            ClosedGateActionView(
                action_id="act-1",
                action_category=ActionCategory.RESPONSE,
                writeback_required=True,
                writeback_applicable=True,
                writeback_readiness=WritebackReadiness.READY,
                writeback_status=WritebackStatus.CONFIRMED,
                has_command=True,
                all_required_intents_confirmed=True,
                tool_name="block_ip",
            )
        ],
        "terminal_event_writeback": TerminalEventWritebackView(
            action_id="act-disp",
            disposition_id="disp-1",
            writeback_id="wbk-1",
            closure_cycle=1,
            approved_disposition=SourceDisposition.CONTAINED,
            actual_disposition=SourceDisposition.CONTAINED,
            receipt_status=WritebackStatus.CONFIRMED,
            plan_revision=1,
            simulated=False,
            confirmation_evidence=ConfirmationEvidence.READBACK_VERIFIED,
        ),
        "current_plan_revision": 1,
        "current_closure_cycle": 1,
        "side_effect_convergence": SideEffectConvergenceSummary(
            event_id="evt-eval-switch",
            current_plan_revision=1,
        ),
    }
    base.update(overrides)
    return TransitionContext(**base)  # type: ignore[arg-type]


def test_closed_gate_blocks_without_report_by_default() -> None:
    with pytest.raises(InvalidStateTransitionError) as exc:
        validate_closed_gate(_closed_ctx())
    assert exc.value.error_code == "closed_requires_report"


def test_closed_gate_skipped_when_eval_switch_on() -> None:
    with eval_switch_context(disable_closed=True):
        validate_closed_gate(_closed_ctx())


def test_binding_skipped_when_eval_switch_on() -> None:
    action = _response_action()
    detail = build_approval_binding_detail(action)
    mutated = action.model_copy(update={"action_fingerprint": "fp-changed"})
    with pytest.raises(ValidationError):
        validate_approval_binding(mutated, detail)
    with eval_switch_context(disable_bind=True):
        validate_approval_binding(mutated, detail)


@pytest.mark.asyncio
async def test_outbound_guard_skipped_when_eval_switch_on() -> None:
    from app.core.guardrails import OutboundDispositionGuard
    from app.models.disposition import DispositionCommand, SourceObjectLocator
    from app.models.enums import DispositionIntentKind, ExecutionOwner, SourceObjectKind

    locator = SourceObjectLocator(
        source_product="mock_xdr",
        source_tenant_id="t1",
        connector_id="conn-1",
        source_kind=SourceObjectKind.INCIDENT,
        source_object_id="INC-1",
    )
    command = DispositionCommand(
        disposition_id="disp-1",
        action_id="act-1",
        closure_cycle=1,
        intent_kind=DispositionIntentKind.EVENT_STATUS_UPDATE,
        source_locator=locator,
        operation_code="set_event_disposition",
        operation_params={
            "operation_code": "set_event_disposition",
            "target_disposition": "contained",
        },
        operator_id="system",
        idempotency_key="idem-eval-1",
        execution_owner=ExecutionOwner.XDR_MANAGED,
    )
    raw = command.model_dump(mode="python")
    raw["report"] = {"summary": "leak"}
    ctx = {
        "event_id": "evt-out",
        "source_locator": locator,
        "approved_action_ids": {"act-1"},
    }
    with pytest.raises(GuardrailViolationError):
        await OutboundDispositionGuard().validate(raw, ctx)
    with eval_switch_context(disable_egress=True):
        result = await OutboundDispositionGuard().validate(raw, ctx)
    assert result.passed is True


@pytest.mark.asyncio
async def test_verify_deferred_enters_failed_when_split_disabled() -> None:
    from app.agents.verify_agent import VerifyAgent
    from app.models.action import TERMINAL_DISPOSITION_TOOL

    action = _action(
        tool_name=TERMINAL_DISPOSITION_TOOL,
        action_name="terminal_disposition",
        target_type="source_object",
        target="src-1",
        execution_phase=ActionExecutionPhase.POST_VERIFY,
        status=ActionStatus.APPROVED,
        execution_owner=ExecutionOwner.XDR_MANAGED,
        writeback_required=True,
    )
    agent = VerifyAgent(
        working_memory=FakeWorkingMemory(),
        trace_service=FakeTraceService(),
    )
    agent._load_execution_state = AsyncMock(return_value=([action], {}, {}))  # type: ignore[method-assign]
    agent._load_disposition_policy = AsyncMock(  # type: ignore[method-assign]
        return_value=DispositionPolicy.NOT_REQUIRED,
    )
    with eval_switch_context(disable_verify=True):
        result = await agent.execute(_input(event_id=action.event_id, actions=[action]))
    assert result.results[0].effect_status == EffectStatus.FAILED
    assert action.action_id in result.failed_actions
    assert result.results[0].detail == "eval_deferred_counted_as_failed"


@pytest.mark.asyncio
async def test_verify_tool_echo_is_verified_when_split_disabled() -> None:
    from app.agents.verify_agent import VerifyAgent

    action = _action(
        tool_name="block_ip",
        status=ActionStatus.SUCCESS,
        execution_job_id="job-0001",
    )
    job = _job(job_id="job-0001", action_id=action.action_id)
    incomplete = ToolResult(
        call_id="call-00000001",
        tool_name="check_ip_block_status",
        provider_name="mock_observation",
        status=ToolResultStatus.SUCCESS,
        data={"detail": "observation complete"},
    )
    agent = VerifyAgent(
        tool_executor=_mock_executor({"check_ip_block_status": incomplete}),
        working_memory=FakeWorkingMemory(),
        trace_service=FakeTraceService(),
    )
    agent._load_execution_state = AsyncMock(  # type: ignore[method-assign]
        return_value=([action], {"job-0001": job}, {})
    )
    agent._load_disposition_policy = AsyncMock(  # type: ignore[method-assign]
        return_value=DispositionPolicy.NOT_REQUIRED,
    )
    with eval_switch_context(disable_verify=True):
        result = await agent.execute(_input(event_id=action.event_id, actions=[action]))
    assert result.results[0].effect_status == EffectStatus.VERIFIED
    assert result.results[0].detail == "eval_tool_success_echo"
