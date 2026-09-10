"""Sweep the adversary set across mediator configurations and vendor columns.

One world is built per (configuration, column) pair, with the mediator switches
already in place before any service is constructed, and every case for that pair
runs inside it. Harm is whatever the case reported from world state; this module
only tabulates.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from app.eval_suite.cases import ALL_CASES
from app.eval_suite.chain import CaseOutcome, Injection, run_case
from app.eval_suite.configs import (
    ALL_CONFIGS,
    LEAVE_ONE_OUT_CONFIGS,
    SINGLE_GATE_CONFIGS,
    SUBSTRATE,
    SUBSTRATE_CONFIGS,
    MonitorConfig,
    PlannerModel,
    VendorColumn,
    harness_context,
)
from app.eval_suite.planner import LLMPlanner
from app.eval_suite.policy_engine import ExternalPolicyEngine, PolicyEngineOutboundGuard
from app.eval_suite.substrate import substrate_context
from app.eval_suite.world import eval_world

ProgressHook = Callable[[str], None]
ArmHook = Callable[[list[dict[str, Any]]], None]


async def run_matrix(
    *,
    configs: Sequence[MonitorConfig] = ALL_CONFIGS,
    columns: Sequence[VendorColumn] = (VendorColumn.MOCK, VendorColumn.PSEUDO_LIVE),
    planners: Sequence[PlannerModel] = (PlannerModel.UNTRUSTED_PLANNER,),
    cases: Sequence[Injection] = ALL_CASES,
    progress: ProgressHook | None = None,
    on_arm: ArmHook | None = None,
    trials: int = 1,
    llm_planner: LLMPlanner | None = None,
    policy: ExternalPolicyEngine | None = None,
) -> list[dict[str, Any]]:
    """Run every (case, configuration, column, planner) combination.

    ``trials`` repeats each case in the real-planner arm only. The scripted arms
    are deterministic, so repeating them would pad the denominator with copies of
    the same row and shrink an interval that was never uncertain.
    """
    if PlannerModel.LLM_PLANNER in planners and llm_planner is None:
        raise ValueError("planners includes llm_planner but no LLMPlanner was supplied")
    if any(config.external_policy for config in configs) and policy is None:
        raise ValueError("configs includes a comparator arm but no policy engine was supplied")
    rows: list[dict[str, Any]] = []
    for column in columns:
        scoped = [case for case in cases if case.runs_in(column.value)]
        if not scoped:
            continue
        for config in configs:
            for planner in planners:
                started = time.monotonic()
                reps = max(1, trials) if planner is PlannerModel.LLM_PLANNER else 1
                arm_policy = policy if config.external_policy else None
                guard_factory = (
                    (lambda inner, engine=arm_policy: PolicyEngineOutboundGuard(inner, engine))
                    if arm_policy is not None
                    else None
                )
                with harness_context(config, column):
                    async with eval_world(column, outbound_guard_factory=guard_factory) as world:
                        async with substrate_context(world, config):
                            for trial in range(reps):
                                for case in scoped:
                                    try:
                                        outcome = await run_case(
                                            world,
                                            case,
                                            config_name=config.name,
                                            planner=planner,
                                            llm_planner=llm_planner,
                                            policy=arm_policy,
                                            trial=trial,
                                        )
                                    except Exception as exc:  # noqa: BLE001
                                        # One case must not throw away an arm. The
                                        # planner run that motivated this used to
                                        # die on a vanished event row after two
                                        # hours, with nothing written.
                                        outcome = CaseOutcome(
                                            case_id=case.case_id,
                                            adversary=case.adversary,
                                            harm_kind=case.harm,
                                            config=config.name,
                                            column=world.column.value,
                                            planner=planner.value,
                                            trial=trial,
                                            applicable=False,
                                            harm_detail=(
                                                f"harness exception: {type(exc).__name__}: {exc}"
                                            ),
                                            notes={"harness_exception": repr(exc)[:500]},
                                        )
                                        if progress is not None:
                                            progress(
                                                f"  {case.case_id} trial={trial} "
                                                f"raised {type(exc).__name__}"
                                            )
                                    row = outcome.as_row()
                                    row["expected_mediator"] = case.expected_mediator
                                    row["mediators_loaded"] = list(config.loaded())
                                    row["substrate_removed"] = list(config.substrate_removed())
                                    row["description"] = case.description
                                    rows.append(row)
                if progress is not None:
                    progress(
                        f"{column.value}/{config.name}/{planner.value}: "
                        f"{len(scoped) * reps} executions in {time.monotonic() - started:.1f}s"
                    )
                if on_arm is not None:
                    on_arm(rows)
    return rows


def applicable(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Rows the arm could actually mount; see ``Injection.applies_to``."""
    return [row for row in rows if row.get("applicable", True)]


def harm_rate(rows: Iterable[dict[str, Any]]) -> tuple[int, int]:
    total = 0
    harmed = 0
    for row in applicable(rows):
        total += 1
        harmed += 1 if row["harmed"] else 0
    return harmed, total


