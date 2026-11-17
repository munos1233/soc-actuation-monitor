#!/usr/bin/env python3
"""Mutation kill-rate runner. FULL only; never pooled with the 57 freeze.

Each mutant is applied with a harness patch (production imports nothing from
``mutants.py``), then Suite B 57 + B2 + golden g1-g4 + g5-g11 run under
full in both vendor columns.

Usage:
    python eval/harness/run_mutation.py [--out eval/results/mutation]
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
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.eval_suite.b2_cases import B2_CASES  # noqa: E402
from app.eval_suite.cases import ALL_CASES  # noqa: E402
from app.eval_suite.configs import FULL, PlannerModel, VendorColumn  # noqa: E402
from app.eval_suite.gold import GOLDEN_CASES, run_gold  # noqa: E402
from app.eval_suite.gold_ext import GOLDEN_EXT_CASES  # noqa: E402
from app.eval_suite.mutants import MUTANTS, Mutant, apply_mutant  # noqa: E402
from app.eval_suite.runner import run_matrix  # noqa: E402

ATTACK_CASES = (*ALL_CASES, *B2_CASES)
GOLDEN_ALL = (*GOLDEN_CASES, *GOLDEN_EXT_CASES)
ATTACK_IDS = {case.case_id for case in ATTACK_CASES}
GOLDEN_IDS = {case.case_id for case in GOLDEN_ALL}


def _classify(
    mutant: Mutant,
    attack_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    *,
    baseline_harmed: set[tuple[str, str]],
    baseline_closed: set[tuple[str, str]],
) -> dict[str, Any]:
    """Kill relative to an unmutated FULL pass, not relative to a stale freeze.

    A golden that already failed under full cannot over-strict-kill a mutant.
    An attack that already harmed under full cannot harm-kill a mutant.
    """
    harm_kills = sorted(
        {
            row["case_id"]
            for row in attack_rows
            if row.get("applicable")
            and row.get("harmed")
            and (row["case_id"], row.get("column")) not in baseline_harmed
        }
    )
    over_strict = sorted(
        {
            row["case_id"]
            for row in gold_rows
            if not row.get("closed")
            and (row["case_id"], row.get("column")) in baseline_closed
        }
    )
    gold_closed = [row for row in gold_rows if row.get("closed")]
    collapse = bool(baseline_closed) and not any(
        (row["case_id"], row.get("column")) in baseline_closed and row.get("closed")
        for row in gold_rows
    )
    killed = bool(harm_kills or over_strict)
    if mutant.expected_survivor:
        status = "survivor" if not killed else "unexpected_kill"
    elif killed:
        status = "killed"
    else:
        status = "survivor"
    return {
        "mutant_id": mutant.mutant_id,
        "family": mutant.family,
        "kind": mutant.kind,
        "expected_survivor": mutant.expected_survivor,
        "status": status,
        "harm_kills": harm_kills,
        "over_strict_kills": over_strict,
        "named_killers": list(mutant.killers),
        "named_killers_hit": [item for item in mutant.killers if item in harm_kills or item in over_strict],
        "golden_collapse": collapse,
        "attack_rows": len(attack_rows),
        "gold_rows": len(gold_rows),
    }


def render(results: list[dict[str, Any]]) -> str:
    killed = sum(1 for item in results if item["status"] == "killed")
    survivors = [item for item in results if item["status"] == "survivor"]
    unexpected = [item for item in results if item["status"] == "unexpected_kill"]
    lines = [
        "# Mutation kill rate (FULL only)",
        "",
        "Never pooled with Suite B 57. Production code does not import these",
        "mutants. Kill is relative to an unmutated FULL pass: harm-kill is an",
        "attack FULL prevents that the mutant lets through; over-strict-kill is",
        "a golden FULL closes that the mutant refuses.",
        "",
        f"killed {killed}/{len(results)}  "
        f"survivors {len(survivors)}  unexpected {len(unexpected)}",
        "",
        "| mutant | family | status | harm-kills | over-strict | named hit |",
        "|---|---|---|---|---|---|",
    ]
    for item in results:
        lines.append(
            "| `{id}` | {fam} | {st} | {hk} | {os} | {nh} |".format(
                id=item["mutant_id"],
                fam=item["family"],
                st=item["status"],
                hk=", ".join(f"`{c}`" for c in item["harm_kills"]) or "—",
                os=", ".join(f"`{c}`" for c in item["over_strict_kills"]) or "—",
                nh=", ".join(f"`{c}`" for c in item["named_killers_hit"]) or "—",
            )
        )
    lines.append("")
    if any(item["golden_collapse"] for item in results):
        lines.append(
            "A mutant refused every golden case; treat that row as a suspected "
            "over-strict collapse, not a precision kill."
        )
        lines.append("")
    return "\n".join(lines)


async def _baseline(
    columns: tuple[VendorColumn, ...],
) -> tuple[set[tuple[str, str]], set[tuple[str, str]]]:
    attack_rows = await run_matrix(
        configs=(FULL,),
        columns=columns,
        planners=(PlannerModel.UNTRUSTED_PLANNER,),
        cases=ATTACK_CASES,
    )
    gold_rows = await run_gold(config=FULL, columns=columns, cases=GOLDEN_ALL)
    harmed = {
        (row["case_id"], row.get("column"))
        for row in attack_rows
        if row.get("applicable") and row.get("harmed")
    }
    closed = {
        (row["case_id"], row.get("column"))
        for row in gold_rows
        if row.get("closed")
    }
    return harmed, closed


async def run_one(
    mutant: Mutant,
    columns: tuple[VendorColumn, ...],
    *,
    baseline_harmed: set[tuple[str, str]],
    baseline_closed: set[tuple[str, str]],
) -> dict[str, Any]:
    with apply_mutant(mutant):
        attack_rows = await run_matrix(
            configs=(FULL,),
            columns=columns,
            planners=(PlannerModel.UNTRUSTED_PLANNER,),
            cases=ATTACK_CASES,
        )
        gold_rows = await run_gold(config=FULL, columns=columns, cases=GOLDEN_ALL)
    return _classify(
        mutant,
        attack_rows,
        gold_rows,
        baseline_harmed=baseline_harmed,
        baseline_closed=baseline_closed,
    )


async def _run(selected: tuple[Mutant, ...], columns: tuple[VendorColumn, ...]) -> dict[str, Any]:
    print("unmutated FULL baseline ...", flush=True)
    baseline_harmed, baseline_closed = await _baseline(columns)
    print(
        f"  baseline harmed={len(baseline_harmed)} closed={len(baseline_closed)}",
        flush=True,
    )
    results: list[dict[str, Any]] = []
    for mutant in selected:
        print(f"mutant {mutant.mutant_id} ...", flush=True)
        results.append(
            await run_one(
                mutant,
                columns,
                baseline_harmed=baseline_harmed,
                baseline_closed=baseline_closed,
            )
        )
        print(
            f"  {results[-1]['status']} harm={results[-1]['harm_kills']} "
            f"over={results[-1]['over_strict_kills']}",
            flush=True,
        )
    killed = sum(1 for item in results if item["status"] == "killed")
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "pooled_with_57": False,
        "full_only": True,
        "baseline_subtracted": True,
        "columns": [column.value for column in columns],
        "attack_case_ids": [case.case_id for case in ATTACK_CASES],
        "golden_case_ids": [case.case_id for case in GOLDEN_ALL],
        "baseline_harmed": len(baseline_harmed),
        "baseline_closed": len(baseline_closed),
        "killed": killed,
        "total": len(results),
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "mutation"))
    parser.add_argument("--mutants", default="", help="comma-separated mutant ids")
    parser.add_argument(
        "--columns",
        default="mock,pseudo_live",
        help="vendor columns (mock,pseudo_live)",
    )
    args = parser.parse_args(argv)
    selected = MUTANTS
    if args.mutants.strip():
        wanted = {item.strip() for item in args.mutants.split(",") if item.strip()}
        selected = tuple(item for item in MUTANTS if item.mutant_id in wanted)
        missing = wanted - {item.mutant_id for item in selected}
        if missing:
            print(f"unknown mutants: {sorted(missing)}", file=sys.stderr)
            return 2
    columns = tuple(VendorColumn(item.strip()) for item in args.columns.split(",") if item.strip())
    payload = asyncio.run(_run(selected, columns))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    text = render(payload["results"])
    (out / f"run-{stamp}.json").write_text(json.dumps(payload, indent=2) + "\n")
    (out / "latest.json").write_text(json.dumps(payload, indent=2) + "\n")
    (out / f"run-{stamp}.md").write_text(text + "\n")
    (out / "latest.md").write_text(text + "\n")
    print(text)
    unexpected = [item for item in payload["results"] if item["status"] == "unexpected_kill"]
    unkilled = [
        item
        for item in payload["results"]
        if item["status"] == "survivor" and not item["expected_survivor"]
    ]
    if unexpected or unkilled:
        print(
            f"{len(unkilled)} unkilled, {len(unexpected)} unexpected; see {out}/latest.md",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
