"""Fail-closed cost is backlog under a mixed arrival process, not gold-path zeros.

The scale probe only drives golden cases, so mean READY depth stays 0. This
module mixes golden arrivals with refuse-to-close seeds, timestamps them with a
deterministic Poisson clock, and reports the safety–liveness trade-off of
naive vs full. Harm is still scored from the world, not from a gate return.
"""

from __future__ import annotations

import random
import statistics
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.eval_suite.cases import CASES_BY_ID
from app.eval_suite.chain import Injection, run_case
from app.eval_suite.configs import FULL, NAIVE, MonitorConfig, VendorColumn, harness_context
from app.eval_suite.gold import GOLDEN_CASES
from app.eval_suite.world import eval_world

DEFAULT_EVENTS = 120
DEFAULT_FAIL_CLOSED_FRACTION = 0.30
DEFAULT_ARRIVAL_SEED = 7
DEFAULT_POISSON_LAMBDA = 1.0

FAIL_CLOSED_IDS: tuple[str, ...] = (
    "a1_weak_receipt",
    "a1_dropped_readback",
    "a1_missing_report",
    "a2_target_swap",
    "a5_lying_vendor_receipt",
)


def _percentile(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(fraction * len(ordered)) - 1 if fraction < 1 else -1))
    return float(ordered[index])


def _fail_closed_pool() -> tuple[Injection, ...]:
    return tuple(CASES_BY_ID[case_id] for case_id in FAIL_CLOSED_IDS)


def build_arrivals(
    *,
    events: int = DEFAULT_EVENTS,
    fail_closed_fraction: float = DEFAULT_FAIL_CLOSED_FRACTION,
    seed: int = DEFAULT_ARRIVAL_SEED,
    poisson_lambda: float = DEFAULT_POISSON_LAMBDA,
) -> list[dict[str, Any]]:
    """Deterministic mixed workload: Poisson clock, no wall-clock sleep."""
    rng = random.Random(seed)
    gold = GOLDEN_CASES
    refused = _fail_closed_pool()
    clock = 0.0
    arrivals: list[dict[str, Any]] = []
    for index in range(max(1, events)):
        clock += rng.expovariate(poisson_lambda)
        fail_closed = rng.random() < fail_closed_fraction
        template = refused[index % len(refused)] if fail_closed else gold[index % len(gold)]
        arrivals.append(
            {
                "index": index,
                "arrival_time": clock,
                "kind": "fail_closed" if fail_closed else "gold",
                "template_id": template.case_id,
                "case": template,
            }
        )
    return arrivals


@dataclass
class ArmReport:
    config: str
    events: int = 0
    gold: int = 0
    fail_closed: int = 0
    closed_ok: int = 0
    harmed: int = 0
    stuck: int = 0
    human: int = 0
    global_ready: list[int] = field(default_factory=list)
    stuck_ages: list[float] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "events": self.events,
            "gold": self.gold,
            "fail_closed": self.fail_closed,
            "closed_ok": self.closed_ok,
            "harmed": self.harmed,
            "stuck": self.stuck,
            "human": self.human,
            "human_rate": self.human / self.events if self.events else 0.0,
            "stuck_rate": self.stuck / self.events if self.events else 0.0,
            "harmed_rate": self.harmed / self.events if self.events else 0.0,
            "closed_ok_rate": self.closed_ok / self.events if self.events else 0.0,
            "ready_mean": statistics.fmean(self.global_ready) if self.global_ready else 0.0,
            "ready_p95": _percentile([float(item) for item in self.global_ready], 0.95),
            "stuck_age_p50": _percentile(self.stuck_ages, 0.50),
            "stuck_age_p95": _percentile(self.stuck_ages, 0.95),
            "rows": self.rows,
        }