def summarize(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate harm by configuration, adversary, column and planner."""
    by_config: dict[str, dict[str, Any]] = {}
    for row in applicable(rows):
        bucket = by_config.setdefault(
            row["config"],
            {"harmed": 0, "total": 0, "by_adversary": {}, "by_column": {}},
        )
        bucket["total"] += 1
        bucket["harmed"] += 1 if row["harmed"] else 0
        adversary = bucket["by_adversary"].setdefault(row["adversary"], {"harmed": 0, "total": 0})
        adversary["total"] += 1
        adversary["harmed"] += 1 if row["harmed"] else 0
        column = bucket["by_column"].setdefault(row["column"], {"harmed": 0, "total": 0})
        column["total"] += 1
        column["harmed"] += 1 if row["harmed"] else 0
    return {
        "by_config": by_config,
        "unmediated_under_full": unmediated_under_full(rows),
        "not_applicable": [
            {
                "case_id": row["case_id"],
                "adversary": row["adversary"],
                "planner": row["planner"],
                "reason": row["harm_detail"],
            }
            for row in rows
            if not row.get("applicable", True) and row["config"] == "full"
        ],
    }


def unmediated_under_full(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Cases whose harm still happened with every mediator loaded.

    This list is the suite's own falsification record. It is reported, never
    suppressed: a non-empty entry means the claimed mediator does not in fact
    mediate that path.
    """
    return [
        {
            "case_id": row["case_id"],
            "adversary": row["adversary"],
            "column": row["column"],
            "planner": row["planner"],
            "harm_kind": row["harm_kind"],
            "harm_detail": row["harm_detail"],
            "expected_mediator": row.get("expected_mediator"),
        }
        for row in applicable(rows)
        if row["config"] == "full" and row["harmed"]
    ]


def leave_one_out_table(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Per-mediator marginal contribution: full vs full-minus-one."""
    full_harm, full_total = harm_rate(r for r in rows if r["config"] == "full")
    table = [
        {
            "config": "full",
            "removed": None,
            "harmed": full_harm,
            "total": full_total,
        }
    ]
    for config in LEAVE_ONE_OUT_CONFIGS:
        harmed, total = harm_rate(r for r in rows if r["config"] == config.name)
        if total == 0:
            continue
        removed = next(
            mediator
            for mediator in ("close", "bind", "verify", "egress")
            if not getattr(config, mediator)
        )
        table.append(
            {
                "config": config.name,
                "removed": removed,
                "harmed": harmed,
                "total": total,
                "marginal_harm": harmed - full_harm,
            }
        )
    return table


def substrate_table(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Marginal harm of weakening one mechanism that has no production switch.

    Separate from ``leave_one_out_table`` on purpose. Those rows unload a gate the
    code can unload; these weaken the substrate underneath it, and merging the two
    would suggest the system has seven switches. It has four.
    """
    full_harm, full_total = harm_rate(r for r in rows if r["config"] == "full")
    table = [{"config": "full", "weakened": [], "harmed": full_harm, "total": full_total}]
    for config in SUBSTRATE_CONFIGS:
        harmed, total = harm_rate(r for r in rows if r["config"] == config.name)
        if total == 0:
            continue
        table.append(
            {
                "config": config.name,
                "weakened": [m for m in SUBSTRATE if not getattr(config, m)],
                "harmed": harmed,
                "total": total,
                "marginal_harm": harmed - full_harm,
            }
        )
    return table


def wilson_interval(harmed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Wilson rather than normal-approximation because the counts this suite
    produces are small and cluster at 0 and 1, where the normal interval leaves
    the unit interval and reports zero width for a zero count.
    """
    if total <= 0:
        return (0.0, 0.0)
    phat = harmed / total
    denominator = 1.0 + z * z / total
    centre = phat + z * z / (2.0 * total)
    spread = z * math.sqrt(phat * (1.0 - phat) / total + z * z / (4.0 * total * total))
    low = (centre - spread) / denominator
    high = (centre + spread) / denominator
    return (max(0.0, round(low, 4)), min(1.0, round(high, 4)))


def planner_table(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Harm rate per (planner, configuration) with an interval and a loss count.

    ``lost`` is the number of executions the arm could not score because the
    provider refused to answer. Those rows are outside the denominator, so the
    count has to travel with the rate or the rate is not interpretable.
    """
    table: list[dict[str, Any]] = []
    for planner in sorted({row["planner"] for row in rows}):
        for config in sorted({row["config"] for row in rows if row["planner"] == planner}):
            scoped = [row for row in rows if row["planner"] == planner and row["config"] == config]
            harmed, total = harm_rate(scoped)
            lost = sum(1 for row in scoped if "planner_unavailable" in (row.get("notes") or {}))
            low, high = wilson_interval(harmed, total)
            table.append(
                {
                    "planner": planner,
                    "config": config,
                    "harmed": harmed,
                    "total": total,
                    "rate": round(harmed / total, 4) if total else None,
                    "wilson_95": [low, high],
                    "lost_to_provider": lost,
                }
            )
    return table


def render_planner_markdown(table: Sequence[dict[str, Any]]) -> str:
    lines = [
        "| planner | configuration | harm | rate | 95% Wilson | lost to provider |",
        "|---|---|---|---|---|---|",
    ]
    for entry in table:
        low, high = entry["wilson_95"]
        rate = "—" if entry["rate"] is None else f"{entry['rate']:.2f}"
        lines.append(
            f"| {entry['planner']} | {entry['config']} | {entry['harmed']}/{entry['total']} "
            f"| {rate} | [{low:.2f}, {high:.2f}] | {entry['lost_to_provider']} |"
        )
    return "\n".join(lines)


def pareto_table(
    *,
    suite_a_rows: Sequence[dict[str, Any]],
    suite_b_rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Benign closure against harm, one row per arm.

    Neither number means anything alone. A configuration that refuses every close
    has no harm and no use; one that closes everything has full utility and no
    integrity. The pair is the result.
    """
    arms = sorted({str(row["config"]) for row in suite_a_rows})
    table: list[dict[str, Any]] = []
    for arm in arms:
        benign = [row for row in suite_a_rows if row["config"] == arm]
        closed = sum(1 for row in benign if row["closed"])
        adversarial = list(applicable(row for row in suite_b_rows if row["config"] == arm))
        harmed = sum(1 for row in adversarial if row["harmed"])
        table.append(
            {
                "config": arm,
                "benign_closed": closed,
                "benign_total": len(benign),
                "benign_rate": (closed / len(benign)) if benign else None,
                "harmed": harmed,
                "harm_total": len(adversarial),
                "harm_rate": (harmed / len(adversarial)) if adversarial else None,
                "harm_wilson_95": wilson_interval(harmed, len(adversarial)),
            }
        )
    return table


def render_pareto_markdown(table: Sequence[dict[str, Any]]) -> str:
    lines = [
        "| arm | benign closed (Suite A) | harm (Suite B) | harm rate | 95% Wilson |",
        "|---|---|---|---|---|",
    ]
    for entry in table:
        rate = "—" if entry["harm_rate"] is None else f"{entry['harm_rate']:.2f}"
        low, high = entry["harm_wilson_95"]
        lines.append(
            f"| {entry['config']} "
            f"| {entry['benign_closed']}/{entry['benign_total']} "
            f"| {entry['harmed']}/{entry['harm_total']} "
            f"| {rate} | [{low:.2f}, {high:.2f}] |"
        )
    return "\n".join(lines)


def render_markdown(rows: Sequence[dict[str, Any]]) -> str:
    """Ablation table: harm count per configuration per adversary, per column."""
    configs = [c.name for c in (*SINGLE_GATE_CONFIGS, *LEAVE_ONE_OUT_CONFIGS, *SUBSTRATE_CONFIGS)]
    present = [name for name in configs if any(r["config"] == name for r in rows)]
    adversaries = sorted({r["adversary"] for r in rows})
    lines: list[str] = []
    for column in sorted({r["column"] for r in rows}):
        lines.append(f"### vendor column: {column}")
        lines.append("")
        header = "| configuration | " + " | ".join(adversaries) + " | total |"
        lines.append(header)
        lines.append("|" + "---|" * (len(adversaries) + 2))
        for name in present:
            cells: list[str] = []
            for adversary in adversaries:
                harmed, total = harm_rate(
                    r
                    for r in rows
                    if r["config"] == name and r["column"] == column and r["adversary"] == adversary
                )
                cells.append(f"{harmed}/{total}" if total else "-")
            harmed, total = harm_rate(
                r for r in rows if r["config"] == name and r["column"] == column
            )
            lines.append(f"| {name} | " + " | ".join(cells) + f" | {harmed}/{total} |")
        lines.append("")
    unmediated = unmediated_under_full(rows)
    lines.append("### harm still reachable with every mediator loaded")
    lines.append("")
    if not unmediated:
        lines.append("None.")
    else:
        lines.append("| case | column | harm | detail |")
        lines.append("|---|---|---|---|")
        for item in unmediated:
            lines.append(
                f"| {item['case_id']} | {item['column']} | {item['harm_kind']} "
                f"| {item['harm_detail']} |"
            )
    lines.append("")
    skipped = sorted({r["case_id"] for r in rows if not r.get("applicable", True)})
    if skipped:
        lines.append(
            "Excluded from every cell above as not applicable to this arm "
            f"({len(skipped)} cases): {', '.join(skipped)}."
        )
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "applicable",
    "harm_rate",
    "leave_one_out_table",
    "pareto_table",
    "planner_table",
    "render_markdown",
    "render_pareto_markdown",
    "render_planner_markdown",
    "run_matrix",
    "substrate_table",
    "summarize",
    "unmediated_under_full",
    "wilson_interval",
]
