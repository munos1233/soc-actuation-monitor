#!/usr/bin/env python3
"""Mixed-load fail-closed backlog (does not overwrite scale or overhead).

    DATABASE_URL=... REDIS_URL=... python eval/harness/run_backlog.py \
        --events 120 --out eval/results/backlog
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

from app.eval_suite.backlog import (  # noqa: E402
    DEFAULT_EVENTS,
    render_backlog_markdown,
    run_backlog_probe,
)
from app.eval_suite.configs import VendorColumn  # noqa: E402


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=DEFAULT_EVENTS)
    parser.add_argument("--column", default=VendorColumn.MOCK.value)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "backlog"))
    return parser.parse_args(argv)


async def _run(args: argparse.Namespace) -> int:
    report = await run_backlog_probe(
        events=args.events,
        column=VendorColumn(args.column),
    )
    report["generated_at"] = datetime.now(UTC).isoformat()
    rendered = render_backlog_markdown(report) + "\n"
    print(rendered)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    payload = json.dumps(report, indent=2, default=str)
    (out_dir / f"run-{stamp}.json").write_text(payload, encoding="utf-8")
    (out_dir / "latest.json").write_text(payload, encoding="utf-8")
    (out_dir / "latest.md").write_text(rendered, encoding="utf-8")
    return 0


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run(_parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
