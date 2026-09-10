"""Appendix-only unit checks on the four mediator predicates.

These call gate functions directly with hand-built inputs. That is useful for
one thing and one thing only: showing that each predicate rejects the input it
claims to reject.

It is **not** evidence of mediation, and it must never be presented as the
headline result. A gate function can be perfectly correct and still mediate
nothing if the call chain reaches the vendor without passing through it, or
passes it an attacker-controlled witness. Only the boundary-injection runs in
``app.eval_suite.chain`` can speak to that, because only they read harm from
the database and from what the vendor received.

The paper's ablation table comes from ``app.eval_suite.runner``. This module is
the appendix.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.errors import GuardrailViolationError, ValidationError
from app.core.guardrails import OutboundDispositionGuard
from app.eval_monitor import eval_switch_context
from app.models.action import Action
from app.models.disposition import DispositionCommand, SourceObjectLocator
from app.models.enums import (
    ActionCategory,
    ActionExecutionPhase,
    ActionLevel,
    ActionStatus,
    ExecutionOwner,
    SourceObjectKind,
)
from app.models.ids import new_disposition_id
from app.services.playbook_approval_binding import (
    build_approval_binding_detail,
    validate_approval_binding,
)

_LOCATOR = SourceObjectLocator(
    source_product="mock_xdr",
    source_tenant_id="tenant-component",
    connector_id="conn-component",
    source_kind=SourceObjectKind.INCIDENT,
    source_object_id="INC-component-1",
)


def _action(**overrides: Any) -> Action:
    payload: dict[str, Any] = {
        "action_id": "act-component-1",
        "event_id": "evt-component-1",
        "plan_revision": 1,
        "action_fingerprint": "fp-component-1",
        "action_category": ActionCategory.RESPONSE,
        "action_name": "isolate_host",
        "tool_name": "isolate_host",
        "action_level": ActionLevel.L2,
        "execution_phase": ActionExecutionPhase.IMMEDIATE,
        "execution_owner": ExecutionOwner.XDR_MANAGED,
        "status": ActionStatus.APPROVED,
        "target_type": "host",
        "target": "host-component-1",
        "parameters": {"target": "host-component-1"},
        "disposition_source_ref": _LOCATOR,
    }
    payload.update(overrides)
    return Action(**payload)


def _entity_command(*, target: str) -> DispositionCommand:
    """Build the real outbound envelope through the production factory."""
    from app.models.ids import new_writeback_id
    from app.services.disposition_command_factory import DispositionCommandFactory

    return DispositionCommandFactory().build_entity_action_submit(
        _action(target=target, parameters={"target": target}),
        source_locator=_LOCATOR,
        source_concurrency_token=None,
        operator_id="component-check",
        disposition_id=new_disposition_id(),
        writeback_id=new_writeback_id(),
        closure_cycle=1,
        entity_action_code="isolate_host",
    )


def check_binding_rejects_content_drift() -> dict[str, Any]:
    """The recheck must reject a rewritten action even with a matching label."""
    approved = _action()
    detail = build_approval_binding_detail(approved)
    validate_approval_binding(approved, detail)
    drifted = _action(target="host-attacker", parameters={"target": "host-attacker"})
    try:
        validate_approval_binding(drifted, detail)
    except ValidationError as exc:
        return {
            "check": "binding_rejects_content_drift",
            "rejected": True,
            "reason": (exc.details or {}).get("reason"),
        }
    return {"check": "binding_rejects_content_drift", "rejected": False, "reason": None}


def check_binding_switch_unloads() -> dict[str, Any]:
    """With the switch set, the predicate returns without checking anything."""
    approved = _action()
    detail = build_approval_binding_detail(approved)
    drifted = _action(target="host-attacker", parameters={"target": "host-attacker"})
    with eval_switch_context(
        disable_closed=False,
        disable_bind=True,
        disable_verify=False,
        disable_egress=False,
    ):
        try:
            validate_approval_binding(drifted, detail)
        except ValidationError:
            return {"check": "binding_switch_unloads", "unloaded": False}
    return {"check": "binding_switch_unloads", "unloaded": True}


async def check_guard_blocks_narrative() -> dict[str, Any]:
    """The outbound guard must block analysis narrative in an outbound field."""
    guard = OutboundDispositionGuard()
    command = _entity_command(
        target="host-1 investigation report: lateral movement confirmed",
    )
    try:
        await guard.validate(command, {"event_id": "evt-component-1"})
    except GuardrailViolationError as exc:
        rules = [
            item.get("rule_name")
            for item in (exc.details or {}).get("violations", [])
            if isinstance(item, dict)
        ]
        return {"check": "guard_blocks_narrative", "blocked": True, "rules": rules}
    return {"check": "guard_blocks_narrative", "blocked": False, "rules": []}


async def check_guard_blocks_foreign_locator() -> dict[str, Any]:
    """A command pointed at another object must not match a trusted locator."""
    guard = OutboundDispositionGuard()
    command = _entity_command(target="host-1")
    foreign = _LOCATOR.model_copy(update={"source_object_id": "INC-foreign-9"})
    try:
        await guard.validate(
            command,
            {"event_id": "evt-component-1", "source_locator": foreign},
        )
    except GuardrailViolationError as exc:
        rules = [
            item.get("rule_name")
            for item in (exc.details or {}).get("violations", [])
            if isinstance(item, dict)
        ]
        return {"check": "guard_blocks_foreign_locator", "blocked": True, "rules": rules}
    return {"check": "guard_blocks_foreign_locator", "blocked": False, "rules": []}


def check_verify_switch_flips_deferred_accounting() -> dict[str, Any]:
    """The phase-split switch is what makes a deferred action count as failed."""
    from app.eval_monitor import eval_count_deferred_as_failure

    loaded = eval_count_deferred_as_failure()
    with eval_switch_context(
        disable_closed=False,
        disable_bind=False,
        disable_verify=True,
        disable_egress=False,
    ):
        unloaded = eval_count_deferred_as_failure()
    return {
        "check": "verify_switch_flips_deferred_accounting",
        "with_phase_split": loaded,
        "without_phase_split": unloaded,
    }


async def run_component_checks() -> list[dict[str, Any]]:
    """Run every appendix check. No database, no vendor, no call chain."""
    return [
        check_binding_rejects_content_drift(),
        check_binding_switch_unloads(),
        await check_guard_blocks_narrative(),
        await check_guard_blocks_foreign_locator(),
        check_verify_switch_flips_deferred_accounting(),
    ]


def run_component_checks_sync() -> list[dict[str, Any]]:
    return asyncio.run(run_component_checks())


__all__ = [
    "check_binding_rejects_content_drift",
    "check_binding_switch_unloads",
    "check_guard_blocks_foreign_locator",
    "check_guard_blocks_narrative",
    "check_verify_switch_flips_deferred_accounting",
    "run_component_checks",
    "run_component_checks_sync",
]
