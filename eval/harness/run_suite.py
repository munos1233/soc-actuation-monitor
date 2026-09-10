"""Run the actuation-integrity evaluation.

Suite B drives adversaries A1–A5 at the system boundary — planner-authored
rows, vendor receipts, vendor observation answers, repeated dispatch — through
the production service chain against a real PostgreSQL, and scores harm from
database and vendor-side facts. Suite A runs the golden path under exactly the
same Full configuration and reports closure rate and over-block.

The suite needs a database and Redis it is allowed to write to. Never point it
at a deployment you care about::

    docker compose -p shadowtrace-eval up -d postgres redis   # ports of your choosing
    export DATABASE_URL=postgresql+asyncpg://shadowtrace:shadowtrace@localhost:55432/shadowtrace
    export REDIS_URL=redis://localhost:56379/0
    python eval/harness/run_suite.py --out eval/results

Subsets, for a quick signal::

    python eval/harness/run_suite.py --configs naive,full --columns mock --skip-gold
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.eval_suite.cases import ALL_CASES  # noqa: E402
from app.eval_suite.component import run_component_checks  # noqa: E402
from app.eval_suite.configs import (  # noqa: E402
    ALL_CONFIGS,
    CONFIGS,
    FULL,
    NAIVE,
    PlannerModel,
    VendorColumn,
)
from app.eval_suite.gold import (  # noqa: E402
    render_gold_markdown,
    run_gold,
    summarize_gold,
    usability_delta,
)
from app.eval_suite.runner import (  # noqa: E402
    leave_one_out_table,
    render_markdown,
    run_matrix,
    substrate_table,
    summarize,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--configs",
        default="all",
        help="comma-separated configuration names, or 'all' (default)",
    )
    parser.add_argument(
        "--columns",
        default="mock,pseudo_live",
        help="comma-separated vendor columns (default: both)",
    )
    parser.add_argument(
        "--cases",
        default="all",
        help="comma-separated case ids, or 'all' (default)",
    )
    parser.add_argument(
        "--planners",
        default="untrusted_planner,dead_playbook",
        help="comma-separated planner models (default: both, for the baseline)",
    )
    parser.add_argument("--skip-gold", action="store_true", help="skip suite A")
    parser.add_argument("--skip-suite-b", action="store_true", help="skip suite B")
    parser.add_argument(
        "--out",
        default="",
        help="directory for results (JSON + markdown); omit to print only",
    )
    parser.add_argument(
        "--export-cases",
        default="",
        help="write the case registry as JSON to this path and exit",
    )
    return parser.parse_args(argv)


def _case_registry() -> list[dict[str, Any]]:
    return [
        {
            "case_id": case.case_id,
            "adversary": case.adversary,
            "harm": case.harm,
            "expected_mediator": case.expected_mediator,
            "columns": list(case.columns),
            "description": case.description,
        }
        for case in ALL_CASES
    ]


async def _run(args: argparse.Namespace) -> int:
    configs = (
        list(ALL_CONFIGS)
        if args.configs == "all"
        else [CONFIGS[name.strip()] for name in args.configs.split(",") if name.strip()]
    )
    columns = [VendorColumn(name.strip()) for name in args.columns.split(",") if name.strip()]
    planners = [PlannerModel(name.strip()) for name in args.planners.split(",") if name.strip()]
    cases = (
        list(ALL_CASES)
        if args.cases == "all"
        else [case for case in ALL_CASES if case.case_id in set(args.cases.split(","))]
    )

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "columns": [column.value for column in columns],
        "configs": [config.name for config in configs],
        "planners": [planner.value for planner in planners],
        "case_registry": _case_registry(),
    }
    markdown: list[str] = ["# Actuation-integrity evaluation", ""]

    if not args.skip_suite_b:
        rows = await run_matrix(
            configs=configs,
            columns=columns,
            planners=planners,
            cases=cases,
            progress=lambda message: print(message, file=sys.stderr),
        )
        report["suite_b_rows"] = rows
        report["suite_b_summary"] = summarize(rows)
        report["leave_one_out"] = leave_one_out_table(
            [row for row in rows if row["planner"] == PlannerModel.UNTRUSTED_PLANNER.value]
        )
        markdown.append("## Suite B: boundary injection through the real chain")
        markdown.append("")
        markdown.append(
            render_markdown(
                [row for row in rows if row["planner"] == PlannerModel.UNTRUSTED_PLANNER.value]
            )
        )
        markdown.append("### leave-one-out: marginal harm of removing one mediator")
        markdown.append("")
        markdown.append("| configuration | mediator removed | harm | marginal |")
        markdown.append("|---|---|---|---|")
        for entry in report["leave_one_out"]:
            marginal = entry.get("marginal_harm")
            markdown.append(
                f"| {entry['config']} | {entry['removed'] or '—'} "
                f"| {entry['harmed']}/{entry['total']} "
                f"| {'—' if marginal is None else f'+{marginal}'} |"
            )
        markdown.append("")
        report["substrate_ablation"] = substrate_table(
            [row for row in rows if row["planner"] == PlannerModel.UNTRUSTED_PLANNER.value]
        )
        if len(report["substrate_ablation"]) > 1:
            markdown.append(
                "### substrate ablation: mechanisms with no production switch, "
                "weakened in the harness"
            )
            markdown.append("")
            markdown.append("| configuration | mechanisms weakened | harm | marginal |")
            markdown.append("|---|---|---|---|")
            for entry in report["substrate_ablation"]:
                marginal = entry.get("marginal_harm")
                markdown.append(
                    f"| {entry['config']} | {', '.join(entry['weakened']) or '—'} "
                    f"| {entry['harmed']}/{entry['total']} "
                    f"| {'—' if marginal is None else f'+{marginal}'} |"
                )
            markdown.append("")
        dead = [row for row in rows if row["planner"] == PlannerModel.DEAD_PLAYBOOK.value]
        if dead:
            markdown.append("## Baseline: dead playbook (no adaptive planner)")
            markdown.append("")
            markdown.append(render_markdown(dead))

    if not args.skip_gold:
        # The naive arm is the usability control: it says whether the mediators
        # cost benign closures, which is the only thing that makes the Full
        # closure rate meaningful.
        gold_rows = await run_gold(columns=columns, config=FULL)
        naive_rows = await run_gold(columns=columns, config=NAIVE)
        report["suite_a_rows"] = [*gold_rows, *naive_rows]
        report["suite_a_summary"] = {
            "full": summarize_gold(gold_rows),
            "naive": summarize_gold(naive_rows),
        }
        report["suite_a_usability_delta"] = usability_delta(gold_rows, naive_rows)
        markdown.append(
            render_gold_markdown(
                gold_rows,
                title="### suite A: golden path under the Full configuration",
            )
        )
        markdown.append(
            render_gold_markdown(
                naive_rows,
                title="### suite A control: same cases with every mediator unloaded",
            )
        )

    checks = await run_component_checks()
    report["component_checks"] = checks
    markdown.append("## Appendix: predicate-level checks (not mediation evidence)")
    markdown.append("")
    for check in checks:
        verdict = json.dumps({k: v for k, v in check.items() if k != "check"})
        markdown.append(f"- `{check['check']}`: {verdict}")
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
        (out_dir / f"run-{stamp}.md").write_text(rendered, encoding="utf-8")
        (out_dir / "latest.json").write_text(
            json.dumps(report, indent=2, default=str), encoding="utf-8"
        )
        (out_dir / "latest.md").write_text(rendered, encoding="utf-8")
        print(f"wrote {out_dir}/run-{stamp}.json", file=sys.stderr)
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    if args.export_cases:
        path = Path(args.export_cases)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_case_registry(), indent=2), encoding="utf-8")
        print(f"wrote {path}", file=sys.stderr)
        return 0
    return asyncio.run(_run(args))


if __name__ == "__main__":
    raise SystemExit(main())
