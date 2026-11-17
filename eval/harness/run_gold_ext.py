#!/usr/bin/env python3
"""Suite A extension runner: golden g5-g11, naive vs full, never pooled.

Usage:
    python eval/harness/run_gold_ext.py [--out eval/results/gold_ext]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.eval_suite.configs import FULL, NAIVE  # noqa: E402
from app.eval_suite.gold import render_gold_markdown, run_gold  # noqa: E402
from app.eval_suite.gold_ext import GOLDEN_EXT_CASES  # noqa: E402


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "gold_ext"))
    args = parser.parse_args(argv)

    full_rows = await run_gold(config=FULL, cases=GOLDEN_EXT_CASES)
    naive_rows = await run_gold(config=NAIVE, cases=GOLDEN_EXT_CASES)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "cases": [c.case_id for c in GOLDEN_EXT_CASES],
        "pooled_with_frozen_golden": False,
        "full": full_rows,
        "naive": naive_rows,
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"run-{stamp}.json").write_text(json.dumps(payload, indent=2) + "\n")
    (out / "latest.json").write_text(json.dumps(payload, indent=2) + "\n")

    md = [
        "# Golden extension layer (g5-g11)",
        "",
        "Never pooled with the frozen golden substrate (g1-g4) or any table",
        "measured on it (overhead / backlog / scale keep their frozen",
        "substrate captions). Each case is a legitimate flow the frozen four",
        "do not cover; over-blocking here is a mediator defect.",
        "",
        "## Full configuration",
        "",
        render_gold_markdown(full_rows, title="### g5-g11 under full"),
        "## Naive (usability comparison)",
        "",
        render_gold_markdown(naive_rows, title="### g5-g11 under naive"),
    ]
    text = "\n".join(md)
    (out / f"run-{stamp}.md").write_text(text + "\n")
    (out / "latest.md").write_text(text + "\n")
    print(text)

    over_blocked = [
        row for row in full_rows if not row["closed"]
    ]
    if over_blocked:
        print(
            f"{len(over_blocked)} golden extension case(s) over-blocked under full; "
            "fix the mediator and re-freeze this layer",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
