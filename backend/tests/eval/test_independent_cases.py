"""Independent author cases stay outside ALL_CASES / Suite B pooling."""

from __future__ import annotations

from app.eval_suite.cases import ALL_CASES
from app.eval_suite.independent_cases import (
    AGENT_CASES,
    HUMAN_CASES,
    INDEPENDENT_CASES,
    OUT_OF_KNOB_SUBMISSIONS,
)


def test_independent_cases_never_in_all_cases() -> None:
    all_ids = {c.case_id for c in ALL_CASES}
    indie_ids = {c.case_id for c in INDEPENDENT_CASES}
    assert indie_ids.isdisjoint(all_ids)


def test_independent_adversary_is_i() -> None:
    assert HUMAN_CASES and AGENT_CASES
    assert all(c.adversary == "I" for c in INDEPENDENT_CASES)


def test_tracks_are_disjoint_and_union_is_registry() -> None:
    human_ids = {c.case_id for c in HUMAN_CASES}
    agent_ids = {c.case_id for c in AGENT_CASES}
    assert human_ids.isdisjoint(agent_ids)
    assert human_ids | agent_ids == {c.case_id for c in INDEPENDENT_CASES}


def test_out_of_knob_listed() -> None:
    assert "submission-H3-a1.md" in OUT_OF_KNOB_SUBMISSIONS
