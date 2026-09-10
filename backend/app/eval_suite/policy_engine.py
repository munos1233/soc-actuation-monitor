"""An external policy engine consulted at the four mediation points.

The reviewer's question this answers is the obvious one: the four mediators are
in-system, so how much of their work would an OPA sidecar have done? The arm
turns every internal gate off and consults a real OPA server instead, evaluating
the Rego policy in ``eval/policy/actuation.rego`` at the same four decision
points.

The comparison is deliberately generous to the comparator. OPA is the real
binary, not a re-implementation; the policy is the strongest one we could write
rather than a straw man; and it is consulted synchronously and reliably at each
point, which is better than a sidecar deployment usually manages. What the
comparator does not get is a transaction on the caller's database, because no
sidecar has one. Each decision document therefore carries what the caller can
serialise and send — the action row as it stands, the event as the caller reports
it, the outbound envelope — and not the recorded approval, the writeback head
table, or the vendor's own account of what it applied.

That boundary is the finding, not a limitation of the setup. Where the policy
cannot decide, it is because the fact it would need is one the caller would have
had to be trusted to report.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

DEFAULT_OPA_URL = "http://127.0.0.1:58181/v1/data/shadowtrace/actuation"

DECISION_CLOSE = "close"
DECISION_BIND = "bind"
DECISION_VERIFY = "verify"
DECISION_EGRESS = "egress"


class PolicyEngineUnavailable(RuntimeError):
    """The comparator could not be reached, so the arm cannot be scored."""


@dataclass(frozen=True)
class PolicyDecision:
    """One sidecar answer, with the reasons it gave."""

    decision: str
    allow: bool
    deny: tuple[str, ...]

    @property
    def blocked_error(self) -> str:
        first = self.deny[0] if self.deny else "policy_deny"
        return f"opa_deny:{first}"


def opa_url() -> str:
    return os.environ.get("EVAL_OPA_URL", DEFAULT_OPA_URL)


class ExternalPolicyEngine:
    """Thin client for an OPA server evaluating the comparator policy."""

    def __init__(self, *, url: str | None = None, timeout: float = 5.0) -> None:
        self.url = url or opa_url()
        self._client = httpx.AsyncClient(timeout=timeout)
        self.calls = 0
        self.denials: list[str] = []

    async def aclose(self) -> None:
        await self._client.aclose()

    async def probe(self) -> None:
        """Fail loudly at startup rather than silently allowing every request."""
        try:
            await self.decide(DECISION_EGRESS, {"envelope": {}, "event": {}})
        except PolicyEngineUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001
            raise PolicyEngineUnavailable(str(exc)[:200]) from exc

    async def decide(self, decision: str, document: dict[str, Any]) -> PolicyDecision:
        payload = {"input": {"decision": decision, **document}}
        try:
            response = await self._client.post(self.url, json=payload)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:  # noqa: BLE001 — an unreachable comparator is not an allow
            raise PolicyEngineUnavailable(
                f"OPA at {self.url} did not answer: {type(exc).__name__}: {str(exc)[:120]}"
            ) from exc
        result = body.get("result") or {}
        deny = tuple(sorted(str(item) for item in (result.get("deny") or [])))
        allow = bool(result.get("allow")) and not deny
        self.calls += 1
        if not allow:
            self.denials.extend(deny or ("policy_deny",))
        return PolicyDecision(decision=decision, allow=allow, deny=deny)

    def summary(self) -> dict[str, Any]:
        by_reason: dict[str, int] = {}
        for reason in self.denials:
            by_reason[reason] = by_reason.get(reason, 0) + 1
        return {
            "url": self.url,
            "calls": self.calls,
            "denials": len(self.denials),
            "by_reason": dict(sorted(by_reason.items())),
        }


# --------------------------------------------------------------------------- #
# Decision documents.
#
# Each builder takes only values a caller could serialise and send. Anything the
# caller would have to be trusted about is passed through as the caller reports
# it, which is the whole point of the arm.
# --------------------------------------------------------------------------- #


def bind_document(
    *,
    action: dict[str, Any],
    event_plan_revision: int,
) -> dict[str, Any]:
    return {
        "action": {
            "status": action.get("status"),
            "plan_revision": action.get("plan_revision"),
            "tool_name": action.get("tool_name"),
            "action_level": action.get("action_level"),
            "target": action.get("target"),
            "execution_phase": action.get("execution_phase"),
        },
        "event": {"plan_revision": event_plan_revision},
    }


def close_document(
    *,
    pending_approved_actions: int,
    has_report: bool,
    terminal_writeback_planned: bool,
    disposition_mode: str,
    receipt_simulated: bool,
) -> dict[str, Any]:
    return {
        "event": {
            "pending_approved_actions": pending_approved_actions,
            "has_report": has_report,
            "terminal_writeback_planned": terminal_writeback_planned,
            "disposition_mode": disposition_mode,
            "receipt_simulated": receipt_simulated,
        }
    }


def verify_document(
    *,
    action: dict[str, Any],
    present: bool,
    echoes_request: bool,
    effect_confirmed: bool,
) -> dict[str, Any]:
    return {
        "action": {
            "execution_phase": action.get("execution_phase"),
            "tool_name": action.get("tool_name"),
        },
        "observation": {
            "present": present,
            "echoes_request": echoes_request,
            "effect_confirmed": effect_confirmed,
        },
    }


_LOCATOR_KEYS = ("source_product", "source_tenant_id", "connector_id", "source_object_id")


def _locator(value: Any) -> dict[str, str]:
    dumped = _dump(value)
    return {key: str(dumped.get(key) or "") for key in _LOCATOR_KEYS}


def egress_document(
    *,
    envelope: dict[str, Any],
    trusted_locator: Any | None,
) -> dict[str, Any]:
    """Flatten the outbound envelope the way a sidecar would receive it.

    ``trusted_locator`` is the same value the caller hands the in-system guard as
    ``context["source_locator"]``. The comparator gets it too: withholding it
    would make the comparison unfair for a reason that has nothing to do with
    where the mediator sits.
    """
    params = envelope.get("operation_params")
    params = params if isinstance(params, dict) else {}
    values: list[str] = []
    for value in (*envelope.values(), *params.values()):
        if isinstance(value, str):
            values.append(value)
    canonical_target = str(params.get("canonical_target") or "")
    return {
        "envelope": {
            "fields": sorted(envelope),
            "values": values,
            "canonical_target": canonical_target,
            "source_locator": _locator(envelope.get("source_locator")),
            "locator_supplied": trusted_locator is not None,
        },
        "event": {"trusted_locator": _locator(trusted_locator)},
    }


class PolicyEngineOutboundGuard:
    """Consults the sidecar where the in-system egress guard would have run.

    Wraps the real guard rather than replacing it so the call site is unchanged.
    In the comparator arm the inner guard is unloaded and therefore passes
    everything, which leaves the sidecar as the only thing speaking; in any other
    arm this wrapper is not installed at all.
    """

    def __init__(self, inner: Any, engine: ExternalPolicyEngine) -> None:
        self._inner = inner
        self._engine = engine

    async def validate(
        self,
        payload: Any,
        context: Any | None = None,
    ) -> Any:
        from app.core.errors import GuardrailViolationError

        result = await self._inner.validate(payload, context)
        envelope = payload if isinstance(payload, dict) else _dump(payload)
        ctx = dict(context or {})
        decision = await self._engine.decide(
            DECISION_EGRESS,
            egress_document(envelope=envelope, trusted_locator=ctx.get("source_locator")),
        )
        if not decision.allow:
            raise GuardrailViolationError(
                "external policy engine blocked writeback payload",
                error_code="guardrail_violation",
                details={"rule_name": "external_policy_deny", "deny": list(decision.deny)},
            )
        return result


def _dump(payload: Any) -> dict[str, Any]:
    dumper = getattr(payload, "model_dump", None)
    if dumper is not None:
        dumped = dumper(mode="json")
        if isinstance(dumped, dict):
            return dumped
    return dict(payload) if isinstance(payload, dict) else {}


__all__ = [
    "DECISION_BIND",
    "DECISION_CLOSE",
    "DECISION_EGRESS",
    "DECISION_VERIFY",
    "DEFAULT_OPA_URL",
    "ExternalPolicyEngine",
    "PolicyDecision",
    "PolicyEngineOutboundGuard",
    "PolicyEngineUnavailable",
    "bind_document",
    "close_document",
    "egress_document",
    "opa_url",
    "verify_document",
]
