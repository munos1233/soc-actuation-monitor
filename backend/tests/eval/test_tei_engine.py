"""TEI.tla engine: full holds; each ablation has a CE; CAS is layered."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "eval" / "model"))

from tei_engine import (  # noqa: E402
    ATTR_VIEW_FIELDS,
    ACTION_HONEST_ADVANCE,
    ACTION_PLANNER_FORGE,
    ACTION_PLANNER_STALE,
    Mechanisms,
    START,
    attr_view,
    bind_ok,
    close_ok,
    close_witness_pair,
    emit_tlc_seeds,
    explore,
    explore_view_pair,
    view_consistent,
)


def test_full_tei_has_no_counterexample() -> None:
    result = explore(Mechanisms())
    assert result["mechanisms"] == "full"
    assert result["violations"] == {}
    assert result["cas_status_layer_holds"] is True


def test_ablations_have_shortest_counterexamples() -> None:
    expected = {
        Mechanisms(CloseRebuild=False): "close",
        Mechanisms(BindRecompute=False): "bind",
        Mechanisms(EgressWitness=False): "egress",
        Mechanisms(RoleRevoke=False): "role",
        Mechanisms(VerifySplit=False): "verify",
        Mechanisms(HeadUnique=False): "head",
        Mechanisms(ClaimCAS=False): "cas",
    }
    for mech, inv in expected.items():
        result = explore(mech)
        assert inv in result["violations"], (mech.name, result["violations"])
        assert result["violations"][inv]


def test_cas_lemma_is_status_layer() -> None:
    full = explore(Mechanisms())
    assert full["cas_lemma"]["head_holds"] is True
    assert full["cas_lemma"]["status_holds"] is True
    minus_cas = explore(Mechanisms(ClaimCAS=False))
    assert "head" not in minus_cas["violations"]
    assert "cas" in minus_cas["violations"]
    assert minus_cas["violations"]["cas"][-1] == "SecondClaim"
    minus_head = explore(Mechanisms(HeadUnique=False))
    assert "head" in minus_head["violations"]


def test_attribute_only_has_close_and_bind_counterexamples() -> None:
    """One π ∈ Π: AttrView self-consistency, not CloseOK/BindOK."""
    full = explore(Mechanisms())
    assert full["violations"] == {}
    attr = explore(Mechanisms(AttributeOnly=True))
    assert attr["mechanisms"] == "attribute_only"
    assert "close" in attr["violations"]
    assert "bind" in attr["violations"]
    assert attr["violations"]["close"][0] == "PlannerStaleCycle"
    assert attr["violations"]["bind"][0] == "PlannerForgeFingerprint"
    assert "egress" not in attr["violations"]


def test_attr_view_excludes_store_fields() -> None:
    assert "rebuiltCycle" not in ATTR_VIEW_FIELDS
    assert "recomputedFp" not in ATTR_VIEW_FIELDS
    assert attr_view(START) == (
        START.callerCycle,
        START.plannerFp,
        START.signedOk,
        START.attachedApprovalCopy,
        START.reportedReceipt,
    )
    assert close_ok(START) is True
    assert bind_ok(START) is True
    assert view_consistent(START) is True


def test_close_witness_pair_same_view_different_predicate() -> None:
    pair = close_witness_pair()
    assert pair["same_view"] is True
    assert pair["close_ok_honest"] is True
    assert pair["close_ok_stale"] is False
    assert pair["honest_action"] == ACTION_HONEST_ADVANCE
    assert pair["stale_action"] == ACTION_PLANNER_STALE
    assert "rebuiltCycle" not in {
        "callerCycle",
        "plannerFp",
        "signedOk",
        "attachedApprovalCopy",
        "reportedReceipt",
    }
    assert pair["honest"].rebuiltCycle != pair["stale"].rebuiltCycle
    assert attr_view(pair["honest"]) == attr_view(pair["stale"])


def test_view_pair_product_finds_close_ce() -> None:
    result = explore_view_pair()
    assert result["inv_view_close_holds"] is False
    trace = result["inv_view_close_ce"]
    assert trace is not None
    actions = {step.split("_", 1)[1] for step in trace}
    assert ACTION_HONEST_ADVANCE in actions
    assert ACTION_PLANNER_STALE in actions
    assert {ACTION_HONEST_ADVANCE, ACTION_PLANNER_STALE} == actions


def test_honest_advance_is_not_an_ablation() -> None:
    from tei_engine import LADDER

    names = [mech.name for mech in LADDER]
    assert names[0] == "full"
    assert "attribute_only" in names
    assert "minus_honest" not in names
    assert ACTION_PLANNER_FORGE == "PlannerForgeFingerprint"


def test_reads_s_then_close_holds() -> None:
    from tei_engine import reads_s_close

    full = Mechanisms()
    attr = Mechanisms(AttributeOnly=True)
    assert reads_s_close(full) is True
    assert reads_s_close(attr) is False
    assert explore(full)["violations"] == {}
    assert "close" in explore(attr)["violations"]


def test_tlc_seeds_cover_soc_four() -> None:
    seeds = emit_tlc_seeds()
    by_inv = {seed["invariant"]: seed for seed in seeds}
    assert {"close", "bind", "egress", "role"} <= set(by_inv)
    assert by_inv["close"]["trace"][0] == "PlannerStaleCycle"
    assert by_inv["close"]["injection"] == {"bump_revision_after_activation": True}
