"""Kind headline never copies fixture 22; shared predicates are tests-only."""

from __future__ import annotations

import json
from pathlib import Path

from app.eval_suite.kind_corpus import (
    attack_cases,
    golden_cases,
    real_api_cases,
    run_kind_corpus,
    tei_lab_mapped_cases,
)


def test_shared_predicates_residual() -> None:
    naive = run_kind_corpus("kind_naive")
    attr = run_kind_corpus("kind_attribute")
    tei = run_kind_corpus("kind_tei")
    assert sum(1 for row in naive if row["harmed"]) == 11
    assert sum(1 for row in attr if row["harmed"]) == 9
    assert sum(1 for row in tei if row["harmed"]) == 0
    assert len(real_api_cases()) == 9  # 8 attack + 1 golden
    assert len(tei_lab_mapped_cases()) == 4  # 3 attack + 1 golden
    assert len(attack_cases()) == 11
    assert len(golden_cases()) == 2
    # Golden rows must persist under every arm, including the TEI webhook.
    golden_ids = {c.case_id for c in golden_cases()}
    for rows in (naive, attr, tei):
        assert all(not row["harmed"] for row in rows if row["case_id"] in golden_ids)
    assert {row["surface"] for row in naive} == {"real_api", "tei_lab_mapped"}


def test_client_bookkeeping_annotation_exempt() -> None:
    """Golden-row finding: kubectl's last-applied annotation is not an
    envelope field; a fully legitimate NetworkPolicy must pass TEI."""
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "eval" / "k8s"))
    from tei_admit import KIND_APPROVAL, KIND_NETWORK_POLICY, Store, tei_admit

    store = Store()
    store.put(
        {
            "kind": KIND_APPROVAL,
            "namespace": "tei-lab",
            "name": "appr-1",
            "spec": {"cycle": 1, "action": "isolate", "target": "app-a"},
        }
    )
    np = {
        "kind": KIND_NETWORK_POLICY,
        "namespace": "tei-lab",
        "name": "np-appr-1",
        "spec": {
            "podSelector": {"matchLabels": {"app": "app-a"}},
            "policyTypes": ["Ingress"],
        },
        "annotations": {
            "tei.lab/approval-ref": "appr-1",
            "tei.lab/approved-cycle": "1",
            "tei.lab/approved-action": "isolate",
            "tei.lab/approved-target": "app-a",
            "tei.lab/identity": "wl-app-a",
            "kubectl.kubernetes.io/last-applied-configuration": '{"kind":"NetworkPolicy"}',
        },
        "labels": {},
    }
    decision = tei_admit(store, "writer", "create", np)
    assert decision.persist, decision.reason


def test_run_k8s_kind_without_cluster_does_not_copy_fixture(tmp_path: Path) -> None:
    import sys

    import pytest

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "eval" / "harness"))
    import run_k8s_kind as harness

    ready, _ = harness._kind_ready()
    if ready:
        pytest.skip("kind tei-lab is already up")
    code = harness.main(["--out", str(tmp_path)])
    assert code == 1
    payload = json.loads((tmp_path / "latest.json").read_text())
    assert payload["copied_fixture_22"] is False
    assert payload.get("failed") is True


def test_allow_shared_predicates_writes_method(tmp_path: Path) -> None:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "eval" / "harness"))
    import run_k8s_kind as harness

    code = harness.main(["--out", str(tmp_path), "--allow-shared-predicates"])
    assert code == 0
    payload = json.loads((tmp_path / "latest.json").read_text())
    assert payload["method"] == "shared_predicates"
    assert payload["copied_fixture_22"] is False
    assert payload["fixture_22"] is False
