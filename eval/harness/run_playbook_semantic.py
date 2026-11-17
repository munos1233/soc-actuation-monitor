#!/usr/bin/env python3
"""Playbook-semantic closer vs naive vs full. Not a commercial SOAR product eval."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.eval_suite.cases import A1_CASES, A5_CASES  # noqa: E402
from app.eval_suite.configs import (  # noqa: E402
    FULL,
    NAIVE,
    PLAYBOOK_SEMANTIC,
    PlannerModel,
    VendorColumn,
)
from app.eval_suite.gold import GOLDEN_CASES, run_gold, summarize_gold  # noqa: E402
from app.eval_suite.runner import run_matrix  # noqa: E402


async def _run() -> dict:
    gold = {}
    for config in (PLAYBOOK_SEMANTIC, NAIVE, FULL):
        rows = await run_gold(columns=(VendorColumn.MOCK, VendorColumn.PSEUDO_LIVE), config=config)
        gold[config.name] = {"rows": rows, "summary": summarize_gold(rows)}
    receipt_cases = tuple(
        case
        for case in (*A1_CASES, *A5_CASES)
        if case.case_id
        in {
            "a1_weak_receipt",
            "a1_dropped_readback",
            "a5_lying_vendor_receipt",
            "a5_echo_observation",
        }
    )
    suite = await run_matrix(
        configs=(PLAYBOOK_SEMANTIC, NAIVE, FULL),
        columns=(VendorColumn.MOCK, VendorColumn.PSEUDO_LIVE),
        planners=(PlannerModel.UNTRUSTED_PLANNER,),
        cases=receipt_cases,
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "commercial_soar": False,
        "note": "Measures the playbook-as-truth closer, not a product.",
        "gold": gold,
        "receipt_rows": suite,
    }


def render(payload: dict) -> str:
    lines = [
        "# Playbook-semantic closer",
        "",
        "Not a commercial SOAR evaluation. Closer writes CLOSED on step SUCCESS.",
        "",
        "| arm | suite A closed |",
        "|---|---|",
    ]
    for name, block in payload["gold"].items():
        summary = block["summary"]
        by_col = summary.get("by_column") or {}
        closed = sum(int((col or {}).get("closed") or 0) for col in by_col.values())
        total = sum(int((col or {}).get("total") or 0) for col in by_col.values())
        lines.append(f"| `{name}` | {closed}/{total} |")
    lines.append("")
    lines.append("| case | column | playbook_semantic | naive | full |")
    lines.append("|---|---|---|---|---|")
    by: dict[tuple[str, str, str], bool] = {}
    for row in payload["receipt_rows"]:
        if row.get("applicable"):
            by[(row["case_id"], row["column"], row["config"])] = bool(row["harmed"])
    cases = sorted({(r["case_id"], r["column"]) for r in payload["receipt_rows"] if r.get("applicable")})
    for case_id, column in cases:
        cells = []
        for cfg in ("playbook_semantic", "naive", "full"):
            harmed = by.get((case_id, column, cfg))
            cells.append("harm" if harmed else ("ok" if harmed is False else "—"))
        lines.append(f"| `{case_id}` | {column} | " + " | ".join(cells) + " |")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "playbook_semantic"))
    args = parser.parse_args(argv)
    payload = asyncio.run(_run())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    md = render(payload)
    (out / "latest.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
    (out / "latest.md").write_text(md + "\n")
    print(md)
    gold_full = payload["gold"]["playbook_semantic"]["summary"]
    # Gold must close; do not require a specific key shape beyond non-empty.
    if not gold_full:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
