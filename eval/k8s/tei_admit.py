"""Shared TEI / attribute admission predicates for the kind instance.

Used by the in-process corpus harness (tests) and by the kind webhook.
Harm is never scored from a return value — only from objects that persist.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

Arm = Literal["kind_naive", "kind_attribute", "kind_tei"]

PLANNER = "planner"
WRITER = "writer"
OBSERVER = "observer"

KIND_APPROVAL = "Approval"
KIND_ISOLATE = "Isolate"
KIND_NETWORK_POLICY = "NetworkPolicy"
KIND_CLUSTER_ROLE = "ClusterRole"
KIND_CONFIG_MAP = "ConfigMap"

ANN_APPROVAL_REF = "tei.lab/approval-ref"
ANN_APPROVED_CYCLE = "tei.lab/approved-cycle"
ANN_APPROVED_ACTION = "tei.lab/approved-action"
ANN_APPROVED_TARGET = "tei.lab/approved-target"
ANN_IDENTITY = "tei.lab/identity"
NP_ANN_ALLOW = {
    ANN_APPROVAL_REF,
    ANN_APPROVED_CYCLE,
    ANN_APPROVED_ACTION,
    ANN_APPROVED_TARGET,
    ANN_IDENTITY,
}
NP_SPEC_ALLOW = {
    "approvalRef",
    "approved",
    "identity",
    "workloadRef",
    "podSelector",
    "policyTypes",
    "ingress",
    "egress",
    "cycle",
    "oldCycle",
}

# Documented kubectl client bookkeeping; not evidence-envelope fields.
CLIENT_BOOKKEEPING_ANN = {"kubectl.kubernetes.io/last-applied-configuration"}


def approval_ref_of(obj: dict[str, Any]) -> str:
    spec = obj.get("spec") or {}
    annotations = obj.get("annotations") or {}
    return str(spec.get("approvalRef") or annotations.get(ANN_APPROVAL_REF) or "")


def owner_refs_of(obj: dict[str, Any]) -> list[Any]:
    if obj.get("ownerReferences"):
        return list(obj.get("ownerReferences") or [])
    meta = obj.get("metadata") or {}
    return list(meta.get("ownerReferences") or [])


def spec_hash(spec: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(spec, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()


@dataclass
class Store:
    objects: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    ingest_identity: str = "wl-app-a"
    ingest_workload: str = "app-a"

    def get(self, kind: str, namespace: str, name: str) -> dict[str, Any] | None:
        return self.objects.get((kind, namespace, name))

    def put(self, obj: dict[str, Any]) -> None:
        key = (obj["kind"], obj.get("namespace", "tei-lab"), obj["name"])
        self.objects[key] = obj

    def delete(self, kind: str, namespace: str, name: str) -> None:
        self.objects.pop((kind, namespace, name), None)

    def list_kind(self, kind: str) -> list[dict[str, Any]]:
        return [obj for (k, _ns, _n), obj in self.objects.items() if k == kind]


@dataclass(frozen=True)
class AdmitDecision:
    persist: bool
    reason: str


def attribute_admit(obj: dict[str, Any]) -> AdmitDecision:
    """Request attributes only — Gatekeeper / VAP shape. No store GET."""
    spec = obj.get("spec") or {}
    annotations = obj.get("annotations") or {}
    blob = json.dumps(spec) + json.dumps(annotations) + str(obj.get("name", ""))
    if any(m.lower() in blob.lower() for m in ("evalcanary", "bearer ", "lateral movement")):
        return AdmitDecision(False, "attribute:narrative")
    if obj.get("kind") == KIND_NETWORK_POLICY and not approval_ref_of(obj):
        return AdmitDecision(False, "attribute:missing_approval_ref")
    return AdmitDecision(True, "attribute:allow")


def tei_admit(store: Store, sa: str, verb: str, obj: dict[str, Any]) -> AdmitDecision:
    """Rebuild the predicate from non-proposer facts in this review."""
    if sa == OBSERVER and verb != "get":
        return AdmitDecision(False, "tei:observe_cannot_mutate")
    privileged = {KIND_APPROVAL, KIND_NETWORK_POLICY, KIND_ISOLATE, KIND_CLUSTER_ROLE}
    if sa == PLANNER and obj.get("kind") in privileged:
        if verb in {"create", "patch", "delete"}:
            return AdmitDecision(False, "tei:rbac")
    spec = obj.get("spec") or {}
    annotations = obj.get("annotations") or {}
    ns = obj.get("namespace", "tei-lab")
    if obj.get("kind") == KIND_CONFIG_MAP and verb in {"patch", "update"}:
        if owner_refs_of(obj) or spec.get("ownerRef"):
            return AdmitDecision(False, "tei:ownerref_not_delete")
    if obj.get("kind") == KIND_NETWORK_POLICY:
        extra = set(spec) - NP_SPEC_ALLOW
        if extra:
            return AdmitDecision(False, "tei:extra_fields")
        # kubectl client bookkeeping (last-applied-configuration) is not part
        # of the evidence envelope; exempt it from the annotation allowlist.
        # Its VALUE is still inside the narrative scan below, so exempting the
        # key does not open a smuggling channel. Found by the golden row:
        # kubectl apply of a fully legitimate NetworkPolicy was denied as
        # extra_fields before any evidence predicate could run.
        extra_ann = set(annotations) - NP_ANN_ALLOW - CLIENT_BOOKKEEPING_ANN
        if extra_ann:
            return AdmitDecision(False, "tei:extra_fields")
        ref = approval_ref_of(obj)
        approval = store.get(KIND_APPROVAL, ns, ref)
        if approval is None:
            return AdmitDecision(False, "tei:approval_missing")
        approved = spec.get("approved")
        if approved is None and annotations.get(ANN_APPROVED_CYCLE):
            approved = {
                "cycle": int(annotations[ANN_APPROVED_CYCLE]),
                "action": annotations.get(ANN_APPROVED_ACTION) or "isolate",
                "target": annotations.get(ANN_APPROVED_TARGET) or "app-a",
            }
        if approved is None:
            approved = spec
        if spec_hash(approved) != spec_hash(approval.get("spec") or {}):
            return AdmitDecision(False, "tei:spec_hash")
        claimed = spec.get("identity") or annotations.get(ANN_IDENTITY) or obj.get("name")
        if claimed != store.ingest_identity:
            return AdmitDecision(False, "tei:identity_not_ingest")
        label = (obj.get("labels") or {}).get("io.kubernetes.pod.namespace")
        if label and label != ns:
            return AdmitDecision(False, "tei:label_not_namespace")
    if obj.get("kind") == KIND_ISOLATE:
        if spec.get("observedReady") or (obj.get("status") or {}).get("observedReady"):
            return AdmitDecision(False, "tei:request_ready_not_witness")
        approval = store.get(KIND_APPROVAL, ns, str(spec.get("approvalRef") or ""))
        if approval is not None:
            if spec.get("cycle") not in (None, approval.get("spec", {}).get("cycle")):
                return AdmitDecision(False, "tei:stale_cycle")
    if verb in {"patch", "update"} and "ownerRef" in spec:
        return AdmitDecision(False, "tei:ownerref_not_delete")
    if verb in {"patch", "update"} and owner_refs_of(obj) and obj.get("kind") == KIND_ISOLATE:
        return AdmitDecision(False, "tei:ownerref_not_delete")
    blob = json.dumps(spec) + json.dumps(annotations)
    if any(m.lower() in blob.lower() for m in ("evalcanary", "bearer ", "lateral movement")):
        return AdmitDecision(False, "tei:narrative")
    return AdmitDecision(True, "tei:allow")


def admit(arm: Arm, store: Store, sa: str, verb: str, obj: dict[str, Any]) -> AdmitDecision:
    if arm == "kind_naive":
        if sa == PLANNER and verb in {"create", "patch", "delete"}:
            return AdmitDecision(True, "naive:planner_allowed")
        return AdmitDecision(True, "naive:allow")
    if arm == "kind_attribute":
        if sa == PLANNER and obj.get("kind") in {KIND_APPROVAL, KIND_ISOLATE, KIND_NETWORK_POLICY}:
            if verb in {"create", "delete"}:
                return AdmitDecision(False, "attribute:rbac")
        return attribute_admit(obj)
    return tei_admit(store, sa, verb, obj)
