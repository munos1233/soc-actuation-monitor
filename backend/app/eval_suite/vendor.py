"""In-process vendor stub that records what crossed the boundary.

Two jobs:

1. **Observation.** Every command handed to :meth:`RecordingVendor.submit` is
   recorded verbatim, so egress harm is scored from what the vendor actually
   received — not from whether the outbound guard said "blocked". The canary
   scan is deliberately independent of ``OutboundDispositionGuard``.
2. **Dishonesty.** A vendor may acknowledge without applying, claim success it
   cannot prove, drop the readback, or answer a readback it never performed.
   :class:`ReceiptProfile` selects which of those a case exercises, which is how
   the pseudo-live column pressures the strong-evidence branch of the closure
   gate.

This is a stub, not a vendor integration: no HTTP, no vendor SDK, no credential
handling. Runs made with it must be reported as ``mock`` / ``pseudo_live``
columns and never as a live deployment.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from app.adapters.disposition.base import (
    BaseDispositionAdapter,
    DispositionAdapterCapabilities,
)
from app.models.disposition import (
    DispositionCommand,
    DispositionReceipt,
    EntityEffectCompletion,
    SourceObjectLocator,
    parse_entity_effect_target,
)
from app.models.enums import (
    CapabilityState,
    ConfirmationEvidence,
    ConnectorStatus,
    DispositionIntentKind,
    WritebackStatus,
)

_ALLOWED_OPERATIONS = frozenset(
    {
        "set_event_disposition",
        "submit_entity_action",
        "record_execution_result",
        "record_compensation",
    }
)


class ReceiptProfile(StrEnum):
    """How honest the vendor is about the effect it reports."""

    STRONG = "strong"
    """Applies the change and proves it: CONFIRMED + readback_verified."""

    WEAK_ACK = "weak_ack"
    """Acknowledges receipt only: CONFIRMED + adapter_acknowledged, no readback."""

    SIMULATED_CONFIRM = "simulated_confirm"
    """Claims readback_verified while flagging the result as simulated."""

    DROPPED_READBACK = "dropped_readback"
    """Accepts the submit, then fails every readback attempt."""

    LYING_SUCCESS = "lying_success"
    """Returns CONFIRMED straight from submit without any readback surface."""

    FLAKY_READBACK = "flaky_readback"
    """Loses the readback once; behaves like ``STRONG`` when the caller retries.

    This is not an adversary — it is the benign outage that a golden-path run
    has to survive, and the retry it forces is counted as extra work.
    """


class ReadbackError(RuntimeError):
    """Raised when the vendor refuses or loses the readback."""


class RecordingVendor(BaseDispositionAdapter):
    """Vendor stub with a recorded boundary and a selectable receipt profile."""

    def __init__(
        self,
        *,
        product: str,
        profile: ReceiptProfile = ReceiptProfile.STRONG,
        simulated: bool = True,
        entity_effect_verified: bool = True,
    ) -> None:
        self.name = product
        self.profile = profile
        self.simulated = simulated
        self.entity_effect_verified = entity_effect_verified
        self._default_profile = profile
        self._default_simulated = simulated
        self._default_entity_effect_verified = entity_effect_verified
        self.received: list[dict[str, Any]] = []
        self.submit_calls = 0
        self.readback_calls = 0
        self.replayed_submits = 0
        self._receipts_by_key: dict[str, DispositionReceipt] = {}
        self.tally_sink: Callable[[dict[str, Any]], Awaitable[None]] | None = None
        """Optional out-of-process record of what crossed the boundary.

        ``received`` is per-instance, which is all a single-process run needs. The
        contention probe runs several processes against one database, each with its
        own vendor, so there is no instance to count against; it installs a sink
        here that writes to shared storage. Left ``None`` everywhere else.
        """

    # -- observation ------------------------------------------------------- #

    def reset(self) -> None:
        """Clear recordings and restore this column's honest defaults.

        Cases share one world, so a case that made the vendor lie must not leak
        that behaviour into the next case's rows.
        """
        self.received.clear()
        self.submit_calls = 0
        self.readback_calls = 0
        self.replayed_submits = 0
        self._receipts_by_key.clear()
        self.profile = self._default_profile
        self.simulated = self._default_simulated
        self.entity_effect_verified = self._default_entity_effect_verified

    def received_payloads(self) -> list[dict[str, Any]]:
        return list(self.received)

    def observed_canaries(self, canary: str) -> list[str]:
        """Paths in delivered payloads containing *canary*.

        Independent of the outbound guard: a plain recursive string search over
        what the vendor was handed.
        """
        needle = canary.lower()
        hits: list[str] = []

        def walk(value: Any, path: str) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    walk(item, f"{path}.{key}" if path else str(key))
            elif isinstance(value, (list, tuple)):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")
            elif isinstance(value, str) and needle in value.lower():
                hits.append(path or "<value>")

        for payload in self.received:
            walk(payload, "")
        return hits

    def delivered_intents(self, intent: DispositionIntentKind) -> list[dict[str, Any]]:
        """Distinct external effects of *intent*, one per idempotency key.

        Two submits of the same key are one effect at any vendor that honours the
        key, so counting raw calls here would score a delivery retry as a dual
        dispatch. A genuine second dispatch carries a new key and shows up.
        """
        effects: dict[str, dict[str, Any]] = {}
        for payload in self.received:
            if payload.get("intent_kind") != intent.value:
                continue
            key = str(payload.get("idempotency_key") or id(payload))
            effects.setdefault(key, payload)
        return list(effects.values())

    # -- adapter contract -------------------------------------------------- #

    def capabilities(self) -> DispositionAdapterCapabilities:
        supported = CapabilityState.SUPPORTED
        return DispositionAdapterCapabilities(
            intents={
                DispositionIntentKind.EVENT_STATUS_UPDATE: supported,
                DispositionIntentKind.ENTITY_ACTION_SUBMIT: supported,
                DispositionIntentKind.EXECUTION_RESULT_RECORD: supported,
                DispositionIntentKind.COMPENSATION_RECORD: supported,
            },
            operations={op: supported for op in _ALLOWED_OPERATIONS},
            supports_idempotency=True,
            supports_status_query=False,
            supports_concurrency_token=True,
            supports_lookup_by_idempotency=False,
            supports_readback_confirmation=self.profile not in {ReceiptProfile.LYING_SUCCESS},
            supports_entity_effect_readback=True,
        )

    def validate_command(self, command: DispositionCommand) -> None:
        """Envelope validation only.

        A vendor checks its own schema; it does not know which of our fields
        carry analysis narrative. Keeping this stub free of content inspection
        is what makes the outbound guard the sole mediator for egress cases —
        if the stub also scanned content, an egress result would credit two
        defenses at once.
        """
        DispositionCommand.model_validate(command.model_dump(mode="json"))

    async def submit(self, command: DispositionCommand) -> DispositionReceipt:
        self.submit_calls += 1
        # A vendor that advertises idempotency collapses a replayed key onto the
        # first effect, so a delivery retry must not look like a second action.
        # The payload is still recorded: egress scoring cares about what crossed
        # the wire, not about how many distinct effects it caused.
        payload = command.model_dump(mode="json")
        self.received.append(payload)
        if self.tally_sink is not None:
            await self.tally_sink(payload)
        replayed = self._receipts_by_key.get(command.idempotency_key)
        if replayed is not None:
            self.replayed_submits += 1
            return replayed
        now = datetime.now(UTC)
        base: dict[str, Any] = {
            "writeback_id": f"wbk-{self.name}-{command.disposition_id}",
            "sequence": 1,
            "disposition_id": command.disposition_id,
            "action_id": command.action_id,
            "source_record_id": command.source_locator.source_object_id,
            "submitted_at": now,
            "observed_at": now,
            "simulated": self.simulated,
        }
        if self.profile is ReceiptProfile.LYING_SUCCESS:
            receipt = DispositionReceipt(
                **base,
                status=WritebackStatus.CONFIRMED,
                confirmation_evidence=ConfirmationEvidence.ADAPTER_ACKNOWLEDGED,
                confirmed_at=now,
                provider_code="vendor_claims_applied",
            )
        else:
            receipt = DispositionReceipt(
                **base,
                status=WritebackStatus.ACCEPTED,
                provider_code="accepted",
            )
        self._receipts_by_key[command.idempotency_key] = receipt
        return receipt

    async def confirm_readback(self, command: DispositionCommand) -> DispositionReceipt | None:
        self.readback_calls += 1
        if self.profile in {ReceiptProfile.DROPPED_READBACK, ReceiptProfile.FLAKY_READBACK}:
            raise ReadbackError("vendor readback surface unavailable")
        now = datetime.now(UTC)
        base: dict[str, Any] = {
            "writeback_id": f"wbk-{self.name}-{command.disposition_id}",
            "sequence": 2,
            "disposition_id": command.disposition_id,
            "action_id": command.action_id,
            "source_record_id": command.source_locator.source_object_id,
            "status": WritebackStatus.CONFIRMED,
            "submitted_at": now,
            "observed_at": now,
            "confirmed_at": now,
        }
        if self.profile is ReceiptProfile.WEAK_ACK:
            return DispositionReceipt(
                **base,
                confirmation_evidence=ConfirmationEvidence.ADAPTER_ACKNOWLEDGED,
                simulated=self.simulated,
                provider_code="acknowledged_no_readback",
            )
        if self.profile is ReceiptProfile.SIMULATED_CONFIRM:
            return DispositionReceipt(
                **base,
                confirmation_evidence=ConfirmationEvidence.READBACK_VERIFIED,
                simulated=True,
                provider_code="simulated_readback",
            )
        return DispositionReceipt(
            **base,
            confirmation_evidence=ConfirmationEvidence.READBACK_VERIFIED,
            simulated=self.simulated,
            provider_code="readback_verified",
        )

    async def lookup_submission(
        self,
        idempotency_key: str,
        source_locator: SourceObjectLocator,
    ) -> DispositionReceipt | None:
        _ = (idempotency_key, source_locator)
        return None

    async def read_entity_effect_completion(
        self,
        command: DispositionCommand,
        receipt: DispositionReceipt,
    ) -> EntityEffectCompletion | None:
        entity_action_code = str(getattr(command.operation_params, "entity_action_code", "") or "")
        canonical_target = _canonical_target(command)
        try:
            target_type, target, applied_status = parse_entity_effect_target(
                entity_action_code,
                canonical_target,
            )
        except ValueError:
            return None
        provider_writeback_id = receipt.raw_result.get("provider_writeback_id")
        if not isinstance(provider_writeback_id, str) or not provider_writeback_id:
            provider_writeback_id = receipt.writeback_id
        return EntityEffectCompletion(
            verified=self.entity_effect_verified,
            disposition_id=command.disposition_id,
            writeback_id=receipt.writeback_id,
            provider_writeback_id=provider_writeback_id,
            action_id=command.action_id,
            entity_action_code=entity_action_code,
            canonical_target=canonical_target,
            target_type=target_type,
            target=target,
            applied_status=applied_status if self.entity_effect_verified else "unknown",
            provider_record_id=f"prec-{command.disposition_id}",
            observed_version=1,
            provider_code=(
                "effect_readback_verified" if self.entity_effect_verified else "effect_unverified"
            ),
        )

    async def health_check(self) -> ConnectorStatus:
        return ConnectorStatus.ONLINE


def _canonical_target(command: DispositionCommand) -> str:
    return str(getattr(command.operation_params, "canonical_target", "") or "")


__all__ = ["ReadbackError", "ReceiptProfile", "RecordingVendor"]
