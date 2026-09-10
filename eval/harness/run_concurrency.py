#!/usr/bin/env python3
"""Multi-process contention probe (Experiment 3 of the evaluation).

Separate from run_suite.py because it is a different kind of measurement: the
matrix asks whether a mechanism refuses a second attempt, this asks whether the
mechanism holds when the attempts are genuinely simultaneous. It also needs to
spawn processes, and mixing that into the matrix runner would make one slow run
out of two fast ones.

    DATABASE_URL=... REDIS_URL=... python eval/harness/run_concurrency.py \
        --workers 4 --rounds 5 --out eval/results/concurrency

Point it only at the isolated evaluation stack. It writes to the database it is
given.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.eval_suite.concurrency import (  # noqa: E402
    DEFAULT_ROUNDS,
    DEFAULT_WORKERS,
    PROBE_CONFIGS,
    render_concurrency_markdown,
    run_concurrency_probe,
    summarize_concurrency,
)
from app.eval_suite.configs import CONFIGS, VendorColumn  # noqa: E402


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--rounds", type=int, default=DEFAULT_ROUNDS)
    parser.add_argument("--column", default=VendorColumn.MOCK.value)
    parser.add_argument(
        "--configs",
        default=",".join(config.name for config in PROBE_CONFIGS),
        help="comma-separated configuration names",
    )
    parser.add_argument("--out", default="")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    configs = tuple(CONFIGS[name.strip()] for name in args.configs.split(",") if name.strip())
    rows = await run_concurrency_probe(
        column=VendorColumn(args.column),
        configs=configs,
        workers=args.workers,
        rounds=args.rounds,
    )
    table = summarize_concurrency(rows)
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "workers": args.workers,
        "rounds": args.rounds,
        "column": args.column,
        "configs": [config.name for config in configs],
        "rows": rows,
        "summary": table,
    }
    markdown = [
        "# Multi-process contention probe",
        "",
        f"{args.workers} concurrent OS processes, {args.rounds} rounds per "
        f"configuration per contention point, vendor column `{args.column}`.",
        "",
        render_concurrency_markdown(table),
        "",
    ]
    late = sum(int(entry["late_workers"]) for entry in table)
    if late:
        markdown.append(
            f"**{late} worker starts missed the shared start instant**; those rounds "
            "did not race and must not be read as evidence either way."
        )
        markdown.append("")
    rendered = "\n".join(markdown)
    print(rendered)
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        (out_dir / f"run-{stamp}.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        (out_dir / "latest.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        (out_dir / "latest.md").write_text(rendered, encoding="utf-8")
        print(f"wrote {out_dir}/run-{stamp}.json", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
