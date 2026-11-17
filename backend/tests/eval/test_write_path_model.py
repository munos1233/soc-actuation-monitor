"""The write-path model checker is offline and must hold under full."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "eval" / "model"))

from write_path_invariants import Mechanisms, check, emit_seeds  # noqa: E402


def test_full_write_path_has_no_counterexample() -> None:
    result = check(Mechanisms())
    assert result["mechanisms"] == "full"
    assert result["violations"] == {}


def test_each_ablation_has_a_shortest_counterexample() -> None:
    expected = {
        "minus_close": "close",
        "minus_bind": "bind",
        "minus_egress": "egress",
        "minus_role": "role",
    }
    for mech, inv in (
        (Mechanisms(close_rebuild=False), "close"),
        (Mechanisms(bind_recompute=False), "bind"),
        (Mechanisms(egress_event_source=False), "egress"),
        (Mechanisms(role_revoke=False), "role"),
    ):
        result = check(mech)
        assert result["mechanisms"] == f"minus_{inv}", result["mechanisms"]
        assert inv in result["violations"], (inv, result["violations"])
        assert result["violations"][inv], expected


def test_emit_seeds_maps_each_ablation_to_injection_knobs() -> None:
    seeds = emit_seeds()
    by_inv = {seed["invariant"]: seed for seed in seeds}
    assert set(by_inv) == {"close", "bind", "egress", "role"}
    assert by_inv["close"]["injection"] == {"bump_revision_after_activation": True}
    assert by_inv["bind"]["injection"] == {
        "mutate_after_approval": "target_forged_fingerprint"
    }
    assert by_inv["egress"]["injection"] == {"locator_swap": True}
    assert by_inv["role"]["injection"] == {"sql_bypass": "close"}
    assert by_inv["close"]["trace"][0] == "PlannerStaleCycle"
    assert by_inv["close"]["source"] == "TEI.tla/TLC"
