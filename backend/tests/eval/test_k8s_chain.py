"""Kubernetes TEI instance: naive harms, full is clean, not pooled with 57."""

from __future__ import annotations

from collections import Counter

from app.eval_suite.k8s_cases import ALL_K8S_CASES, K8S_CASES_BY_ADVERSARY
from app.eval_suite.k8s_chain import run_k8s_suite
from app.eval_suite.k8s_world import Gates


def test_k8s_case_set_has_at_least_three_per_class() -> None:
    assert len(ALL_K8S_CASES) >= 22
    for adv, cases in K8S_CASES_BY_ADVERSARY.items():
        assert len(cases) >= 3, adv


def test_k8s_naive_harms_and_full_is_zero() -> None:
    naive = run_k8s_suite(Gates.naive(), config_name="naive")
    full = run_k8s_suite(Gates.full(), config_name="full")
    naive_by = Counter(o.adversary for o in naive if o.harmed)
    for adv in ("A0", "A1", "A2", "A3", "A4", "A5"):
        assert naive_by[adv] >= 1, (adv, naive_by)
    harmed_full = [o.case_id for o in full if o.harmed]
    assert harmed_full == [], harmed_full


def test_k8s_a0_is_403_then_201() -> None:
    from app.eval_suite.k8s_cases import A0_CASES
    from app.eval_suite.k8s_chain import run_k8s_case

    case = A0_CASES[0]
    naive = run_k8s_case(case, Gates.naive(), config_name="naive")
    full = run_k8s_case(case, Gates.full(), config_name="full")
    assert naive.harmed
    assert naive.persisted_privileged_by_planner or "201" in "".join(naive.notes)
    assert not full.harmed
    assert any("403" in note for note in full.notes)
