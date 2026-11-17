#!/usr/bin/env python3
"""SOC held-out suite from the frozen external sample. Not pooled with 57."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.eval_suite.configs import FULL, NAIVE, PlannerModel, VendorColumn  # noqa: E402
from app.eval_suite.heldout_cases import HELDOUT_CASES, HELDOUT_SAMPLE  # noqa: E402
from app.eval_suite.runner import run_matrix, summarize  # noqa: E402


def render(rows: list[dict], summary: dict) -> str:
    lines = [
        "# SOC held-out (external sample)",
        "",
        "Not pooled with Suite B 57. Case ids point at `external_sample.json`.",
        "",
        f"naive harmed={summary.get('naive')}  full harmed={summary.get('full')}",
        "",
        "| case | sample | naive | full |",
        "|---|---|---|---|",
    ]
    by = {}
    for row in rows:
        if not row.get("applicable"):
            continue
        key = (row["case_id"], row["config"])
        by.setdefault(key, []).append(bool(row["harmed"]))
    for case in HELDOUT_CASES:
        naive = by.get((case.case_id, "naive"), [])
        full = by.get((case.case_id, "full"), [])
        n = f"{sum(naive)}/{len(naive)}" if naive else "—"
        f = f"{sum(full)}/{len(full)}" if full else "—"
        lines.append(f"| `{case.case_id}` | `{HELDOUT_SAMPLE[case.case_id]}` | {n} | {f} |")
    lines.append("")
    return "\n".join(lines)


async def _run() -> dict:
    rows = await run_matrix(
        configs=(NAIVE, FULL),
        columns=(VendorColumn.MOCK, VendorColumn.PSEUDO_LIVE),
        planners=(PlannerModel.UNTRUSTED_PLANNER,),
        cases=HELDOUT_CASES,
    )
    naive = [r for r in rows if r["config"] == "naive" and r.get("applicable")]
    full = [r for r in rows if r["config"] == "full" and r.get("applicable")]
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "pooled_with_57": False,
        "sample_map": HELDOUT_SAMPLE,
        "suite_b_rows": rows,
        "summary": {
            "naive": f"{sum(1 for r in naive if r['harmed'])}/{len(naive)}",
            "full": f"{sum(1 for r in full if r['harmed'])}/{len(full)}",
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "heldout"))
    args = parser.parse_args(argv)
    payload = asyncio.run(_run())
    if any(
        row["harmed"] and row["config"] == "full" and row.get("applicable")
        for row in payload["suite_b_rows"]
    ):
        print("full construction harmed on held-out; fix TEI and re-freeze this suite only", file=sys.stderr)
        code = 1
    else:
        code = 0
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    md = render(payload["suite_b_rows"], payload["summary"])
    (out / "latest.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
    (out / "latest.md").write_text(md + "\n")
    print(md)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
