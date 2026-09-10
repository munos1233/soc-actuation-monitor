"""Sweep the adversary set across mediator configurations and vendor columns.

One world is built per (configuration, column) pair, with the mediator switches
already in place before any service is constructed, and every case for that pair
runs inside it. Harm is whatever the case reported from world state; this module
only tabulates.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable, Sequence
from typing import Any

from app.eval_suite.cases import ALL_CASES
from app.eval_suite.chain import Injection, run_case
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
from app.eval_suite.substrate import substrate_context
from app.eval_suite.world import eval_world

ProgressHook = Callable[[str], None]


async def run_matrix(
    *,
    configs: Sequence[MonitorConfig] = ALL_CONFIGS,
    columns: Sequence[VendorColumn] = (VendorColumn.MOCK, VendorColumn.PSEUDO_LIVE),
    planners: Sequence[PlannerModel] = (PlannerModel.UNTRUSTED_PLANNER,),
    cases: Sequence[Injection] = ALL_CASES,
    progress: ProgressHook | None = None,
) -> list[dict[str, Any]]:
    """Run every (case, configuration, column, planner) combination."""
    rows: list[dict[str, Any]] = []
    for column in columns:
        scoped = [case for case in cases if case.runs_in(column.value)]
        if not scoped:
            continue
        for config in configs:
            for planner in planners:
                started = time.monotonic()
                with harness_context(config, column):
                    async with eval_world(column) as world:
                        async with substrate_context(world, config):
                            for case in scoped:
                                outcome = await run_case(
                                    world,
                                    case,
                                    config_name=config.name,
                                    planner=planner,
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
                        f"{len(scoped)} cases in {time.monotonic() - started:.1f}s"
                    )
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
    "render_markdown",
    "run_matrix",
    "substrate_table",
    "summarize",
    "unmediated_under_full",
]
