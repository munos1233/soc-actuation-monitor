"""Offline tests for freeze cell-diff harness."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_harness():
    path = Path(__file__).resolve().parents[3] / "eval" / "harness" / "diff_freeze.py"
    spec = importlib.util.spec_from_file_location("diff_freeze", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_suite_b_identity_zero_diffs() -> None:
    mod = _load_harness()
    root = Path(__file__).resolve().parents[3]
    payload = json.loads((root / "eval" / "results" / "latest.json").read_text())
    cells = mod._extract_cells(payload)
    report = mod.diff_cells(cells, cells)
    assert report["cell_diffs"] == 0
    assert report["baseline_cells"] > 0


def test_kind_mismatch_detected() -> None:
    mod = _load_harness()
    root = Path(__file__).resolve().parents[3]
    payload = json.loads((root / "eval" / "results" / "k8s-kind" / "latest.json").read_text())
    base = mod._extract_cells(payload)
    rerun = {k: dict(v) for k, v in base.items()}
    first = next(iter(rerun))
    rerun[first] = {**rerun[first], "harmed": not rerun[first]["harmed"]}
    report = mod.diff_cells(base, rerun)
    assert report["cell_diffs"] == 1
    assert len(report["mismatches"]) == 1
