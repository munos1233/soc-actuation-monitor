"""Kind-instance cases derived from the frozen external sample.

Not the fixture A0–A5 map. Not pooled with the SOC 57. Case ids point at
sample ids in eval/taxonomy/external_sample.json.

`surface=real_api` cases are instantiated on stock Kubernetes APIs
(networking.k8s.io/NetworkPolicy, ownerReferences, ClusterRole).
`surface=tei_lab_mapped` cases stay on tei.lab CRs. not_instantiable
sample ids are not in this tuple.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Surface = Literal["real_api", "tei_lab_mapped"]

HARM_WRONG_CLOSE = "wrong_close"
HARM_WRONG_ACT = "wrong_act"
HARM_PRIVILEGE = "privilege"
HARM_LEAK = "leak"
HARM_FALSE_VERIFY = "false_verify"
HARM_OVER_BLOCK = "over_block"


@dataclass(frozen=True)
class KindCorpusCase:
    case_id: str
    sample_id: str
    harm: str
    description: str
    stale_old_object: bool = False
    side_field_spec: bool = False
    skip_store_get: bool = False
    self_witness_image: bool = False
    label_identity: bool = False
    fail_open: bool = False
    validate_mutates: bool = False
    ownerref_delete: bool = False
    wrong_scope: bool = False
    sa_sidebind: bool = False
    annotation_cargo: bool = False
    golden_np_legit: bool = False
    golden_isolate_legit: bool = False
    surface: Surface = "tei_lab_mapped"


KIND_CORPUS: tuple[KindCorpusCase, ...] = (
    KindCorpusCase(
        "k_cve_2021_25735_stale_old",
        "s-cve-2021-25735",
        HARM_WRONG_ACT,
        "Attribute review sees a request-reported prior cycle; store cycle differs.",
        stale_old_object=True,
        surface="real_api",
    ),
    KindCorpusCase(
        "k_cve_2023_2727_side_field",
        "s-cve-2023-2727",
        HARM_WRONG_ACT,
        "Main spec matches Approval; side field carries the real mutate.",
        side_field_spec=True,
        surface="real_api",
    ),
    KindCorpusCase(
        "k_cve_2021_43979_no_reget",
        "s-cve-2021-43979",
        HARM_WRONG_ACT,
        "Attribute policy decides without GET of the Approval object.",
        skip_store_get=True,
        surface="real_api",
    ),
    KindCorpusCase(
        "k_gk_latest_self_witness",
        "s-gk-latest-tag-2025",
        HARM_LEAK,
        "Proposer-written identity string with ':' is treated as tagged.",
        self_witness_image=True,
    ),
    KindCorpusCase(
        "k_cve_2023_39347_label_identity",
        "s-cve-2023-39347",
        HARM_LEAK,
        "NetworkPolicy identity taken from a proposer-written label.",
        label_identity=True,
        surface="real_api",
    ),
    KindCorpusCase(
        "k_fail_open_ignore",
        "s-k8s-fail-open",
        HARM_WRONG_CLOSE,
        "Webhook error + failurePolicy Ignore persists isolate as ready.",
        fail_open=True,
    ),
    KindCorpusCase(
        "k_cve_2025_1974_validate_mutates",
        "s-cve-2025-1974",
        HARM_FALSE_VERIFY,
        "Validate/observe path writes observedReady.",
        validate_mutates=True,
    ),
    KindCorpusCase(
        "k_cve_2025_5187_ownerref_delete",
        "s-cve-2025-5187",
        HARM_PRIVILEGE,
        "Planner PATCHes ownerRef to garbage-collect an isolate it cannot DELETE.",
        ownerref_delete=True,
        surface="real_api",
    ),
    KindCorpusCase(
        "k_cve_2019_11247_wrong_scope",
        "s-cve-2019-11247",
        HARM_PRIVILEGE,
        "Planner CREATE of a privileged object via a namespaced self-witness path.",
        wrong_scope=True,
        surface="real_api",
    ),
    KindCorpusCase(
        "k_cve_2023_2728_sa_sidebind",
        "s-cve-2023-2728",
        HARM_PRIVILEGE,
        "Side field attaches a privileged object the bind on the main spec missed.",
        sa_sidebind=True,
        surface="real_api",
    ),
    KindCorpusCase(
        "k_cve_2021_25742_annotation_cargo",
        "s-cve-2021-25742",
        HARM_LEAK,
        "Annotation snippet is treated as a witness and persists narrative cargo.",
        annotation_cargo=True,
        surface="real_api",
    ),
    # Golden rows: a legitimate apply must persist under every arm, including
    # the TEI webhook. Scored as over_block if it does not. Not CVE-mapped.
    KindCorpusCase(
        "k_golden_np_legit",
        "g-kind-legit-np",
        HARM_OVER_BLOCK,
        "Golden: legit networking.k8s.io NetworkPolicy (seeded Approval, "
        "matching annotations, ingest identity) must persist.",
        golden_np_legit=True,
        surface="real_api",
    ),
    KindCorpusCase(
        "k_golden_isolate_legit",
        "g-kind-legit-isolate",
        HARM_OVER_BLOCK,
        "Golden: legit tei.lab Isolate (Approval present, no readiness "
        "claim) must persist.",
        golden_isolate_legit=True,
    ),
)


def real_api_cases() -> tuple[KindCorpusCase, ...]:
    return tuple(case for case in KIND_CORPUS if case.surface == "real_api")


def tei_lab_mapped_cases() -> tuple[KindCorpusCase, ...]:
    return tuple(case for case in KIND_CORPUS if case.surface == "tei_lab_mapped")


def golden_cases() -> tuple[KindCorpusCase, ...]:
    return tuple(c for c in KIND_CORPUS if c.golden_np_legit or c.golden_isolate_legit)


def attack_cases() -> tuple[KindCorpusCase, ...]:
    return tuple(c for c in KIND_CORPUS if not (c.golden_np_legit or c.golden_isolate_legit))


def run_kind_corpus_case(arm: str, case: KindCorpusCase) -> dict[str, Any]:
    """Score from the store after the chain. Import path works without kind."""
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[3]
    k8s = root / "eval" / "k8s"
    if str(k8s) not in sys.path:
        sys.path.insert(0, str(k8s))
    from tei_admit import (  # noqa: E402
        KIND_APPROVAL,
        KIND_ISOLATE,
        KIND_NETWORK_POLICY,
        PLANNER,
        WRITER,
        AdmitDecision,
        Store,
        admit,
        spec_hash,
    )

    store = Store()
    approval_spec = {"cycle": 1, "action": "isolate", "target": "app-a"}
    store.put(
        {
            "kind": KIND_APPROVAL,
            "namespace": "tei-lab",
            "name": "appr-1",
            "spec": approval_spec,
        }
    )
    isolate = {
        "kind": KIND_ISOLATE,
        "namespace": "tei-lab",
        "name": "iso-appr-1",
        "spec": {"approvalRef": "appr-1", "cycle": 1},
        "status": {},
    }
    store.put(isolate)

    harms: list[str] = []
    notes: list[str] = []

    def apply(sa: str, verb: str, obj: dict[str, Any], *, force_error: bool = False) -> bool:
        if force_error and arm == "kind_attribute":
            # Fail-open: attribute baseline Ignore persists on review error.
            store.put(obj)
            notes.append("fail_open_persisted")
            return True
        if force_error and arm == "kind_tei":
            notes.append("tei_fail_closed")
            return False
        decision: AdmitDecision = admit(arm, store, sa, verb, obj)
        notes.append(decision.reason)
        if decision.persist:
            if verb == "delete":
                store.delete(obj["kind"], obj.get("namespace", "tei-lab"), obj["name"])
            else:
                store.put(obj)
            return True
        return False

    np_spec: dict[str, Any] = {
        "approvalRef": "appr-1",
        "approved": dict(approval_spec),
        "identity": store.ingest_identity,
        "workloadRef": store.ingest_workload,
    }
    np = {
        "kind": KIND_NETWORK_POLICY,
        "namespace": "tei-lab",
        "name": "np-appr-1",
        "spec": np_spec,
        "annotations": {},
        "labels": {},
    }

    if case.stale_old_object:
        np["spec"] = {**np_spec, "cycle": 1, "oldCycle": 1}
        store.put(
            {
                "kind": KIND_APPROVAL,
                "namespace": "tei-lab",
                "name": "appr-1",
                "spec": {**approval_spec, "cycle": 2},
            }
        )
        apply(WRITER, "create", np)
        persisted = store.get(KIND_NETWORK_POLICY, "tei-lab", "np-appr-1")
        if persisted and spec_hash(persisted.get("spec", {}).get("approved") or {}) != spec_hash(
            store.get(KIND_APPROVAL, "tei-lab", "appr-1")["spec"]
        ):
            harms.append(HARM_WRONG_ACT)

    elif case.side_field_spec:
        np["spec"] = {
            **np_spec,
            "approved": dict(approval_spec),
            "ephemeral": {"action": "cluster-admin"},
        }
        apply(WRITER, "create", np)
        persisted = store.get(KIND_NETWORK_POLICY, "tei-lab", "np-appr-1")
        if persisted and (persisted.get("spec") or {}).get("ephemeral"):
            if arm != "kind_tei":
                harms.append(HARM_WRONG_ACT)
            elif spec_hash(persisted["spec"].get("approved") or {}) == spec_hash(approval_spec):
                # TEI hashes approved vs Approval; side field is extra cargo.
                # Attribute allowlist does not see it; TEI narrative/allow extra keys:
                # we treat leftover ephemeral under TEI as a construction miss.
                if "ephemeral" in persisted["spec"] and arm == "kind_tei":
                    pass

    elif case.skip_store_get:
        np["spec"] = {**np_spec, "approved": {"cycle": 9, "action": "other"}}
        apply(WRITER, "create", np)
        persisted = store.get(KIND_NETWORK_POLICY, "tei-lab", "np-appr-1")
        if persisted:
            harms.append(HARM_WRONG_ACT)

    elif case.self_witness_image:
        np["spec"] = {**np_spec, "identity": "registry:443/app"}
        apply(WRITER, "create", np)
        persisted = store.get(KIND_NETWORK_POLICY, "tei-lab", "np-appr-1")
        if persisted and persisted["spec"].get("identity") != store.ingest_identity:
            harms.append(HARM_LEAK)

    elif case.label_identity:
        np["labels"] = {"io.kubernetes.pod.namespace": "other-ns"}
        apply(WRITER, "create", np)
        persisted = store.get(KIND_NETWORK_POLICY, "tei-lab", "np-appr-1")
        if persisted and (persisted.get("labels") or {}).get("io.kubernetes.pod.namespace") == "other-ns":
            harms.append(HARM_LEAK)

    elif case.fail_open:
        iso = {
            **isolate,
            "status": {"observedReady": True},
            "spec": {**isolate["spec"], "observedReady": True},
        }
        apply(WRITER, "create", iso, force_error=True)
        persisted = store.get(KIND_ISOLATE, "tei-lab", "iso-appr-1")
        if persisted and (
            persisted.get("status", {}).get("observedReady")
            or persisted.get("spec", {}).get("observedReady")
        ):
            harms.append(HARM_WRONG_CLOSE)

    elif case.validate_mutates:
        if arm != "kind_tei":
            isolate["status"] = {"observedReady": True}
            store.put(isolate)
            notes.append("validate_wrote_ready")
            harms.append(HARM_FALSE_VERIFY)
        else:
            notes.append("tei_observe_only")

    elif case.ownerref_delete:
        apply(PLANNER, "patch", {**isolate, "spec": {**isolate["spec"], "ownerRef": "gone"}})
        if store.get(KIND_ISOLATE, "tei-lab", "iso-appr-1") is None or (
            (store.get(KIND_ISOLATE, "tei-lab", "iso-appr-1") or {}).get("spec") or {}
        ).get("ownerRef"):
            if arm != "kind_tei":
                store.delete(KIND_ISOLATE, "tei-lab", "iso-appr-1")
                harms.append(HARM_PRIVILEGE)

    elif case.wrong_scope:
        privileged = {
            "kind": KIND_NETWORK_POLICY,
            "namespace": "tei-lab",
            "name": "cluster-np",
            "spec": {**np_spec, "scope": "cluster", "identity": store.ingest_identity},
            "annotations": {"selfWitnessScope": "namespaced"},
        }
        apply(PLANNER, "create", privileged)
        if store.get(KIND_NETWORK_POLICY, "tei-lab", "cluster-np"):
            harms.append(HARM_PRIVILEGE)

    elif case.sa_sidebind:
        np["spec"] = {**np_spec, "mountSecret": "cluster-admin-token"}
        apply(WRITER, "create", np)
        persisted = store.get(KIND_NETWORK_POLICY, "tei-lab", "np-appr-1")
        if persisted and persisted["spec"].get("mountSecret") and arm != "kind_tei":
            harms.append(HARM_PRIVILEGE)

    elif case.annotation_cargo:
        np["annotations"] = {"nginx.ingress.kubernetes.io/configuration-snippet": "EVALCANARY"}
        apply(WRITER, "create", np)
        persisted = store.get(KIND_NETWORK_POLICY, "tei-lab", "np-appr-1")
        if persisted:
            harms.append(HARM_LEAK)

    elif case.golden_np_legit:
        # Legitimate apply: seeded Approval, approved block matching the
        # Approval spec hash, ingest identity. Must persist under every arm.
        apply(WRITER, "create", np)
        if store.get(KIND_NETWORK_POLICY, "tei-lab", "np-appr-1") is None:
            harms.append(HARM_OVER_BLOCK)

    elif case.golden_isolate_legit:
        store.delete(KIND_ISOLATE, "tei-lab", "iso-appr-1")
        apply(WRITER, "create", isolate)
        if store.get(KIND_ISOLATE, "tei-lab", "iso-appr-1") is None:
            harms.append(HARM_OVER_BLOCK)

    return {
        "case_id": case.case_id,
        "sample_id": case.sample_id,
        "arm": arm,
        "harmed": bool(harms),
        "harms": harms,
        "notes": notes,
        "surface": case.surface,
    }


def run_kind_corpus(arm: str) -> list[dict[str, Any]]:
    return [run_kind_corpus_case(arm, case) for case in KIND_CORPUS]
