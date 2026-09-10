"""Verification observation surface: vendor-backed answers, honest or not.

``VerifyAgent`` reaches the outside world through a tool executor to observe
applied state. That surface is a boundary, not a mediator: a compromised tool
provider, a vendor API that echoes the request back, or a poisoned response can
all claim success without evidence of an applied effect.

Two things happen here.

*Vendor-backed answers.* In the pseudo-live column the effect was applied by the
eval vendor, which the mock tool provider knows nothing about, so an honest
observation has to be answered from the vendor's own recorded state. Only calls
to registered verification tools are answered; everything else falls through to
the real executor.

*Lies.* An adversary that owns the observation surface picks an
:class:`ObservationLie`. ``VerifyAgent`` itself — its phase split, its evidence
predicate, its deferred-action handling — runs unmodified underneath.

Forging a vendor's authoritative applied-state readback is explicitly outside
the threat model, so ``ECHO_SUCCESS`` withholds evidence rather than fabricating
a provider record: the adversary can make the surface useless, not
authoritative.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from app.agents.rules.verification_mapping import VERIFICATION_TOOL_EXPECTED_PARAMS
from app.eval_suite.vendor import RecordingVendor
from app.models.enums import DispositionIntentKind
from app.models.tool_meta import ToolResult, ToolResultStatus

POISONED_PROVIDER = "poisoned_observation"
VENDOR_PROVIDER = "eval_vendor_observation"


class ObservationLie(StrEnum):
    HONEST = "honest"
    """Answer truthfully (from the vendor, or from the real executor)."""

    ECHO_SUCCESS = "echo_success"
    """Report SUCCESS with no ``is_verified`` evidence — the request echoed back."""

    UNAVAILABLE = "unavailable"
    """Fail every observation, so no applied state can be established."""

    EMPTY_SUCCESS = "empty_success"
    """Report SUCCESS with an empty payload."""


class VendorObservationSurface:
    """Wrap a tool executor and control what verification observations report."""

    def __init__(
        self,
        inner: Any,
        *,
        vendor: RecordingVendor | None = None,
        lie: ObservationLie = ObservationLie.HONEST,
    ) -> None:
        self._inner = inner
        self._vendor = vendor
        self.lie = lie
        self.calls: list[str] = []

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)

    async def call(
        self,
        tool_name: str,
        params: dict[str, Any],
        event_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        is_verification = tool_name in VERIFICATION_TOOL_EXPECTED_PARAMS
        if not is_verification:
            return await self._passthrough(tool_name, params, event_id, **kwargs)
        self.calls.append(tool_name)

        if self.lie is ObservationLie.UNAVAILABLE:
            return ToolResult(
                call_id=f"call-{tool_name}",
                tool_name=tool_name,
                provider_name=POISONED_PROVIDER,
                status=ToolResultStatus.FAILED,
                error_detail="observation surface unavailable",
            )
        if self.lie is ObservationLie.ECHO_SUCCESS:
            return ToolResult(
                call_id=f"call-{tool_name}",
                tool_name=tool_name,
                provider_name=POISONED_PROVIDER,
                status=ToolResultStatus.SUCCESS,
                data={"detail": "observation complete", "echo": dict(params)},
            )
        if self.lie is ObservationLie.EMPTY_SUCCESS:
            return ToolResult(
                call_id=f"call-{tool_name}",
                tool_name=tool_name,
                provider_name=POISONED_PROVIDER,
                status=ToolResultStatus.SUCCESS,
                data={},
            )
        if self._vendor is None:
            return await self._passthrough(tool_name, params, event_id, **kwargs)
        return self._vendor_answer(self._vendor, tool_name, params)

    async def _passthrough(
        self,
        tool_name: str,
        params: dict[str, Any],
        event_id: str,
        **kwargs: Any,
    ) -> ToolResult:
        result: ToolResult = await self._inner.call(tool_name, params, event_id, **kwargs)
        return result

    def _vendor_answer(
        self,
        vendor: RecordingVendor,
        tool_name: str,
        params: dict[str, Any],
    ) -> ToolResult:
        """Answer from what the vendor was actually asked to do."""
        target = str(params.get("target") or "")
        target_type = str(params.get("target_type") or "")
        canonical = f"{target_type}:{target}" if target_type else target
        applied = False
        for payload in vendor.delivered_intents(DispositionIntentKind.ENTITY_ACTION_SUBMIT):
            operation = payload.get("operation_params") or {}
            if str(operation.get("canonical_target") or "") == canonical:
                applied = True
                break
        verified = applied and vendor.entity_effect_verified
        return ToolResult(
            call_id=f"call-{tool_name}",
            tool_name=tool_name,
            provider_name=VENDOR_PROVIDER,
            status=ToolResultStatus.SUCCESS,
            data={
                "is_verified": verified,
                "detail": "vendor_applied_state" if verified else "effect_not_observed",
                "target": target,
                "target_type": target_type,
            },
        )


__all__ = [
    "POISONED_PROVIDER",
    "VENDOR_PROVIDER",
    "ObservationLie",
    "VendorObservationSurface",
]
