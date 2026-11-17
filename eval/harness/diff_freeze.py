#!/usr/bin/env python3
"""Cell-by-cell freeze diff for independent re-execution (offline, no DB).

Compares a frozen baseline JSON to a re-run JSON. Supports:

- Suite B / heldout / independent: top-level ``rows`` or ``suite_b_rows``
  keyed by (case_id, config, column[, planner][, trial])
- Kind: top-level ``arms`` keyed by (case_id, arm)

Usage:
    python eval/harness/diff_freeze.py \\
        --baseline eval/results/latest.json \\
        --rerun /path/to/rerun/latest.json \\
        --out eval/results/reexec/suite-b-diff \\
        --label suite_b \\
        --env-json eval/results/reexec/env.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _git_head(repo: Path) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:  # noqa: BLE001
        return "unknown"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _cell_key_suite(row: dict[str, Any]) -> tuple[Any, ...]:
    return (
        row.get("case_id"),
        row.get("config") or row.get("arm"),
        row.get("column"),
        row.get("planner"),
        row.get("trial", 0),
    )


def _cell_key_kind(row: dict[str, Any]) -> tuple[Any, ...]:
    return (row.get("case_id"), row.get("arm"), None, None, 0)


def _extract_cells(payload: dict[str, Any]) -> dict[tuple[Any, ...], dict[str, Any]]:
    """Normalize freeze JSON into a cell map."""
    cells: dict[tuple[Any, ...], dict[str, Any]] = {}
    if isinstance(payload.get("arms"), dict):
        for arm_name, rows in payload["arms"].items():
            if not isinstance(rows, list):
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                enriched = dict(row)
                enriched.setdefault("arm", arm_name)
                key = _cell_key_kind(enriched)
                cells[key] = {
                    "harmed": bool(enriched.get("harmed")),
                    "applicable": True,
                    "raw": {
                        "case_id": enriched.get("case_id"),
                        "arm": enriched.get("arm"),
                        "harmed": enriched.get("harmed"),
                        "harms": enriched.get("harms"),
                        "surface": enriched.get("surface"),
                    },
                }
        return cells

    rows = payload.get("rows")
    if rows is None:
        rows = payload.get("suite_b_rows")
    if not isinstance(rows, list):
        raise SystemExit("freeze JSON has neither arms nor rows/suite_b_rows")

    for row in rows:
        if not isinstance(row, dict):
            continue
        key = _cell_key_suite(row)
        applicable = row.get("applicable", True)
        cells[key] = {
            "harmed": bool(row.get("harmed")) if applicable else False,
            "applicable": bool(applicable),
            "raw": {
                "case_id": row.get("case_id"),
                "config": row.get("config"),
                "column": row.get("column"),
                "planner": row.get("planner"),
                "trial": row.get("trial", 0),
                "harmed": row.get("harmed"),
                "applicable": applicable,
            },
        }
    return cells


def diff_cells(
    baseline: dict[tuple[Any, ...], dict[str, Any]],
    rerun: dict[tuple[Any, ...], dict[str, Any]],
) -> dict[str, Any]:
    only_baseline = sorted(set(baseline) - set(rerun))
    only_rerun = sorted(set(rerun) - set(baseline))
    shared = sorted(set(baseline) & set(rerun))
    mismatches: list[dict[str, Any]] = []
    for key in shared:
        b, r = baseline[key], rerun[key]
        if b["applicable"] != r["applicable"] or b["harmed"] != r["harmed"]:
            mismatches.append(
                {
                    "key": list(key),
                    "baseline": {"harmed": b["harmed"], "applicable": b["applicable"]},
                    "rerun": {"harmed": r["harmed"], "applicable": r["applicable"]},
                }
            )
    return {
        "baseline_cells": len(baseline),
        "rerun_cells": len(rerun),
        "shared_cells": len(shared),
        "only_in_baseline": [list(k) for k in only_baseline],
        "only_in_rerun": [list(k) for k in only_rerun],
        "mismatches": mismatches,
        "cell_diffs": len(only_baseline) + len(only_rerun) + len(mismatches),
    }


def render_md(report: dict[str, Any]) -> str:
    env = report.get("env") or {}
    lines = [
        f"# Freeze cell diff — {report.get('label', 'unlabeled')}",
        "",
        f"generated_at: {report.get('generated_at')}",
        f"baseline: `{report.get('baseline_path')}`",
        f"rerun: `{report.get('rerun_path')}`",
        "",
        "## Environment",
        "",
        f"- commit: `{env.get('commit', 'unknown')}`",
        f"- timezone: `{env.get('timezone', 'unset')}`",
        f"- postgres: `{env.get('postgres', 'unset')}`",
        f"- notes: {env.get('notes', '')}",
        "",
        "## Summary",
        "",
        f"- baseline cells: {report['baseline_cells']}",
        f"- rerun cells: {report['rerun_cells']}",
        f"- shared cells: {report['shared_cells']}",
        f"- **cell diffs: {report['cell_diffs']}** "
        f"(mismatches={len(report['mismatches'])}, "
        f"only_baseline={len(report['only_in_baseline'])}, "
        f"only_rerun={len(report['only_in_rerun'])})",
        "",
    ]
    if report["cell_diffs"] == 0:
        lines.append("All shared cells agree on `(applicable, harmed)`.")
        lines.append("")
        return "\n".join(lines)

    if report["mismatches"]:
        lines.extend(["## Harmed / applicable mismatches", ""])
        for item in report["mismatches"]:
            lines.append(
                f"- `{item['key']}`: baseline={item['baseline']} rerun={item['rerun']}"
            )
        lines.append("")
    if report["only_in_baseline"]:
        lines.extend(["## Only in baseline", ""])
        for key in report["only_in_baseline"]:
            lines.append(f"- `{key}`")
        lines.append("")
    if report["only_in_rerun"]:
        lines.extend(["## Only in re-run", ""])
        for key in report["only_in_rerun"]:
            lines.append(f"- `{key}`")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--rerun", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path, help="prefix without extension")
    parser.add_argument("--label", default="freeze")
    parser.add_argument("--env-json", type=Path, default=None)
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[2]
    env: dict[str, Any] = {
        "commit": _git_head(repo),
        "timezone": "UTC",
        "postgres": "unset",
        "notes": "",
    }
    if args.env_json and args.env_json.is_file():
        env.update(json.loads(args.env_json.read_text()))

    baseline_cells = _extract_cells(_load(args.baseline))
    rerun_cells = _extract_cells(_load(args.rerun))
    body = diff_cells(baseline_cells, rerun_cells)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "label": args.label,
        "baseline_path": str(args.baseline),
        "rerun_path": str(args.rerun),
        "env": env,
        **body,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    json_path = Path(str(args.out) + ".json")
    md_path = Path(str(args.out) + ".md")
    json_path.write_text(json.dumps(report, indent=2, default=str) + "\n")
    md_path.write_text(render_md(report))
    print(render_md(report))
    return 0 if report["cell_diffs"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