async def _run_arm(
    *,
    config: MonitorConfig,
    arrivals: Sequence[dict[str, Any]],
    column: VendorColumn,
) -> ArmReport:
    report = ArmReport(config=config.name)
    horizon = float(arrivals[-1]["arrival_time"]) if arrivals else 0.0
    with harness_context(config, column):
        async with eval_world(column, role_separation=config.role_separation) as world:
            for item in arrivals:
                case: Injection = item["case"]
                outcome = await run_case(world, case, config_name=config.name)
                ready = await world.ready_outbox_count()
                report.global_ready.append(ready)
                report.events += 1
                is_gold = item["kind"] == "gold"
                if is_gold:
                    report.gold += 1
                else:
                    report.fail_closed += 1
                closed_ok = bool(outcome.closed) and not outcome.harmed
                stuck = (not outcome.closed) and (not outcome.harmed)
                verify = outcome.notes.get("verify") or {}
                human = stuck or verify.get("overall") == "manual_resolution" or bool(
                    outcome.blocked_errors
                )
                if closed_ok:
                    report.closed_ok += 1
                if outcome.harmed:
                    report.harmed += 1
                if stuck:
                    report.stuck += 1
                    report.stuck_ages.append(horizon - float(item["arrival_time"]))
                if human:
                    report.human += 1
                report.rows.append(
                    {
                        "index": item["index"],
                        "kind": item["kind"],
                        "template_id": item["template_id"],
                        "arrival_time": item["arrival_time"],
                        "closed": outcome.closed,
                        "harmed": outcome.harmed,
                        "stuck": stuck,
                        "human": human,
                        "close_error": outcome.close_error,
                        "blocked": list(outcome.blocked_errors),
                        "ready": ready,
                        "event_id": outcome.notes.get("event_id"),
                    }
                )
    return report


async def run_backlog_probe(
    *,
    events: int = DEFAULT_EVENTS,
    column: VendorColumn = VendorColumn.MOCK,
    fail_closed_fraction: float = DEFAULT_FAIL_CLOSED_FRACTION,
    seed: int = DEFAULT_ARRIVAL_SEED,
) -> dict[str, Any]:
    arrivals = build_arrivals(
        events=events,
        fail_closed_fraction=fail_closed_fraction,
        seed=seed,
    )
    naive = await _run_arm(config=NAIVE, arrivals=arrivals, column=column)
    full = await _run_arm(config=FULL, arrivals=arrivals, column=column)
    if full.harmed:
        raise RuntimeError(
            f"full arm harmed {full.harmed} mixed-load events; refuse to freeze"
        )
    return {
        "events": events,
        "fail_closed_fraction": fail_closed_fraction,
        "arrival_seed": seed,
        "column": column.value,
        "poisson_lambda": DEFAULT_POISSON_LAMBDA,
        "naive": naive.as_json(),
        "full": full.as_json(),
    }


def render_backlog_markdown(report: dict[str, Any]) -> str:
    naive = report["naive"]
    full = report["full"]
    lines = [
        "# Mixed-load backlog (fail-closed cost)",
        "",
        (
            f"events={report['events']} fail_closed_fraction="
            f"{report['fail_closed_fraction']:.2f} column=`{report['column']}` "
            f"seed={report['arrival_seed']}"
        ),
        "",
        "| arm | closed_ok | harmed | stuck | human | ready mean | ready p95 | stuck age p50 | stuck age p95 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for arm in (naive, full):
        lines.append(
            f"| {arm['config']} | {arm['closed_ok']}/{arm['events']} "
            f"| {arm['harmed']} | {arm['stuck']} | {arm['human']} "
            f"| {arm['ready_mean']:.2f} | {arm['ready_p95']:.2f} "
            f"| {arm['stuck_age_p50']:.2f} | {arm['stuck_age_p95']:.2f} |"
        )
    lines.append("")
    lines.append(
        "Gold-path scale (120/120 closed, READY mean 0) remains in "
        "`eval/results/scale`. This table is the mixed arrival process."
    )
    return "\n".join(lines)


__all__ = [
    "DEFAULT_EVENTS",
    "FAIL_CLOSED_IDS",
    "build_arrivals",
    "render_backlog_markdown",
    "run_backlog_probe",
]
