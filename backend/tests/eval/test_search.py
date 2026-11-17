"""Offline guards for the coverage search: space, seeds, bypass predicate."""

from __future__ import annotations

from types import SimpleNamespace

from app.eval_suite.search import (
    FLAG_NAMES,
    MUTATE_VALUES,
    RECEIPT_PROFILES,
    SearchSpec,
    coverage_key,
    enumerate_search_space,
    is_bypass,
    model_seed_specs,
    order_candidates,
    spec_from_injection_knobs,
)
from app.eval_suite.vendor import ReceiptProfile


def test_search_space_is_the_documented_cartesian() -> None:
    space = enumerate_search_space()
    expected = len(MUTATE_VALUES) * len(RECEIPT_PROFILES) * (2 ** len(FLAG_NAMES))
    assert len(space) == expected
    assert len({spec.key() for spec in space}) == expected


def test_sql_bypass_seed_is_outside_the_cartesian() -> None:
    assert spec_from_injection_knobs({"sql_bypass": "close"}) is None


def test_model_seeds_are_in_space_and_ordered_first() -> None:
    seeds = model_seed_specs()
    assert seeds
    assert all(spec.mutate_after_approval or spec.locator_swap or spec.bump_revision_after_activation for spec in seeds)
    ordered = order_candidates(enumerate_search_space())
    assert ordered[: len(seeds)] == seeds


def test_bypass_is_harm_or_skip_report_close() -> None:
    spec = SearchSpec(
        mutate_after_approval=None,
        receipt_profile=ReceiptProfile.STRONG,
        skip_report=True,
        locator_swap=False,
        rewrite_idempotency_key=False,
        strip_outbox_revision=False,
        bump_revision_after_activation=False,
    )
    assert is_bypass(spec, SimpleNamespace(harmed=True, closed=False))
    assert is_bypass(spec, SimpleNamespace(harmed=False, closed=True))
    open_spec = SearchSpec(
        mutate_after_approval="target",
        receipt_profile=ReceiptProfile.STRONG,
        skip_report=False,
        locator_swap=False,
        rewrite_idempotency_key=False,
        strip_outbox_revision=False,
        bump_revision_after_activation=False,
    )
    assert not is_bypass(open_spec, SimpleNamespace(harmed=False, closed=True))


def test_coverage_key_uses_world_facts() -> None:
    key = coverage_key(
        SimpleNamespace(
            closed=False,
            harmed=False,
            blocked_errors=("validation_error",),
            entity_submits=0,
        )
    )
    assert key == (False, False, frozenset({"validation_error"}), False)
