#!/usr/bin/env python3
"""Exhaustive interleaving check of the terminal-head activation protocol.

The substrate ablation in the evaluation runs the real system and observes what
gets through. It answers "did this happen", and because the harness drives cases
sequentially it can only answer that for the interleavings the harness happens to
produce. The multi-process probe widens that, but four processes over five rounds
still sample rather than enumerate.

This module asks the other question: over *every* interleaving of K workers
executing the activation protocol, does the single-active-head invariant hold?
The protocol is small enough to enumerate, so the answer is a proof over the
model rather than a sample, and when the answer is no the checker prints the
shortest trace that gets there.

The model is deliberately close to the code it abstracts, because a model that
drops the awkward parts proves nothing about the system:

* Enqueue selects the prior active head ``FOR UPDATE`` before inserting, so two
  enqueues that both see a prior head are serialized by the row lock. Two that
  both see *no* prior head are not, and that gap is what the partial unique
  index exists to close.
* A worker that waits on that lock does not rescan when the lock is released.
  PostgreSQL rechecks the locked row against the predicate and filters it out if
  it no longer matches; it does not re-execute the query to find the row that
  replaced it. So a waiter can wake up and conclude there is no active head at
  the exact moment one exists.
* The supersede of the prior head and the insert of the new one are one
  transaction, so a unique violation rolls the supersede back with it.
* A prior head that has already been delivered keeps its delivery status when it
  is superseded; only an undelivered one is pulled out of the queue.
* Delivery re-reads the active head and refuses to send if it is no longer the
  newest one.

Two scenarios, because the two races have different shapes and the sequential
suite conflates them:

``shared_action``
    K workers race to execute one approved action. This is the duplicate-effect
    race, and the compare-and-set on action status is the mechanism that decides
    it.
``distinct_actions``
    K workers each hold their own approved action for the same
    (event, cycle, intent, slot) — an amended plan revision, or a second closure
    attempt. Every claim legitimately succeeds, so the claim CAS decides nothing
    and the three head mechanisms are the only thing standing between this and
    two live terminal writebacks.

Four mechanisms can be switched off, matching :mod:`app.eval_suite.substrate`:
the compare-and-set on action claiming, the partial unique index, the
in-transaction supersede, and the delivery-time assertion. Production has no
switch for any of them; this is a model, so it does.

Run with no arguments: ``python3 eval/model/head_invariants.py``. Nothing outside
the standard library, so a reviewer can check it in one command.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

APPROVED = "approved"
EXECUTING = "executing"

READY = "ready"
DEAD_LETTER = "dead_letter"
DELIVERED = "delivered"

CLAIM_READ = "claim_read"
CLAIM_WRITE = "claim_write"
SCAN = "scan"
WAIT = "wait"
RECHECK = "recheck"
INSERT = "insert"
LEASE = "lease"
LEASE_WAIT = "lease_wait"
CHECK_LINEAGE = "check_lineage"
ASSERT_HEAD = "assert_head"
SUBMIT = "submit"

DONE_LOST_CLAIM = "done:lost_claim"
DONE_UNIQUE_VIOLATION = "done:unique_violation"
DONE_LINEAGE_BLOCKED = "done:lineage_blocked"
DONE_ASSERTION_BLOCKED = "done:assertion_blocked"
DONE_DELIVERED = "done:delivered"

SHARED_ACTION = "shared_action"
DISTINCT_ACTIONS = "distinct_actions"


class Head(NamedTuple):
    """One row of ``disposition_outbox``, reduced to what the invariants need."""

    owner: int
    action: int
    superseded: bool
    delivery: str


class Local(NamedTuple):
    """A worker's transaction-local variables."""

    seen: str | None = None
    candidate: int | None = None
    prior: int | None = None


class State(NamedTuple):
    actions: tuple[str, ...]
    claim_writers: tuple[int, ...]
    heads: tuple[Head, ...]
    locks: frozenset[int]
    pcs: tuple[str, ...]
    locals: tuple[Local, ...]
    submits_by_action: tuple[int, ...]
    stale_delivered: int


@dataclass(frozen=True)
class Mechanisms:
    """Which of the four substrate mechanisms are loaded."""

    name: str
    claim_cas: bool = True
    head_index: bool = True
    head_supersede: bool = True
    head_assertion: bool = True


@dataclass(frozen=True)
class Scenario:
    """Which action each worker is executing."""

    name: str
    owner_action: tuple[int, ...]

    @property
    def workers(self) -> int:
        return len(self.owner_action)

    @property
    def action_count(self) -> int:
        return max(self.owner_action) + 1


