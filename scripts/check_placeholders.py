#!/usr/bin/env python3
"""Refuse to ship while any stand-in artifact is still in place.

A stand-in carries the token below inside the file itself rather than in a
side registry, so a real participant's submission overwriting the path
clears the block automatically and a flag cannot be flipped without doing
the work.
"""

from __future__ import annotations

import sys
from pathlib import Path

TOKEN = "STAND-IN-PENDING-REPLACEMENT"
ROOT = Path(__file__).resolve().parent.parent

# Every path a real participant is expected to author or overwrite.
# Grouped by the layer that becomes unsupportable if the stand-in ships.
TRACKED: dict[str, tuple[str, ...]] = {
    "independent authors (human track)": tuple(
        f"eval/author-brief/submissions/submission-H{h}-a{a}.md"
        for h in (1, 2, 3)
        for a in (1, 2, 3)
    )
    + tuple(f"eval/author-brief/qa-log-H{h}.md" for h in (1, 2, 3))
    + tuple(f"eval/author-brief/role-prompts/human-track-H{h}.md" for h in (1, 2, 3))
    + ("backend/app/eval_suite/independent_cases.py",),
    "gate review (G1/G2)": (
        "eval/results/gate-review/g1-review.md",
        "eval/results/gate-review/g2-review.md",
        "eval/results/gate-review/latest.md",
    ),
    "CVE mapping fidelity (K1/K2)": (
        "eval/results/k8s-kind/cve-scoring/k1-scores.json",
        "eval/results/k8s-kind/cve-scoring/k2-adjudication.md",
        "eval/results/k8s-kind/cve-scoring/latest.md",
    ),
}

# Derived outputs that must be regenerated after a swap. Not marked, because
# a run overwrites them; listed so the report names them.
REGENERATE = (
    "eval/results/independent/latest.json",
    "eval/results/independent/latest.md",
    "eval/results/independent/filter-log.md",
    "eval/results/independent/out-of-knob.md",
    "eval/results/k8s-kind/README.md",
)


def main() -> int:
    missing: list[str] = []
    outstanding: dict[str, list[str]] = {}

    for layer, paths in TRACKED.items():
        for rel in paths:
            path = ROOT / rel
            if not path.exists():
                missing.append(rel)
                continue
            if TOKEN in path.read_text(encoding="utf-8", errors="ignore"):
                outstanding.setdefault(layer, []).append(rel)

    if missing:
        print("tracked path does not exist (registry is stale):", file=sys.stderr)
        for rel in missing:
            print(f"  {rel}", file=sys.stderr)
        return 2

    if not outstanding:
        print("placeholder check: no stand-in artifacts remain")
        return 0

    total = sum(len(v) for v in outstanding.values())
    print(f"{total} stand-in artifact(s) still in place:", file=sys.stderr)
    for layer, paths in outstanding.items():
        print(f"\n  {layer}", file=sys.stderr)
        for rel in paths:
            print(f"    {rel}", file=sys.stderr)
    print(
        "\nReplace them with the real participants' output, then regenerate:",
        file=sys.stderr,
    )
    for rel in REGENERATE:
        print(f"    {rel}", file=sys.stderr)
    print("\nSwap procedure: eval/placeholder-registry.md", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
