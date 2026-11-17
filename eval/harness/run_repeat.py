#!/usr/bin/env python3
"""Small repeat-run noise table. Not pooled with 47/57.

Gold path + three adversaries, N=20, naive vs full, mock column.
Reports mean/variance of wall-clock and harm — case-set Wilson is not this.

    DATABASE_URL=... REDIS_URL=... python eval/harness/run_repeat.py \
        --repeats 20 --out eval/results/repeat
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.eval_suite.cases import CASES_BY_ID  # noqa: E402
from app.eval_suite.chain import run_case  # noqa: E402
from app.eval_suite.configs import FULL, NAIVE, VendorColumn, harness_context  # noqa: E402
from app.eval_suite.gold import GOLDEN_CASES  # noqa: E402
from app.eval_suite.world import eval_world  # noqa: E402

REPEAT_ADVERSARIES = (
    "a1_weak_receipt",
    "a2_forged_fingerprint",
    "a4_locator_swap",
)


async def _once(case: Any, cfg: Any) -> dict[str, Any]:
    started = time.perf_counter()
    with harness_context(cfg, VendorColumn.MOCK):
        async with eval_world(VendorColumn.MOCK, role_separation=cfg.role_separation) as world:
            outcome = await run_case(world, case, config_name=cfg.name)
    elapsed = time.perf_counter() - started
    return {
        "case_id": case.case_id,
        "config": cfg.name,
        "harmed": bool(outcome.harmed),
        "closed": bool(outcome.closed),
        "seconds": elapsed,
    }


def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    harms = [int(r["harmed"]) for r in rows]
    seconds = [float(r["seconds"]) for r in rows]
    return {
        "n": len(rows),
        "harm_rate": sum(harms) / len(harms) if harms else 0.0,
        "harm_variance": statistics.pvariance(harms) if len(harms) > 1 else 0.0,
        "seconds_mean": statistics.fmean(seconds) if seconds else 0.0,
        "seconds_variance": statistics.pvariance(seconds) if len(seconds) > 1 else 0.0,
    }


def render_markdown(groups: dict[str, dict[str, Any]]) -> str:
    lines = [
        "# Repeat-run noise (not pooled with 47/57)",
        "",
        "Wilson intervals in the body are case-set proportions. This table is",
        "repeat-run variance on a fixed four-case slice.",
        "",
        "| slice | config | n | harm rate | harm var | seconds mean | seconds var |",
        "|---|---|---|---|---|---|---|",
    ]
    for key, stats in groups.items():
        case_id, config = key.split("|")
        lines.append(
            f"| `{case_id}` | {config} | {stats['n']} | "
            f"{stats['harm_rate']:.2f} | {stats['harm_variance']:.4f} | "
            f"{stats['seconds_mean']:.3f} | {stats['seconds_variance']:.4f} |"
        )
    lines.append("")
    return "\n".join(lines)


async def _run(repeats: int) -> list[dict[str, Any]]:
    cases = [GOLDEN_CASES[0], *[CASES_BY_ID[i] for i in REPEAT_ADVERSARIES]]
    rows: list[dict[str, Any]] = []
    for case in cases:
        for cfg in (NAIVE, FULL):
            for _ in range(repeats):
                rows.append(await _once(case, cfg))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=20)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "repeat"))
    args = parser.parse_args(argv)
    rows = asyncio.run(_run(args.repeats))
    groups: dict[str, dict[str, Any]] = {}
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        key = f"{row['case_id']}|{row['config']}"
        by_key.setdefault(key, []).append(row)
    for key, chunk in by_key.items():
        groups[key] = _stats(chunk)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "pooled_with_headline": False,
        "repeats": args.repeats,
        "groups": groups,
        "rows": rows,
    }
    rendered = render_markdown(groups)
    print(rendered)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")
    (out / "latest.md").write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