def scenario(name: str, workers: int) -> Scenario:
    if name == SHARED_ACTION:
        return Scenario(name, (0,) * workers)
    if name == DISTINCT_ACTIONS:
        return Scenario(name, tuple(range(workers)))
    raise ValueError(f"unknown scenario {name!r}")


# The ladder from the substrate ablation, plus the two arms the sequential suite
# cannot reach: index-only and supersede-only. Those two are the reason for
# building this at all.
LADDER: tuple[Mechanisms, ...] = (
    Mechanisms("full"),
    Mechanisms("minus_claim_cas", claim_cas=False),
    Mechanisms("minus_head_index", head_index=False),
    Mechanisms("minus_head_supersede", head_supersede=False),
    Mechanisms("minus_head_uniqueness", head_index=False, head_supersede=False),
    Mechanisms(
        "minus_head_uniqueness_and_assertion",
        head_index=False,
        head_supersede=False,
        head_assertion=False,
    ),
    Mechanisms(
        "naive",
        claim_cas=False,
        head_index=False,
        head_supersede=False,
        head_assertion=False,
    ),
)


def initial_state(scn: Scenario) -> State:
    return State(
        actions=(APPROVED,) * scn.action_count,
        claim_writers=(0,) * scn.action_count,
        heads=(),
        locks=frozenset(),
        pcs=(CLAIM_READ,) * scn.workers,
        locals=(Local(),) * scn.workers,
        submits_by_action=(0,) * scn.action_count,
        stale_delivered=0,
    )


def _set(items: tuple[Any, ...], index: int, value: Any) -> tuple[Any, ...]:
    return items[:index] + (value,) + items[index + 1 :]


def _bump(items: tuple[int, ...], index: int) -> tuple[int, ...]:
    return _set(items, index, items[index] + 1)


def _active(heads: tuple[Head, ...]) -> list[int]:
    return [i for i, head in enumerate(heads) if not head.superseded]


def _own_head(heads: tuple[Head, ...], worker: int) -> int | None:
    for index in range(len(heads) - 1, -1, -1):
        if heads[index].owner == worker:
            return index
    return None


def successors(state: State, mech: Mechanisms, scn: Scenario) -> Iterator[tuple[str, State]]:
    """Every single-worker step enabled in this state."""
    for w in range(scn.workers):
        pc = state.pcs[w]
        if pc.startswith("done:"):
            continue
        yield from _worker_steps(state, mech, scn, w, pc)


def _claim_steps(
    state: State,
    mech: Mechanisms,
    w: int,
    pc: str,
    action: int,
    local: Local,
) -> Iterator[tuple[str, State]]:
    if pc == CLAIM_READ and mech.claim_cas:
        # One conditional UPDATE under a row lock: the test and the set are the
        # same step, so no window exists between them.
        if state.actions[action] == APPROVED:
            yield (
                f"w{w}: claim action {action} by compare-and-set, succeeds",
                state._replace(
                    actions=_set(state.actions, action, EXECUTING),
                    claim_writers=_bump(state.claim_writers, action),
                    pcs=_set(state.pcs, w, SCAN),
                ),
            )
        else:
            yield (
                f"w{w}: claim action {action} refused, row is no longer APPROVED",
                state._replace(pcs=_set(state.pcs, w, DONE_LOST_CLAIM)),
            )
        return

    if pc == CLAIM_READ:
        yield (
            f"w{w}: read action {action} status ({state.actions[action]})",
            state._replace(
                pcs=_set(state.pcs, w, CLAIM_WRITE),
                locals=_set(state.locals, w, local._replace(seen=state.actions[action])),
            ),
        )
        return

    if local.seen == APPROVED:
        yield (
            f"w{w}: write action {action} EXECUTING on the strength of an earlier read",
            state._replace(
                actions=_set(state.actions, action, EXECUTING),
                claim_writers=_bump(state.claim_writers, action),
                pcs=_set(state.pcs, w, SCAN),
            ),
        )
    else:
        yield (
            f"w{w}: give up, the earlier read of action {action} was not APPROVED",
            state._replace(pcs=_set(state.pcs, w, DONE_LOST_CLAIM)),
        )


