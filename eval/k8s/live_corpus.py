"""Apply kind-corpus objects and score from kubectl get. Never from HTTP allow."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.eval_suite.kind_corpus import (  # noqa: E402
    HARM_FALSE_VERIFY,
    HARM_LEAK,
    HARM_OVER_BLOCK,
    HARM_PRIVILEGE,
    HARM_WRONG_ACT,
    HARM_WRONG_CLOSE,
    KIND_CORPUS,
    KindCorpusCase,
)
from tei_admit import (  # noqa: E402
    ANN_APPROVAL_REF,
    ANN_APPROVED_ACTION,
    ANN_APPROVED_CYCLE,
    ANN_APPROVED_TARGET,
    ANN_IDENTITY,
)

NS = "tei-lab"
INGEST_IDENTITY = "wl-app-a"
# Provenance label for rows; hosted-cluster runs set TEI_K8S_METHOD_LABEL.
METHOD = os.environ.get("TEI_K8S_METHOD_LABEL", "").strip() or "kind_cluster"


def _run(args: list[str], *, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, check=check)


def kubectl(*args: str, as_sa: str | None = None) -> subprocess.CompletedProcess[str]:
    cmd = ["kubectl", *args]
    if as_sa:
        cmd = ["kubectl", f"--as=system:serviceaccount:{NS}:{as_sa}", *args]
    return _run(cmd)


def apply_doc(doc: dict[str, Any], *, as_sa: str | None = None) -> bool:
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as handle:
        handle.write(json.dumps(doc))
        path = handle.name
    proc = kubectl("apply", "-f", path, as_sa=as_sa)
    Path(path).unlink(missing_ok=True)
    return proc.returncode == 0


def get_obj(resource: str, name: str) -> dict[str, Any] | None:
    proc = kubectl("get", resource, name, "-n", NS, "-o", "json")
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def delete_all() -> None:
    for resource in (
        "networkpolicies.networking.k8s.io",
        "networkpolicies.tei.lab",
        "isolates.tei.lab",
        "approvals.tei.lab",
        "configmap/iso-witness",
    ):
        if "/" in resource:
            kubectl("delete", resource, "-n", NS, "--ignore-not-found")
        else:
            kubectl("delete", resource, "--all", "-n", NS, "--ignore-not-found")
    kubectl("delete", "clusterrole", "cluster-np-priv", "--ignore-not-found")


def seed_approval(*, cycle: int = 1) -> None:
    apply_doc(
        {
            "apiVersion": "tei.lab/v1",
            "kind": "Approval",
            "metadata": {"name": "appr-1", "namespace": NS},
            "spec": {"cycle": cycle, "action": "isolate", "target": "app-a"},
        }
    )


def _np(
    name: str,
    spec: dict[str, Any],
    *,
    annotations: dict[str, str] | None = None,
    labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {"name": name, "namespace": NS}
    if annotations:
        meta["annotations"] = annotations
    if labels:
        meta["labels"] = labels
    return {
        "apiVersion": "tei.lab/v1",
        "kind": "NetworkPolicy",
        "metadata": meta,
        "spec": spec,
    }


def _isolate(spec: dict[str, Any], status: dict[str, Any] | None = None) -> dict[str, Any]:
    doc: dict[str, Any] = {
        "apiVersion": "tei.lab/v1",
        "kind": "Isolate",
        "metadata": {"name": "iso-appr-1", "namespace": NS},
        "spec": spec,
    }
    if status:
        doc["status"] = status
    return doc


def bind_planner_naive(on: bool) -> None:
    if on:
        apply_doc(
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": {"name": "planner-naive", "namespace": NS},
                "subjects": [
                    {
                        "kind": "ServiceAccount",
                        "name": "planner",
                        "namespace": NS,
                    }
                ],
                "roleRef": {
                    "kind": "Role",
                    "name": "planner-naive",
                    "apiGroup": "rbac.authorization.k8s.io",
                },
            }
        )
        apply_doc(
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRoleBinding",
                "metadata": {"name": "planner-naive-cluster"},
                "subjects": [
                    {
                        "kind": "ServiceAccount",
                        "name": "planner",
                        "namespace": NS,
                    }
                ],
                "roleRef": {
                    "kind": "ClusterRole",
                    "name": "planner-naive-cluster",
                    "apiGroup": "rbac.authorization.k8s.io",
                },
            }
        )
    else:
        kubectl("delete", "rolebinding", "planner-naive", "-n", NS, "--ignore-not-found")
        kubectl("delete", "clusterrolebinding", "planner-naive-cluster", "--ignore-not-found")


def set_tei_webhook(on: bool) -> None:
    override = os.environ.get("TEI_K8S_WEBHOOK_MANIFEST", "").strip()
    generated = ROOT / "eval" / "k8s" / "webhook" / "webhook.generated.yaml"
    src = ROOT / "eval" / "k8s" / "webhook" / "webhook.yaml"
    if on:
        if override:
            kubectl("apply", "-f", override)
        elif generated.is_file():
            kubectl("apply", "-f", str(generated))
        else:
            kubectl("apply", "-f", str(src))
    else:
        kubectl("delete", "validatingwebhookconfiguration", "tei-evidence", "--ignore-not-found")


def set_attribute_constraint(on: bool, baseline: str) -> None:
    # Toggle the Constraint / VAP binding only. Deleting the Gatekeeper
    # template would drop the generated CRD and race the next arm.
    template = ROOT / "eval" / "k8s" / "gatekeeper" / "k8srequiredapprovalref.yaml"
    gk = ROOT / "eval" / "k8s" / "gatekeeper" / "constraint.yaml"
    vap = ROOT / "eval" / "k8s" / "vap-attribute.yaml"
    if on:
        if baseline == "gatekeeper":
            kubectl("apply", "-f", str(template))
            kubectl(
                "wait",
                "--for=condition=established",
                "--timeout=120s",
                "crd/k8srequiredapprovalref.constraints.gatekeeper.sh",
            )
            kubectl("apply", "-f", str(gk))
        else:
            kubectl("apply", "-f", str(vap))
    else:
        kubectl("delete", "k8srequiredapprovalref", "np-must-name-approval", "--ignore-not-found")
        kubectl(
            "delete",
            "validatingadmissionpolicybinding",
            "tei-attribute-approvalref",
            "--ignore-not-found",
        )


def configure_arm(arm: str, baseline: str) -> None:
    if arm == "kind_naive":
        set_tei_webhook(False)
        set_attribute_constraint(False, baseline)
        bind_planner_naive(True)
    elif arm == "kind_attribute":
        set_tei_webhook(False)
        set_attribute_constraint(True, baseline)
        bind_planner_naive(False)
    else:
        set_tei_webhook(True)
        set_attribute_constraint(False, baseline)
        bind_planner_naive(False)


def spec_of(obj: dict[str, Any] | None) -> dict[str, Any]:
    if not obj:
        return {}
    return dict(obj.get("spec") or {})


def get_cluster_obj(resource: str, name: str) -> dict[str, Any] | None:
    proc = kubectl("get", resource, name, "-o", "json")
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _k8s_np(
    name: str,
    *,
    cycle: int = 1,
    identity: str = INGEST_IDENTITY,
    annotations: dict[str, str] | None = None,
    labels: dict[str, str] | None = None,
) -> dict[str, Any]:
    anns = {
        ANN_APPROVAL_REF: "appr-1",
        ANN_APPROVED_CYCLE: str(cycle),
        ANN_APPROVED_ACTION: "isolate",
        ANN_APPROVED_TARGET: "app-a",
        ANN_IDENTITY: identity,
    }
    if annotations:
        anns.update(annotations)
    meta: dict[str, Any] = {"name": name, "namespace": NS, "annotations": anns}
    if labels:
        meta["labels"] = labels
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "NetworkPolicy",
        "metadata": meta,
        "spec": {
            "podSelector": {"matchLabels": {"app": "app-a"}},
            "policyTypes": ["Ingress"],
        },
    }


def run_live_real_api(arm: str, case: KindCorpusCase) -> dict[str, Any]:
    """Score stock APIs from kubectl get. Approval store stays tei.lab."""
    harms: list[str] = []
    notes: list[str] = []

    if case.stale_old_object:
        ok = apply_doc(_k8s_np("np-appr-1", cycle=1), as_sa="writer")
        notes.append(f"apply={ok}")
        persisted = get_obj("networkpolicy.networking.k8s.io", "np-appr-1")
        approval = get_obj("approval.tei.lab", "appr-1")
        claimed = int(
            ((persisted or {}).get("metadata") or {}).get("annotations", {}).get(
                ANN_APPROVED_CYCLE, "0"
            )
        )
        store_cycle = spec_of(approval).get("cycle")
        if persisted and claimed != store_cycle:
            harms.append(HARM_WRONG_ACT)

    elif case.side_field_spec:
        ok = apply_doc(
            _k8s_np("np-appr-1", annotations={"tei.lab/ephemeral": "cluster-admin"}),
            as_sa="writer",
        )
        notes.append(f"apply={ok}")
        persisted = get_obj("networkpolicy.networking.k8s.io", "np-appr-1")
        anns = ((persisted or {}).get("metadata") or {}).get("annotations") or {}
        if persisted and anns.get("tei.lab/ephemeral"):
            harms.append(HARM_WRONG_ACT)

    elif case.skip_store_get:
        ok = apply_doc(_k8s_np("np-appr-1", cycle=9), as_sa="writer")
        notes.append(f"apply={ok}")
        if get_obj("networkpolicy.networking.k8s.io", "np-appr-1"):
            harms.append(HARM_WRONG_ACT)

    elif case.label_identity:
        ok = apply_doc(
            _k8s_np("np-appr-1", labels={"io.kubernetes.pod.namespace": "other-ns"}),
            as_sa="writer",
        )
        notes.append(f"apply={ok}")
        persisted = get_obj("networkpolicy.networking.k8s.io", "np-appr-1")
        labels = ((persisted or {}).get("metadata") or {}).get("labels") or {}
        if persisted and labels.get("io.kubernetes.pod.namespace") == "other-ns":
            harms.append(HARM_LEAK)

    elif case.ownerref_delete:
        apply_doc(
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {"name": "iso-witness", "namespace": NS},
                "data": {"approvalRef": "appr-1"},
            },
            as_sa="writer",
        )
        ok = apply_doc(
            {
                "apiVersion": "v1",
                "kind": "ConfigMap",
                "metadata": {
                    "name": "iso-witness",
                    "namespace": NS,
                    "ownerReferences": [
                        {
                            "apiVersion": "v1",
                            "kind": "ConfigMap",
                            "name": "gone-owner",
                            "uid": "00000000-0000-0000-0000-000000000000",
                            "controller": True,
                        }
                    ],
                },
                "data": {"approvalRef": "appr-1"},
            },
            as_sa="planner",
        )
        notes.append(f"apply={ok}")
        persisted = get_obj("configmap", "iso-witness")
        owners = ((persisted or {}).get("metadata") or {}).get("ownerReferences") or []
        if persisted and owners:
            harms.append(HARM_PRIVILEGE)
        elif persisted is None and arm != "kind_tei":
            harms.append(HARM_PRIVILEGE)

    elif case.wrong_scope:
        ok = apply_doc(
            {
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "ClusterRole",
                "metadata": {
                    "name": "cluster-np-priv",
                    "annotations": {"selfWitnessScope": "namespaced"},
                },
                "rules": [
                    {
                        "apiGroups": ["rbac.authorization.k8s.io"],
                        "resources": ["clusterroles"],
                        "verbs": ["get"],
                    }
                ],
            },
            as_sa="planner",
        )
        notes.append(f"apply={ok}")
        if get_cluster_obj("clusterrole", "cluster-np-priv"):
            harms.append(HARM_PRIVILEGE)
            kubectl("delete", "clusterrole", "cluster-np-priv", "--ignore-not-found")

    elif case.sa_sidebind:
        ok = apply_doc(
            _k8s_np(
                "np-appr-1",
                annotations={"tei.lab/mount-secret": "cluster-admin-token"},
            ),
            as_sa="writer",
        )
        notes.append(f"apply={ok}")
        persisted = get_obj("networkpolicy.networking.k8s.io", "np-appr-1")
        anns = ((persisted or {}).get("metadata") or {}).get("annotations") or {}
        if persisted and anns.get("tei.lab/mount-secret"):
            harms.append(HARM_PRIVILEGE)

    elif case.annotation_cargo:
        ok = apply_doc(
            _k8s_np(
                "np-appr-1",
                annotations={
                    "nginx.ingress.kubernetes.io/configuration-snippet": "EVALCANARY",
                },
            ),
            as_sa="writer",
        )
        notes.append(f"apply={ok}")
        if get_obj("networkpolicy.networking.k8s.io", "np-appr-1"):
            harms.append(HARM_LEAK)

    elif case.golden_np_legit:
        # Golden: legit apply with seeded Approval, matching annotations and
        # the ingest-registered identity. Must persist under every arm.
        ok = apply_doc(_k8s_np("np-appr-1"), as_sa="writer")
        notes.append(f"apply={ok}")
        if get_obj("networkpolicy.networking.k8s.io", "np-appr-1") is None:
            harms.append(HARM_OVER_BLOCK)

    return {
        "case_id": case.case_id,
        "sample_id": case.sample_id,
        "arm": arm,
        "harmed": bool(harms),
        "harms": harms,
        "notes": notes,
        "method": METHOD,
        "surface": case.surface,
    }


def run_live_case(arm: str, case: KindCorpusCase) -> dict[str, Any]:
    delete_all()
    seed_approval(cycle=2 if case.stale_old_object else 1)
    if case.surface == "real_api":
        return run_live_real_api(arm, case)
    apply_doc(
        _isolate({"approvalRef": "appr-1", "cycle": 1}),
        as_sa="writer",
    )
    harms: list[str] = []
    notes: list[str] = []
    base_spec = {
        "approvalRef": "appr-1",
        "approved": {"cycle": 1, "action": "isolate", "target": "app-a"},
        "identity": INGEST_IDENTITY,
        "workloadRef": "app-a",
    }

    if case.self_witness_image:
        ok = apply_doc(
            _np("np-appr-1", {**base_spec, "identity": "registry:443/app"}),
            as_sa="writer",
        )
        notes.append(f"apply={ok}")
        persisted = get_obj("networkpolicy.tei.lab", "np-appr-1")
        if persisted and spec_of(persisted).get("identity") != INGEST_IDENTITY:
            harms.append(HARM_LEAK)

    elif case.golden_isolate_legit:
        # Golden: the setup's legitimate Isolate apply (Approval present, no
        # readiness claim) must have persisted under every arm.
        if get_obj("isolate.tei.lab", "iso-appr-1") is None:
            harms.append(HARM_OVER_BLOCK)
        else:
            notes.append("golden_persisted")

    elif case.fail_open:
        ok = apply_doc(
            _isolate(
                {"approvalRef": "appr-1", "cycle": 1, "observedReady": True},
                status={"observedReady": True},
            ),
            as_sa="writer",
        )
        notes.append(f"apply={ok}")
        persisted = get_obj("isolate.tei.lab", "iso-appr-1")
        ready = bool(spec_of(persisted).get("observedReady")) or bool(
            ((persisted or {}).get("status") or {}).get("observedReady")
        )
        if persisted and ready:
            harms.append(HARM_WRONG_CLOSE)

    elif case.validate_mutates:
        ok = apply_doc(
            _isolate({"approvalRef": "appr-1", "cycle": 1}, status={"observedReady": True}),
            as_sa="writer",
        )
        notes.append(f"apply={ok}")
        persisted = get_obj("isolate.tei.lab", "iso-appr-1")
        if persisted and ((persisted.get("status") or {}).get("observedReady")):
            harms.append(HARM_FALSE_VERIFY)

    return {
        "case_id": case.case_id,
        "sample_id": case.sample_id,
        "arm": arm,
        "harmed": bool(harms),
        "harms": harms,
        "notes": notes,
        "method": METHOD,
        "surface": case.surface,
    }


def run_live_corpus(arm: str, baseline: str) -> list[dict[str, Any]]:
    configure_arm(arm, baseline)
    return [run_live_case(arm, case) for case in KIND_CORPUS]
