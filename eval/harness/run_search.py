#!/usr/bin/env python3
"""Coverage-guided search over implemented Injection knobs.

    DATABASE_URL=... REDIS_URL=... python eval/harness/run_search.py \
        --budget 512 --out eval/results/search

Exit 1 if a bypass is found under full — do not freeze that run.
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
from app.eval_suite.search import (  # noqa: E402
    DEFAULT_BUDGET,
    render_search_markdown,
    run_coverage_search,
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--column", default=VendorColumn.MOCK.value)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "search"))
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    report = await run_coverage_search(
        column=VendorColumn(args.column),
        budget=args.budget,
    )
    payload = report.to_json()
    payload["generated_at"] = datetime.now(UTC).isoformat()
    rendered = render_search_markdown(report) + "\n"
    print(rendered)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    text = json.dumps(payload, indent=2, default=str)
    (out_dir / f"run-{stamp}.json").write_text(text, encoding="utf-8")
    (out_dir / "latest.json").write_text(text, encoding="utf-8")
    (out_dir / "latest.md").write_text(rendered, encoding="utf-8")
    return 1 if report.bypass_found else 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
