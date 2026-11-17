"""OPA / HMAC 16 residuals are exactly needs_store_join."""

from __future__ import annotations

import json
from pathlib import Path

from app.eval_suite.store_join import (
    NEEDS_STORE_JOIN_IDS,
    a15_cells,
    classify,
    needs_store_join_cells,
    residual_case_ids,
)

ROOT = Path(__file__).resolve().parents[3]


def test_a15_cells_are_45() -> None:
    assert len(a15_cells()) == 45
    assert len(needs_store_join_cells()) == 16
    assert classify("a4_narrative_in_target") == "request_closed"
    assert classify("a3_duplicate_entity_dispatch") == "request_closed"
    assert classify("a1_stale_closure_cycle") == "request_closed"


def test_opa_and_hmac_residuals_match_join_set() -> None:
    comparator = json.loads((ROOT / "eval" / "results" / "comparator" / "latest.json").read_text())
    hmac = json.loads((ROOT / "eval" / "results" / "signed_attribute" / "latest.json").read_text())
    opa_ids = residual_case_ids(comparator["suite_b_rows"], "external_opa")
    hmac_ids = residual_case_ids(hmac["suite_b_rows"], "signed_attribute")
    assert opa_ids == set(NEEDS_STORE_JOIN_IDS)
    assert hmac_ids == set(NEEDS_STORE_JOIN_IDS)
