#!/usr/bin/env python3
"""Fill the four missing 2-gate cells of the 2^4 mediator lattice.

Default: project from the frozen Suite B single-gate rows under the
already-claimed monotonicity (harm survives a pair iff it survives both
singles). Validated against the two frozen interaction pairs.

    python eval/harness/run_lattice.py --out eval/results/lattice

--live runs the four configs through the production chain (needs DATABASE_URL).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.eval_suite.configs import LATTICE_CONFIGS  # noqa: E402

PAIRS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("close_and_verify", ("close", "verify")),
    ("bind_and_egress", ("bind", "egress")),
    ("close_and_bind", ("close", "bind")),
    ("close_and_egress", ("close", "egress")),
    ("bind_and_verify", ("bind", "verify")),
    ("verify_and_egress", ("verify", "egress")),
)
FROZEN_PAIRS = {"close_and_verify", "bind_and_egress"}
MISSING_PAIRS = {name for name, _ in PAIRS} - FROZEN_PAIRS


def _load_rows(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return list(payload.get("suite_b_rows") or [])


def _index(
    rows: list[dict[str, Any]],
) -> dict[tuple[str, str, str, str], bool]:
    out: dict[tuple[str, str, str, str], bool] = {}
    for row in rows:
        if row.get("planner") != "untrusted_planner" or not row.get("applicable"):
            continue
        key = (row["case_id"], row["column"], row["config"], row["adversary"])
        out[key] = bool(row["harmed"])
    return out


def project_pair(
    index: dict[tuple[str, str, str, str], bool],
    gates: tuple[str, ...],
    column: str,
) -> dict[str, tuple[int, int]]:
    singles = [f"{g}_only" for g in gates]
    by_adv: dict[str, list[bool]] = defaultdict(list)
    cases = {
        (case_id, adv)
        for case_id, col, cfg, adv in index
        if col == column and cfg == singles[0]
    }
    for case_id, adv in sorted(cases):
        survived = True
        for cfg in singles:
            key = (case_id, column, cfg, adv)
            if key not in index:
                survived = False
                break
            survived = survived and index[key]
        by_adv[adv].append(survived)
    return {
        adv: (sum(flags), len(flags)) for adv, flags in sorted(by_adv.items())
    }


def validate_frozen(
    index: dict[tuple[str, str, str, str], bool], rows: list[dict[str, Any]]
) -> list[str]:
    """Projected pair must match the frozen interaction cells."""
    mismatches: list[str] = []
    actual: dict[tuple[str, str, str], bool] = {}
    for row in rows:
        if row.get("planner") != "untrusted_planner" or not row.get("applicable"):
            continue
        if row["config"] not in FROZEN_PAIRS:
            continue
        actual[(row["case_id"], row["column"], row["config"])] = bool(row["harmed"])
    for name, gates in PAIRS:
        if name not in FROZEN_PAIRS:
            continue
        singles = [f"{g}_only" for g in gates]
        for (case_id, column, cfg, adv), harmed in index.items():
            if cfg != singles[0]:
                continue
            predicted = all(index.get((case_id, column, s, adv), False) for s in singles)
            got = actual.get((case_id, column, name))
            if got is None:
                continue
            if bool(predicted) != bool(got):
                mismatches.append(f"{name} {column} {case_id}: pred={predicted} frozen={got}")
    return mismatches


def render_markdown(
    projected: dict[str, dict[str, dict[str, tuple[int, int]]]],
    mismatches: list[str],
    live: dict[str, Any] | None,
) -> str:
    lines = [
        "# 2^4 mediator lattice — missing 2-gate cells",
        "",
        "Projection: harm survives a pair iff it survives both single-gate",
        "rows (monotone union). Frozen pairs validate the projector.",
        "",
    ]
    if mismatches:
        lines.append("Projector mismatches against frozen pairs:")
        lines.extend(f"- {m}" for m in mismatches)
        lines.append("")
    else:
        lines.append("Projector matches frozen `close_and_verify` and `bind_and_egress`.")
        lines.append("")
    for column in ("mock", "pseudo_live"):
        lines.append(f"## {column}")
        lines.append("")
        lines.append("| pair | A1 | A2 | A3 | A4 | A5 | total |")
        lines.append("|---|---|---|---|---|---|---|")
        for name, _gates in PAIRS:
            cells = projected[column][name]
            parts = []
            harmed = 0
            n = 0
            for adv in ("A1", "A2", "A3", "A4", "A5"):
                h, d = cells.get(adv, (0, 0))
                parts.append(f"{h}/{d}" if d else "—")
                harmed += h
                n += d
            mark = "" if name in FROZEN_PAIRS else " (new)"
            lines.append(
                f"| `{name}`{mark} | " + " | ".join(parts) + f" | {harmed}/{n} |"
            )
        lines.append("")
    if live:
        diffs = live.get("vs_projection") if isinstance(live, dict) else None
        if diffs:
            lines.append("Live ≠ projection (recorded, projector not rewritten):")
            lines.extend(f"- {item}" for item in diffs)
            lines.append("")
        else:
            lines.append("Live production chain matches the monotone projection.")
            lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", default=str(REPO_ROOT / "eval" / "results" / "latest.json"))
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "lattice"))
    parser.add_argument(
        "--live",
        action="store_true",
        help="run LATTICE_CONFIGS on the production chain (needs DATABASE_URL)",
    )
    parser.add_argument(
        "--project-only",
        action="store_true",
        help="explicit alias for the default projection path (unit tests)",
    )
    args = parser.parse_args(argv)
    rows = _load_rows(Path(args.matrix))
    index = _index(rows)
    mismatches = validate_frozen(index, rows)
    projected: dict[str, dict[str, dict[str, tuple[int, int]]]] = {}
    for column in ("mock", "pseudo_live"):
        projected[column] = {
            name: project_pair(index, gates, column) for name, gates in PAIRS
        }
    live_payload: dict[str, Any] | None = None
    live_vs_proj: list[str] = []
    if args.live:
        from app.eval_suite.configs import PlannerModel, VendorColumn
        from app.eval_suite.runner import run_matrix

        import asyncio

        live_rows = asyncio.run(
            run_matrix(
                configs=LATTICE_CONFIGS,
                columns=(VendorColumn.MOCK, VendorColumn.PSEUDO_LIVE),
                planners=(PlannerModel.UNTRUSTED_PLANNER,),
            )
        )
        live_index = _index(live_rows)
        for name, gates in PAIRS:
            if name not in MISSING_PAIRS:
                continue
            for column in ("mock", "pseudo_live"):
                pred = project_pair(index, gates, column)
                for adv, (h, d) in pred.items():
                    live_flags = [
                        harmed
                        for (case_id, col, cfg, ad), harmed in live_index.items()
                        if col == column and cfg == name and ad == adv
                    ]
                    if not live_flags:
                        continue
                    live_h, live_d = sum(live_flags), len(live_flags)
                    if (live_h, live_d) != (h, d):
                        live_vs_proj.append(
                            f"{name} {column} {adv}: live={live_h}/{live_d} projected={h}/{d}"
                        )
        live_payload = {
            "method": "production_chain",
            "configs": [c.name for c in LATTICE_CONFIGS],
            "rows": live_rows,
            "vs_projection": live_vs_proj,
        }
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "method": "monotone_projection_from_single_gate"
        if not args.live
        else "live_production_chain_plus_projection",
        "missing_pairs": sorted(MISSING_PAIRS),
        "projector_mismatches": mismatches,
        "projected": {
            column: {
                name: {adv: f"{h}/{d}" for adv, (h, d) in cells.items()}
                for name, cells in pairs.items()
            }
            for column, pairs in projected.items()
        },
        "live": live_payload,
        "live_vs_projection": live_vs_proj,
    }
    rendered = render_markdown(projected, mismatches, live_payload)
    print(rendered)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "latest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (out / "latest.md").write_text(rendered + "\n", encoding="utf-8")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
