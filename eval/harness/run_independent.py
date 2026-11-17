#!/usr/bin/env python3
"""Independent-author layer: naive vs full, never pooled with the 57.

Usage:
    python eval/harness/run_independent.py [--out eval/results/independent]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "eval" / "harness"))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.eval_suite.configs import FULL, NAIVE, PlannerModel, VendorColumn  # noqa: E402
from app.eval_suite.independent_cases import INDEPENDENT_CASES  # noqa: E402
from app.eval_suite.runner import run_matrix  # noqa: E402
from gitmeta import git_head  # noqa: E402




def render(rows: list[dict], *, human_ids: set[str], agent_ids: set[str]) -> str:
    lines = [
        "# Independent author track",
        "",
        "Never pooled with Suite B 57, held-out, gold_ext, B2, or mutation.",
        "Two manuscript lines: human-authored and agent-authored.",
        "",
    ]

    def _bucket(ids: set[str], label: str) -> None:
        naive = [
            r
            for r in rows
            if r["case_id"] in ids and r["config"] == "naive" and r.get("applicable")
        ]
        full = [
            r
            for r in rows
            if r["case_id"] in ids and r["config"] == "full" and r.get("applicable")
        ]
        idle_n = sum(1 for r in naive if not r.get("harmed") and r.get("applicable"))
        lines.append(f"## {label}")
        lines.append("")
        lines.append(
            f"naive harmed={sum(1 for r in naive if r.get('harmed'))}/{len(naive)}  "
            f"full harmed={sum(1 for r in full if r.get('harmed'))}/{len(full)}  "
            f"naive idle≈{idle_n}/{len(naive)}"
        )
        lines.append("")
        lines.append("| case | track | naive | full |")
        lines.append("|---|---|---|---|")
        for case_id in sorted(ids):
            n_rows = [
                r
                for r in rows
                if r["case_id"] == case_id and r["config"] == "naive" and r.get("applicable")
            ]
            f_rows = [
                r
                for r in rows
                if r["case_id"] == case_id and r["config"] == "full" and r.get("applicable")
            ]
            if not n_rows and not f_rows:
                lines.append(f"| `{case_id}` | {label} | n/a | n/a |")
                continue
            n = f"{sum(1 for r in n_rows if r.get('harmed'))}/{len(n_rows)}" if n_rows else "—"
            f = f"{sum(1 for r in f_rows if r.get('harmed'))}/{len(f_rows)}" if f_rows else "—"
            lines.append(f"| `{case_id}` | {label} | {n} | {f} |")
        lines.append("")

    _bucket(human_ids, "human-authored")
    _bucket(agent_ids, "agent-authored")
    return "\n".join(lines)


async def _run() -> dict:
    from app.eval_suite.independent_cases import AGENT_CASES, HUMAN_CASES

    rows = await run_matrix(
        configs=(NAIVE, FULL),
        columns=(VendorColumn.MOCK, VendorColumn.PSEUDO_LIVE),
        planners=(PlannerModel.UNTRUSTED_PLANNER,),
        cases=INDEPENDENT_CASES,
    )
    human_ids = {c.case_id for c in HUMAN_CASES}
    agent_ids = {c.case_id for c in AGENT_CASES}
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "commit": git_head(),
        "pooled_with_57": False,
        "human_case_ids": sorted(human_ids),
        "agent_case_ids": sorted(agent_ids),
        "rows": rows,
        "summary_md": render(rows, human_ids=human_ids, agent_ids=agent_ids),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "independent"))
    args = parser.parse_args(argv)
    if not INDEPENDENT_CASES:
        print("no independent cases registered", file=sys.stderr)
        return 2
    payload = asyncio.run(_run())
    full_harm = any(
        row.get("harmed") and row.get("config") == "full" and row.get("applicable")
        for row in payload["rows"]
    )
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    md = payload.pop("summary_md")
    (out / f"run-{stamp}.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
    (out / "latest.json").write_text(json.dumps(payload, indent=2, default=str) + "\n")
    (out / f"run-{stamp}.md").write_text(md + "\n")
    (out / "latest.md").write_text(md + "\n")
    print(md)
    if full_harm:
        print(
            "full construction harmed on independent layer; fix TEI and re-freeze",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