def _enqueue_steps(
    state: State,
    mech: Mechanisms,
    w: int,
    pc: str,
    action: int,
    local: Local,
) -> Iterator[tuple[str, State]]:
    if pc == SCAN:
        active = _active(state.heads)
        if not active:
            yield (
                f"w{w}: SELECT prior head FOR UPDATE returns nothing",
                state._replace(
                    pcs=_set(state.pcs, w, INSERT),
                    locals=_set(state.locals, w, local._replace(candidate=None, prior=None)),
                ),
            )
            return
        # The query has no ORDER BY and a LIMIT 1, so any matching row is a legal
        # result. Branching over all of them keeps the check conservative.
        for candidate in active:
            chosen = local._replace(candidate=candidate)
            if candidate in state.locks:
                yield (
                    f"w{w}: SELECT prior head {candidate} FOR UPDATE blocks on the row lock",
                    state._replace(
                        pcs=_set(state.pcs, w, WAIT),
                        locals=_set(state.locals, w, chosen),
                    ),
                )
            else:
                yield (
                    f"w{w}: lock prior head {candidate}",
                    state._replace(
                        locks=state.locks | {candidate},
                        pcs=_set(state.pcs, w, RECHECK),
                        locals=_set(state.locals, w, chosen),
                    ),
                )
        return

    if pc == WAIT:
        candidate = local.candidate
        assert candidate is not None
        if candidate not in state.locks:
            yield (
                f"w{w}: lock on head {candidate} granted",
                state._replace(
                    locks=state.locks | {candidate},
                    pcs=_set(state.pcs, w, RECHECK),
                ),
            )
        return

    if pc == RECHECK:
        candidate = local.candidate
        assert candidate is not None
        if state.heads[candidate].superseded:
            # EvalPlanQual: the locked row no longer matches the predicate, so it
            # is dropped from the result. The query is not re-run, so the head
            # that replaced it stays invisible and this worker proceeds believing
            # there is no active head.
            yield (
                f"w{w}: head {candidate} was superseded while waiting; the predicate "
                f"recheck drops it and the query is not rescanned",
                state._replace(
                    locks=state.locks - {candidate},
                    pcs=_set(state.pcs, w, INSERT),
                    locals=_set(state.locals, w, local._replace(prior=None)),
                ),
            )
        else:
            yield (
                f"w{w}: head {candidate} is still active, adopt it as prior",
                state._replace(
                    pcs=_set(state.pcs, w, INSERT),
                    locals=_set(state.locals, w, local._replace(prior=candidate)),
                ),
            )
        return

    yield _insert_step(state, mech, w, action, local)


def _worker_steps(
    state: State,
    mech: Mechanisms,
    scn: Scenario,
    w: int,
    pc: str,
) -> Iterator[tuple[str, State]]:
    local = state.locals[w]
    action = scn.owner_action[w]

    if pc in {CLAIM_READ, CLAIM_WRITE}:
        yield from _claim_steps(state, mech, w, pc, action, local)
        return

    if pc in {SCAN, WAIT, RECHECK, INSERT}:
        yield from _enqueue_steps(state, mech, w, pc, action, local)
        return

    yield from _delivery_steps(state, mech, w, pc, action)


def _delivery_steps(
    state: State,
    mech: Mechanisms,
    w: int,
    pc: str,
    action: int,
) -> Iterator[tuple[str, State]]:
    """Lease the row, check lineage, re-read the active head, then submit.

    The lock taken here is the one the production worker holds ``FOR UPDATE`` on
    its own outbox row for the whole delivery transaction, adapter call included.
    Modelling it matters: without it the model reports a window between the
    active-head assertion and the vendor call, and that window is closed in the
    real system precisely because a concurrent enqueue has to lock this same row
    to supersede it.
    """
    mine = _own_head(state.heads, w)
    assert mine is not None

    if pc in {LEASE, LEASE_WAIT}:
        if mine in state.locks:
            if pc == LEASE:
                yield (
                    f"w{w}: SELECT head {mine} FOR UPDATE blocks on the row lock",
                    state._replace(pcs=_set(state.pcs, w, LEASE_WAIT)),
                )
            return
        yield (
            f"w{w}: lease head {mine} for delivery",
            state._replace(
                locks=state.locks | {mine},
                pcs=_set(state.pcs, w, CHECK_LINEAGE),
            ),
        )
        return

    if pc == CHECK_LINEAGE:
        # Not one of the four switchable mechanisms: a head carrying a lineage
        # pointer is non-deliverable from commit time, unconditionally.
        if state.heads[mine].superseded:
            yield (
                f"w{w}: head {mine} carries a supersede pointer, refuse to deliver",
                _finish(state, w, mine, DONE_LINEAGE_BLOCKED),
            )
        else:
            yield (
                f"w{w}: head {mine} carries no supersede pointer",
                state._replace(pcs=_set(state.pcs, w, ASSERT_HEAD)),
            )
        return

    if pc == ASSERT_HEAD:
        if not mech.head_assertion:
            yield (
                f"w{w}: deliver head {mine} without re-reading the active head",
                state._replace(pcs=_set(state.pcs, w, SUBMIT)),
            )
            return
        if _newest_active(state.heads) == mine:
            yield (
                f"w{w}: head {mine} is still the active head, proceed to deliver",
                state._replace(pcs=_set(state.pcs, w, SUBMIT)),
            )
        else:
            yield (
                f"w{w}: head {mine} is no longer the active head, refuse to deliver",
                _finish(state, w, mine, DONE_ASSERTION_BLOCKED),
            )
        return

    if pc == SUBMIT:
        stale = _newest_active(state.heads) != mine
        head = state.heads[mine]
        nxt = state._replace(
            heads=_set(state.heads, mine, head._replace(delivery=DELIVERED)),
            submits_by_action=_bump(state.submits_by_action, action),
            stale_delivered=state.stale_delivered + (1 if stale else 0),
            locks=state.locks - {mine},
            pcs=_set(state.pcs, w, DONE_DELIVERED),
        )
        yield (f"w{w}: submit head {mine} to the vendor", nxt)
        return

    raise AssertionError(f"unhandled pc {pc!r}")


