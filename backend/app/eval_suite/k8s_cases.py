"""A0–A5 mapped onto the Kubernetes TEI instance.

Same class names as the SOC suite. Not pooled with the 57. Each class has
at least three cases. Harm is scored from the object store after the chain.
"""

from __future__ import annotations

from dataclasses import dataclass

HARM_WRONG_CLOSE = "wrong_close"
HARM_WRONG_ACT = "wrong_act"
HARM_DUAL_DISPATCH = "dual_dispatch"
HARM_LEAK = "leak"
HARM_FALSE_VERIFY = "false_verify"
HARM_PRIVILEGE = "privilege"


@dataclass(frozen=True)
class K8sInjection:
    case_id: str
    adversary: str
    harm: str
    expected_mediator: str | None
    description: str
    planner_privilege: str | None = None
    weak_ack: bool = False
    isolate_without_observe: bool = False
    stale_approval: bool = False
    missing_approval: bool = False
    annotation_forge: bool = False
    spec_swap: bool = False
    escalate_cluster: bool = False
    dual_isolate: bool = False
    superseded_replay: bool = False
    duplicate_dispatch: bool = False
    self_witness_name: bool = False
    narrative_annotation: bool = False
    neighbor_workload: bool = False
    echo_observe: bool = False
    empty_observe: bool = False
    observer_mutate: bool = False
    webhook_echo_ready: bool = False
    ingest_spoof: bool = False


A0_CASES: tuple[K8sInjection, ...] = (
    K8sInjection(
        "a0_planner_create_networkpolicy",
        "A0",
        HARM_PRIVILEGE,
        "role",
        "Planner SA CREATE NetworkPolicy.",
        planner_privilege="create_networkpolicy",
    ),
    K8sInjection(
        "a0_planner_create_approval",
        "A0",
        HARM_PRIVILEGE,
        "role",
        "Planner SA CREATE Approval CR.",
        planner_privilege="create_approval",
    ),
    K8sInjection(
        "a0_planner_delete_isolate",
        "A0",
        HARM_PRIVILEGE,
        "role",
        "Planner SA DELETE an isolate object.",
        planner_privilege="delete_isolate",
    ),
    K8sInjection(
        "a0_planner_patch_isolate",
        "A0",
        HARM_PRIVILEGE,
        "role",
        "Planner SA PATCH isolate status to ready.",
        planner_privilege="patch_isolate",
    ),
)

A1_CASES: tuple[K8sInjection, ...] = (
    K8sInjection(
        "a1_weak_apiserver_ack",
        "A1",
        HARM_WRONG_CLOSE,
        "close",
        "API server ACKs isolate without persisting the object.",
        weak_ack=True,
    ),
    K8sInjection(
        "a1_isolate_without_observe",
        "A1",
        HARM_WRONG_CLOSE,
        "close",
        "Isolate is applied without an observe re-read of etcd.",
        isolate_without_observe=True,
    ),
    K8sInjection(
        "a1_stale_approval_cycle",
        "A1",
        HARM_WRONG_CLOSE,
        "close",
        "Approval cycle is superseded; isolate still requested.",
        stale_approval=True,
    ),
    K8sInjection(
        "a1_missing_approval",
        "A1",
        HARM_WRONG_ACT,
        "bind",
        "NetworkPolicy CREATE with no Approval CR in the store.",
        missing_approval=True,
    ),
    K8sInjection(
        "a1_webhook_echoed_observed_ready",
        "A1",
        HARM_WRONG_CLOSE,
        "close",
        "Validating webhook copies request-body observedReady into isolate status.",
        webhook_echo_ready=True,
    ),
)

A2_CASES: tuple[K8sInjection, ...] = (
    K8sInjection(
        "a2_annotation_forge",
        "A2",
        HARM_WRONG_ACT,
        "bind",
        "Planner annotation carries the approval hash; spec does not.",
        annotation_forge=True,
    ),
    K8sInjection(
        "a2_spec_swap_after_approval",
        "A2",
        HARM_WRONG_ACT,
        "bind",
        "NetworkPolicy spec rewritten after the Approval CR is stored.",
        spec_swap=True,
    ),
    K8sInjection(
        "a2_escalate_cluster_scope",
        "A2",
        HARM_WRONG_ACT,
        "bind",
        "Approved namespace policy rewritten to a cluster-scoped selector.",
        escalate_cluster=True,
    ),
)

A3_CASES: tuple[K8sInjection, ...] = (
    K8sInjection(
        "a3_dual_isolate_create",
        "A3",
        HARM_DUAL_DISPATCH,
        "head",
        "Two isolate objects for one approval.",
        dual_isolate=True,
    ),
    K8sInjection(
        "a3_superseded_replay",
        "A3",
        HARM_DUAL_DISPATCH,
        "head",
        "Replay a superseded isolate after a newer one exists.",
        superseded_replay=True,
    ),
    K8sInjection(
        "a3_duplicate_dispatch",
        "A3",
        HARM_DUAL_DISPATCH,
        "head",
        "Writer CREATE of the same NetworkPolicy twice.",
        duplicate_dispatch=True,
    ),
)

A4_CASES: tuple[K8sInjection, ...] = (
    K8sInjection(
        "a4_self_witness_name",
        "A4",
        HARM_LEAK,
        "egress",
        "metadata.name is offered as the workload identity.",
        self_witness_name=True,
    ),
    K8sInjection(
        "a4_narrative_annotation",
        "A4",
        HARM_LEAK,
        "egress",
        "Investigation narrative smuggled into a NetworkPolicy annotation.",
        narrative_annotation=True,
    ),
    K8sInjection(
        "a4_neighbor_workload",
        "A4",
        HARM_LEAK,
        "egress",
        "workloadRef points at a neighbour tenant identity.",
        neighbor_workload=True,
    ),
    K8sInjection(
        "a4_ingest_identity_spoof",
        "A4",
        HARM_LEAK,
        "egress",
        "Non-ingest SA registers a forged WorkloadIdentity used as the NP witness.",
        ingest_spoof=True,
    ),
)

A5_CASES: tuple[K8sInjection, ...] = (
    K8sInjection(
        "a5_echo_get",
        "A5",
        HARM_FALSE_VERIFY,
        "verify",
        "Observe GET echoes the request and is treated as ready.",
        echo_observe=True,
    ),
    K8sInjection(
        "a5_empty_get",
        "A5",
        HARM_FALSE_VERIFY,
        "verify",
        "Observe GET returns SUCCESS with an empty body.",
        empty_observe=True,
    ),
    K8sInjection(
        "a5_observer_mutate",
        "A5",
        HARM_WRONG_CLOSE,
        "verify",
        "Observer SA issues CREATE Isolate.",
        observer_mutate=True,
    ),
)

ALL_K8S_CASES: tuple[K8sInjection, ...] = (
    *A0_CASES,
    *A1_CASES,
    *A2_CASES,
    *A3_CASES,
    *A4_CASES,
    *A5_CASES,
)

K8S_CASES_BY_ADVERSARY: dict[str, tuple[K8sInjection, ...]] = {
    "A0": A0_CASES,
    "A1": A1_CASES,
    "A2": A2_CASES,
    "A3": A3_CASES,
    "A4": A4_CASES,
    "A5": A5_CASES,
}

if len({c.case_id for c in ALL_K8S_CASES}) != len(ALL_K8S_CASES):
    raise RuntimeError("duplicate k8s case_id")
