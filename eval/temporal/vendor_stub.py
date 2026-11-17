"""Vendor stub for the Temporal portability instance.

Runs in the worker process (unsandboxed), shared with the harness for
scoring. Same contract shape as the SOC / kind stubs: submit returns an
adapter acknowledgement; only the read-back carries the evidence class.
"""

from __future__ import annotations


class VendorStub:
    def __init__(self) -> None:
        self.profile = "strong"
        self.submits: list[dict] = []
        self.effect_counts: dict[str, int] = {}

    def reset(self, profile: str = "strong") -> None:
        self.profile = profile
        self.submits = []
        self.effect_counts = {}

    def submit(self, cmd: dict) -> dict:
        payload = cmd["payload"]
        self.submits.append(payload)
        disposition_id = cmd["disposition_id"]
        self.effect_counts[disposition_id] = self.effect_counts.get(disposition_id, 0) + 1
        return {
            "disposition_id": disposition_id,
            "receipt_id": f"rcp-{len(self.submits)}",
            "evidence_class": "adapter_acknowledged",
        }

    def readback(self, disposition_id: str) -> dict:
        # strong: the re-read observes the entity effect -> confirmed.
        # weak_ack: the adapter acknowledged, nothing more (a1_weak_receipt shape).
        evidence = "adapter_acknowledged" if self.profile == "weak_ack" else "confirmed"
        return {"disposition_id": disposition_id, "evidence_class": evidence}


STUB = VendorStub()