def _newest_active(heads: tuple[Head, ...]) -> int | None:
    active = _active(heads)
    return max(active) if active else None


def _finish(state: State, w: int, mine: int, reason: str) -> State:
    return state._replace(
        heads=_set(state.heads, mine, state.heads[mine]._replace(delivery=DEAD_LETTER)),
        locks=state.locks - {mine},
        pcs=_set(state.pcs, w, reason),
    )


def _insert_step(
    state: State,
    mech: Mechanisms,
    w: int,
    action: int,
    local: Local,
) -> tuple[str, State]:
    """Supersede the prior head and insert the new one, in one transaction."""
    heads = state.heads
    prior = local.prior
    if mech.head_supersede and prior is not None:
        retired = heads[prior]._replace(superseded=True)
        if retired.delivery == READY:
            # An undelivered head is pulled out of the queue as it is retired; a
            # delivered one keeps its status, because it already happened.
            retired = retired._replace(delivery=DEAD_LETTER)
        heads = _set(heads, prior, retired)

    release = state.locks - ({prior} if prior is not None else set())

    if mech.head_index and _active(heads):
        # The partial unique index rejects the insert. The transaction aborts, so
        # the supersede above is rolled back with it.
        return (
            f"w{w}: insert refused by the active-head unique index",
            state._replace(locks=release, pcs=_set(state.pcs, w, DONE_UNIQUE_VIOLATION)),
        )

    heads = heads + (Head(owner=w, action=action, superseded=False, delivery=READY),)
    superseding = f", superseding {prior}" if mech.head_supersede and prior is not None else ""
    return (
        f"w{w}: insert head {len(heads) - 1}{superseding}",
        state._replace(heads=heads, locks=release, pcs=_set(state.pcs, w, LEASE)),
    )


@dataclass(frozen=True)
class Invariant:
    key: str
    label: str
    statement: str
    bound: int
    measure: Callable[[State], int]

    def holds(self, state: State) -> bool:
        return self.measure(state) <= self.bound


INVARIANTS: tuple[Invariant, ...] = (
    Invariant(
        key="single_active_head",
        label="I3",
        statement=("at most one active terminal head per (event, closure cycle, intent, slot)"),
        bound=1,
        measure=lambda s: len(_active(s.heads)),
    ),
    Invariant(
        key="single_effect_per_action",
        label="I5",
        statement="one approved action produces at most one external effect",
        bound=1,
        measure=lambda s: max(s.submits_by_action),
    ),
    Invariant(
        key="no_stale_delivery",
        label="I6",
        statement="no superseded head is ever delivered",
        bound=0,
        measure=lambda s: s.stale_delivered,
    ),
    Invariant(
        key="single_claim",
        label="I2a",
        statement="at most one worker writes an action's execution status",
        bound=1,
        measure=lambda s: max(s.claim_writers),
    ),
)


@dataclass
class CheckResult:
    mechanisms: str
    scenario: str
    workers: int
    states: int
    transitions: int
    violations: dict[str, list[str]]

    def to_json(self) -> dict[str, Any]:
        return {
            "mechanisms": self.mechanisms,
            "scenario": self.scenario,
            "workers": self.workers,
            "states": self.states,
            "transitions": self.transitions,
            "violations": self.violations,
        }


