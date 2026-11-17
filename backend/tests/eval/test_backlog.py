"""Offline guards for the mixed-load arrival generator."""

from __future__ import annotations

from app.eval_suite.backlog import (
    DEFAULT_EVENTS,
    FAIL_CLOSED_IDS,
    build_arrivals,
)


def test_arrivals_are_deterministic_and_mixed() -> None:
    first = build_arrivals(events=40, seed=7)
    second = build_arrivals(events=40, seed=7)
    assert [row["arrival_time"] for row in first] == [row["arrival_time"] for row in second]
    kinds = {row["kind"] for row in first}
    assert kinds == {"gold", "fail_closed"}
    fail_closed = [row for row in first if row["kind"] == "fail_closed"]
    assert fail_closed
    assert {row["template_id"] for row in fail_closed} <= set(FAIL_CLOSED_IDS)
    times = [row["arrival_time"] for row in first]
    assert times == sorted(times)
    assert times[0] > 0


def test_default_event_count_matches_paper_scale() -> None:
    assert DEFAULT_EVENTS == 120
