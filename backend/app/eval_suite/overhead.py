"""What the four mediators cost, measured rather than asserted.

The paper claims the mediators are affordable, and until now the only number
behind that claim was the extra worker passes the golden path needs. This module
supplies the rest: per-mediator decision latency, the number of SQL statements a
case issues, and the number of worker passes it takes to converge, all for the
same cases under ``naive`` and under ``full``.

Two measurement choices are worth stating because they bound what the numbers
mean.

Latency comes from :func:`app.core.metrics.time_mediator`, which wraps each
mediator including the path where the switch is off. So the ``naive`` row is not
zero: it is the cost of asking whether the mediator is loaded. The difference
between the arms is therefore the mediator's own work and not an artefact of two
differently-scoped timers.

Round trips are counted with a SQLAlchemy cursor hook on the evaluation engine,
so the figure is statements actually issued, including the ones the ORM issues on
its own behalf. It is not a count of round trips the mediators are responsible
for; it is the whole case. The delta between arms is the part that is theirs.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import event

from app.core.metrics import MEDIATORS, mediator_latency_snapshot, reset_mediator_latency
from app.eval_suite.chain import Injection, run_case
from app.eval_suite.configs import FULL, NAIVE, MonitorConfig, VendorColumn, harness_context
from app.eval_suite.gold import GOLDEN_CASES
from app.eval_suite.world import EvalWorld, eval_world

DEFAULT_REPEATS = 3


@dataclass
class StatementCounter:
    """Counts SQL statements issued through one engine."""

    statements: int = 0
    by_verb: dict[str, int] = field(default_factory=dict)

    def record(self, sql: str) -> None:
        self.statements += 1
        verb = sql.strip().split(None, 1)[0].upper() if sql.strip() else "?"
        self.by_verb[verb] = self.by_verb.get(verb, 0) + 1

    def reset(self) -> None:
        self.statements = 0
        self.by_verb.clear()


@contextmanager
def count_statements(world: EvalWorld) -> Iterator[StatementCounter]:
    """Attach a cursor hook to the world's engine for the duration."""
    counter = StatementCounter()
    engine = world.session_factory.kw["bind"]
    sync_engine = getattr(engine, "sync_engine", engine)

    def before_cursor_execute(
        _conn: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        counter.record(statement)

    event.listen(sync_engine, "before_cursor_execute", before_cursor_execute)
    try:
        yield counter
    finally:
        event.remove(sync_engine, "before_cursor_execute", before_cursor_execute)


async def _measure_arm(
    *,
    config: MonitorConfig,
    column: VendorColumn,
    cases: Sequence[Injection],
    repeats: int,
) -> dict[str, Any]:
    wall: list[float] = []
    statements: list[int] = []
    worker_passes: list[int] = []
    reset_mediator_latency()
    with harness_context(config, column):
        async with eval_world(column) as world:
            with count_statements(world) as counter:
                for _ in range(max(1, repeats)):
                    for case in cases:
                        if not case.runs_in(column.value):
                            continue
                        counter.reset()
                        started = time.perf_counter()
                        outcome = await run_case(world, case, config_name=config.name)
                        wall.append(time.perf_counter() - started)
                        statements.append(counter.statements)
                        worker_passes.append(int(outcome.notes.get("worker_ticks", 1)))
    return {
        "config": config.name,
        "column": column.value,
        "cases": len(wall),
        "wall_p50": _p(wall, 0.50),
        "wall_p95": _p(wall, 0.95),
        "statements_mean": statistics.fmean(statements) if statements else 0.0,
        "statements_p95": float(_p([float(item) for item in statements], 0.95)),
        "worker_passes_mean": statistics.fmean(worker_passes) if worker_passes else 0.0,
        "mediators": mediator_latency_snapshot(),
    }


def _p(values: Sequence[float], fraction: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(fraction * len(ordered)) - 1 if fraction < 1 else -1))
    return ordered[index]


async def run_overhead_probe(
    *,
    column: VendorColumn = VendorColumn.MOCK,
    cases: Sequence[Injection] = GOLDEN_CASES,
    repeats: int = DEFAULT_REPEATS,
) -> dict[str, Any]:
    """Measure the same cases under naive and full, in that order.

    Suite A, not Suite B, and the reason matters. On adversarial cases the two arms
    do different amounts of work -- the mediated arm refuses early and therefore
    issues *fewer* statements than the unmediated one -- so comparing them would
    report the mediators as a speedup, which is true and meaningless. On the golden
    path both arms run the same case to the same close, so the difference is the
    cost of the mediation and nothing else.

    Naive first, so that any systematic drift in the machine's state over the run
    works against the conclusion rather than for it: if anything, the full arm is
    measured on the larger database.
    """
    naive = await _measure_arm(config=NAIVE, column=column, cases=cases, repeats=repeats)
    full = await _measure_arm(config=FULL, column=column, cases=cases, repeats=repeats)
    return {
        "arms": [naive, full],
        "delta": {
            "wall_p50": full["wall_p50"] - naive["wall_p50"],
            "statements_mean": full["statements_mean"] - naive["statements_mean"],
            "worker_passes_mean": full["worker_passes_mean"] - naive["worker_passes_mean"],
        },
    }


def render_overhead_markdown(report: dict[str, Any]) -> str:
    arms = report["arms"]
    lines = [
        "| arm | cases | wall p50 (ms) | wall p95 (ms) | SQL statements/case | worker passes |",
        "|---|---|---|---|---|---|",
    ]
    for arm in arms:
        lines.append(
            f"| {arm['config']} | {arm['cases']} "
            f"| {arm['wall_p50'] * 1000:.0f} | {arm['wall_p95'] * 1000:.0f} "
            f"| {arm['statements_mean']:.1f} | {arm['worker_passes_mean']:.2f} |"
        )
    lines.append("")
    lines.append("| mediator | arm | p50 (ms) | p95 (ms) | decisions |")
    lines.append("|---|---|---|---|---|")
    for mediator in MEDIATORS:
        for arm in arms:
            entry = arm["mediators"].get(mediator)
            if entry is None:
                continue
            lines.append(
                f"| {mediator} | {arm['config']} "
                f"| {entry['p50'] * 1000:.2f} | {entry['p95'] * 1000:.2f} "
                f"| {int(entry['count'])} |"
            )
    return "\n".join(lines)


__all__ = [
    "DEFAULT_REPEATS",
    "StatementCounter",
    "count_statements",
    "render_overhead_markdown",
    "run_overhead_probe",
]