def check(mech: Mechanisms, scn: Scenario) -> CheckResult:
    """Breadth-first over the whole reachable state space.

    Breadth-first rather than depth-first so the first violation found for each
    invariant is a shortest one; a nine-step counterexample is something a
    reviewer can read, a ninety-step one is not.
    """
    start = initial_state(scn)
    seen: dict[State, tuple[State, str] | None] = {start: None}
    queue: deque[State] = deque([start])
    transitions = 0
    violations: dict[str, list[str]] = {}

    while queue:
        state = queue.popleft()
        for label, nxt in successors(state, mech, scn):
            transitions += 1
            if nxt in seen:
                continue
            seen[nxt] = (state, label)
            for inv in INVARIANTS:
                if inv.key not in violations and not inv.holds(nxt):
                    violations[inv.key] = _trace(seen, nxt)
            queue.append(nxt)

    return CheckResult(
        mechanisms=mech.name,
        scenario=scn.name,
        workers=scn.workers,
        states=len(seen),
        transitions=transitions,
        violations=violations,
    )


def _trace(seen: dict[State, tuple[State, str] | None], state: State) -> list[str]:
    steps: list[str] = []
    cursor: State | None = state
    while cursor is not None:
        edge = seen[cursor]
        if edge is None:
            break
        parent, label = edge
        steps.append(label)
        cursor = parent
    return list(reversed(steps))


def render_markdown(results: list[CheckResult]) -> str:
    lines = ["## Model check: terminal-head activation", ""]
    groups: dict[tuple[str, int], list[CheckResult]] = {}
    for result in results:
        groups.setdefault((result.scenario, result.workers), []).append(result)

    for (scenario_name, workers), group in groups.items():
        lines.append(f"### `{scenario_name}`, K = {workers}")
        lines.append("")
        header = "| mechanisms | states | " + " | ".join(f"{inv.label}" for inv in INVARIANTS)
        lines.append(header + " |")
        lines.append("|---" * (2 + len(INVARIANTS)) + "|")
        for result in group:
            cells = []
            for inv in INVARIANTS:
                trace = result.violations.get(inv.key)
                cells.append("holds" if trace is None else f"violated ({len(trace)})")
            lines.append(f"| `{result.mechanisms}` | {result.states} | " + " | ".join(cells) + " |")
        lines.append("")

    lines.append("Cells give the length of the shortest counterexample in steps.")
    lines.append("")
    for inv in INVARIANTS:
        lines.append(f"- **{inv.label}**: {inv.statement}")
    lines.append("")

    lines.append("### Shortest counterexamples")
    lines.append("")
    printed: set[tuple[str, str, str]] = set()
    for result in results:
        for inv in INVARIANTS:
            trace = result.violations.get(inv.key)
            if trace is None:
                continue
            key = (result.scenario, result.mechanisms, inv.key)
            if key in printed:
                continue
            printed.add(key)
            lines.append(
                f"**{inv.label} under `{result.mechanisms}`, "
                f"`{result.scenario}`, K={result.workers}** — {inv.statement}"
            )
            lines.append("")
            for index, step in enumerate(trace, start=1):
                lines.append(f"{index}. {step}")
            lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Model-check the head invariants.")
    parser.add_argument(
        "--workers",
        type=int,
        nargs="+",
        default=[2, 3, 4],
        help="numbers of concurrent workers to enumerate (default: 2 3 4)",
    )
    parser.add_argument(
        "--scenarios",
        nargs="+",
        default=[SHARED_ACTION, DISTINCT_ACTIONS],
        choices=[SHARED_ACTION, DISTINCT_ACTIONS],
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="directory to write model-check.json and model-check.md into",
    )
    args = parser.parse_args(argv)

    results = [
        check(mech, scenario(name, workers))
        for name in args.scenarios
        for workers in args.workers
        for mech in LADDER
    ]

    markdown = render_markdown(results)
    print(markdown)

    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "model-check.json").write_text(
            json.dumps([r.to_json() for r in results], indent=2) + "\n",
            encoding="utf-8",
        )
        (args.out / "model-check.md").write_text(markdown + "\n", encoding="utf-8")

    # The full configuration is the claim the paper makes. If it ever fails, say
    # so in the exit code rather than leaving it in a table nobody reads.
    failed = [r for r in results if r.mechanisms == "full" and r.violations]
    if failed:
        print("FAIL: the full configuration violates an invariant", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
