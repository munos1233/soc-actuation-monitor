"""External sample is frozen before cases; every held-out/kind id maps."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SAMPLE = json.loads((ROOT / "eval" / "taxonomy" / "external_sample.json").read_text())


def test_protocol_predates_sample() -> None:
    assert SAMPLE["protocol_written_at"] < SAMPLE["sample_frozen_at"]
    assert SAMPLE["included_count"] == sum(1 for item in SAMPLE["items"] if item["included"])
    assert SAMPLE["truncated_ids"] == []
    assert SAMPLE["t9_defined"] is False


def test_included_items_have_url_and_mapping() -> None:
    for item in SAMPLE["items"]:
        if not item["included"]:
            assert "exclusion" in item
            continue
        assert item["url"].startswith("http")
        assert item["primary"] in {f"T{i}" for i in range(1, 9)}
        assert item["instantiation"] in {"soc", "kind", "not_instantiable"}


def test_heldout_and_kind_ids_point_at_included_sample() -> None:
    from app.eval_suite.heldout_cases import HELDOUT_SAMPLE
    from app.eval_suite.kind_corpus import KIND_CORPUS

    by_id = {item["id"]: item for item in SAMPLE["items"]}
    for case_id, sample_id in HELDOUT_SAMPLE.items():
        assert sample_id in by_id
        assert by_id[sample_id]["included"] is True
        assert by_id[sample_id]["instantiation"] == "soc"
        assert case_id.startswith("h_")
    for case in KIND_CORPUS:
        if case.golden_np_legit or case.golden_isolate_legit:
            # Golden rows are legitimate applies, not sample-mapped attacks;
            # their sample ids are deliberately outside the sample list.
            assert case.harm == "over_block"
            assert case.case_id.startswith("k_golden_")
            continue
        assert case.sample_id in by_id
        assert by_id[case.sample_id]["included"] is True
        assert by_id[case.sample_id]["instantiation"] == "kind"
        assert case.case_id.startswith("k_")
        assert not case.case_id.startswith("a")


def test_kind_tei_has_zero_harm() -> None:
    from app.eval_suite.kind_corpus import run_kind_corpus

    tei = run_kind_corpus("kind_tei")
    assert all(not row["harmed"] for row in tei), tei
    naive = run_kind_corpus("kind_naive")
    attr = run_kind_corpus("kind_attribute")
    assert any(row["harmed"] for row in naive)
    assert sum(1 for row in attr if row["harmed"]) == 9
