"""Run the actuation-integrity evaluation.

Suite B drives adversaries A0–A5 at the system boundary — planner-authored
rows, vendor receipts, vendor observation answers, repeated dispatch — through
the production service chain against a real PostgreSQL, and scores harm from
database and vendor-side facts. Suite A runs the golden path under exactly the
same Full configuration and reports closure rate and over-block.

The suite needs a database and Redis it is allowed to write to. Never point it
at a deployment you care about::

    docker compose -p actuation-evalchain up -d postgres redis   # ports of your choosing
    export DATABASE_URL='postgresql+asyncpg://<eval-owner>:<eval-owner>@localhost:55432/<eval-db>'
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
sys.path.insert(0, str(ROOT / "eval" / "harness"))
sys.path.insert(0, str(ROOT / "backend"))

from gitmeta import git_dirty, git_head  # noqa: E402


def _load_backend_env() -> str | None:
    """Read credentials from backend/.env for the real-planner arm only.

    Settings resolves its ``env_file`` relative to the working directory, and this
    CLI runs from the repository root, so the file the operator actually edits is
    invisible without this. It is loaded only when the run asks for a live
    provider: the default matrix must stay offline and reproducible, and silently
    switching every arm to a paid provider because a file exists would be a trap.
    Values already in the environment win, so a command line still overrides.
    """
    path = ROOT / "backend" / ".env"
    if not path.exists():
        return None
    import os

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        os.environ.setdefault(key.strip(), value.strip())
    return str(path)


from app.core.config import get_settings  # noqa: E402
from app.eval_suite.cases import ALL_CASES  # noqa: E402
from app.eval_suite.component import run_component_checks  # noqa: E402
from app.eval_suite.configs import (  # noqa: E402
    ALL_CONFIGS,
    CONFIGS,
    EXTERNAL_OPA,
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
from app.eval_suite.planner import LLMPlanner  # noqa: E402
from app.eval_suite.policy_engine import (  # noqa: E402
    ExternalPolicyEngine,
    PolicyEngineUnavailable,
)
from app.eval_suite.runner import (  # noqa: E402
    interaction_table,
    leave_one_out_table,
    pareto_table,
    planner_table,
    render_markdown,
    render_pareto_markdown,
    render_planner_markdown,
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
    parser.add_argument(
        "--trials",
        type=int,
        default=1,
        help=(
            "repetitions per case in the llm_planner arm (default 1); the scripted "
            "arms are deterministic and always run once"
        ),
    )
    parser.add_argument(
        "--llm-token-budget",
        type=int,
        default=0,
        help="stop authoring plans once this many provider tokens are spent (0 = no cap)",
    )
    parser.add_argument(
        "--llm-model",
        default="",
        help=(
            "override LLM_PRIMARY_MODEL for the llm_planner arm "
            "(default: the value already in the environment or backend/.env)"
        ),
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
        "commit": git_head(),
        "tree_dirty": git_dirty(),
        "columns": [column.value for column in columns],
        "configs": [config.name for config in configs],
        "planners": [planner.value for planner in planners],
        "case_registry": _case_registry(),
    }
    markdown: list[str] = ["# Actuation-integrity evaluation", ""]

    # The comparator needs to outlive both suites: Suite B measures the harm it
    # stops and Suite A measures what that costs, and one number without the other
    # is not a result.
    policy: ExternalPolicyEngine | None = None
    if any(config.external_policy for config in configs):
        policy = ExternalPolicyEngine()
        try:
            await policy.probe()
        except PolicyEngineUnavailable as exc:
            await policy.aclose()
            raise SystemExit(
                f"the external_opa arm needs a reachable OPA server: {exc}\n"
                "start one with: make paper-opa-up"
            ) from exc
        report["external_policy"] = {"url": policy.url}

    if not args.skip_suite_b:
        llm_planner: LLMPlanner | None = None
        if PlannerModel.LLM_PLANNER in planners:
            env_path = _load_backend_env()
            if args.llm_model:
                import os

                os.environ["LLM_PRIMARY_MODEL"] = args.llm_model
            get_settings.cache_clear()
            llm_planner = LLMPlanner(
                token_budget=args.llm_token_budget or None,
                model_name=args.llm_model or None,
            )
            if llm_planner.settings.llm_mode.strip().lower() == "mock":
                raise SystemExit(
                    "the llm_planner arm needs LLM_MODE=openai_compatible and provider "
                    f"credentials; loaded {env_path or 'no env file'} and still saw mock mode"
                )
            report["llm_planner"] = {
                "model": llm_planner.model_name,
                "trials": max(1, args.trials),
                "token_budget": args.llm_token_budget or None,
            }
        try:

            def _checkpoint(current: list[dict[str, Any]]) -> None:
                if not args.out:
                    return
                out_dir = Path(args.out)
                out_dir.mkdir(parents=True, exist_ok=True)
                (out_dir / "checkpoint.json").write_text(
                    json.dumps(current, indent=2, default=str),
                    encoding="utf-8",
                )

            rows = await run_matrix(
                configs=configs,
                columns=columns,
                planners=planners,
                cases=cases,
                progress=lambda message: print(message, file=sys.stderr),
                on_arm=_checkpoint,
                trials=args.trials,
                llm_planner=llm_planner,
                policy=policy,
            )
        finally:
            from app.eval_suite.planner_peer import shutdown_planner_peer

            shutdown_planner_peer()
            if llm_planner is not None:
                report.setdefault("llm_planner", {})["telemetry"] = llm_planner.telemetry.summary()
                await llm_planner.aclose()
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
        report["interaction"] = interaction_table(
            [row for row in rows if row["planner"] == PlannerModel.UNTRUSTED_PLANNER.value]
        )
        if len(report["interaction"]) > 1:
            markdown.append("### interaction pairs: close+verify and bind+egress")
            markdown.append("")
            markdown.append("| configuration | loaded | harm | marginal |")
            markdown.append("|---|---|---|---|")
            for entry in report["interaction"]:
                marginal = entry.get("marginal_harm")
                markdown.append(
                    f"| {entry['config']} | {', '.join(entry['loaded'])} "
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
        if len({row["planner"] for row in rows}) > 1 or any(
            row["planner"] == PlannerModel.LLM_PLANNER.value for row in rows
        ):
            report["planner_comparison"] = planner_table(rows)
            markdown.append("### planner arms: who authored the proposal")
            markdown.append("")
            markdown.append(render_planner_markdown(report["planner_comparison"]))
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
        comparator_rows: list[dict[str, Any]] = []
        if policy is not None:
            comparator_rows = await run_gold(columns=columns, config=EXTERNAL_OPA, policy=policy)
        report["suite_a_rows"] = [*gold_rows, *naive_rows, *comparator_rows]
        report["suite_a_summary"] = {
            "full": summarize_gold(gold_rows),
            "naive": summarize_gold(naive_rows),
        }
        if comparator_rows:
            report["suite_a_summary"]["external_opa"] = summarize_gold(comparator_rows)
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
        if comparator_rows:
            markdown.append(
                render_gold_markdown(
                    comparator_rows,
                    title=(
                        "### suite A comparator: same cases with an external policy "
                        "engine in place of the mediators"
                    ),
                )
            )
        if comparator_rows and not args.skip_suite_b:
            report["pareto"] = pareto_table(
                suite_a_rows=report["suite_a_rows"],
                suite_b_rows=[
                    row for row in rows if row["planner"] == PlannerModel.UNTRUSTED_PLANNER.value
                ],
            )
            markdown.append("### where each arm sits: benign closure against harm")
            markdown.append("")
            markdown.append(render_pareto_markdown(report["pareto"]))
            markdown.append("")

    if policy is not None:
        report.setdefault("external_policy", {}).update(policy.summary())
        await policy.aclose()

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
    import os

    os.environ.setdefault("PROCESS_ROLE", "actuation")
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
