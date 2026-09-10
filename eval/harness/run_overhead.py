#!/usr/bin/env python3
"""Mediator overhead probe (Experiment 4 of the evaluation).

    DATABASE_URL=... REDIS_URL=... python eval/harness/run_overhead.py \
        --repeats 3 --out eval/results/overhead

Point it only at the isolated evaluation stack.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.eval_suite.configs import VendorColumn  # noqa: E402
from app.eval_suite.overhead import (  # noqa: E402
    DEFAULT_REPEATS,
    render_overhead_markdown,
    run_overhead_probe,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=DEFAULT_REPEATS)
    parser.add_argument("--column", default=VendorColumn.MOCK.value)
    parser.add_argument("--out", default="")
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    report = await run_overhead_probe(
        column=VendorColumn(args.column),
        repeats=args.repeats,
    )
    report["generated_at"] = datetime.now(UTC).isoformat()
    report["repeats"] = args.repeats
    rendered = "\n".join(
        [
            "# Mediator overhead",
            "",
            f"Every applicable case, {args.repeats} repeats, vendor column "
            f"`{args.column}`. The naive row is not zero: it is the cost of asking "
            "whether each mediator is loaded.",
            "",
            render_overhead_markdown(report),
            "",
        ]
    )
    print(rendered)
    if args.out:
        out_dir = Path(args.out)
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        payload = json.dumps(report, indent=2, default=str)
        (out_dir / f"run-{stamp}.json").write_text(payload, encoding="utf-8")
        (out_dir / "latest.json").write_text(payload, encoding="utf-8")
        (out_dir / "latest.md").write_text(rendered, encoding="utf-8")
        print(f"wrote {out_dir}/run-{stamp}.json", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
