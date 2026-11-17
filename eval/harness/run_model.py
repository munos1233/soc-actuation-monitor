#!/usr/bin/env python3
"""Exhaustive interleaving check of the terminal-head protocol (paper §Invariants).

    python eval/harness/run_model.py --out eval/results/model

No database, no Redis, no extra packages. Fails the process if the deployed
configuration ever violates an invariant.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "eval" / "model"))

from head_invariants import main as check_main  # noqa: E402
from write_path_invariants import main as write_path_main  # noqa: E402


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, nargs="+", default=[2, 3, 4])
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "model"))
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = _parse_args(None)
    head = check_main(
        [
            "--workers",
            *[str(w) for w in args.workers],
            "--out",
            args.out,
        ]
    )
    write_path = write_path_main(["--out", args.out])
    raise SystemExit(head or write_path)
