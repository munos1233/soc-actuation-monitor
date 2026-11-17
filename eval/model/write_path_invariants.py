#!/usr/bin/env python3
"""BFS model of the four write-path invariants beyond the head protocol.

Each invariant has a mechanism, an ablation that should fail it, and a
shortest counterexample. Production has no switch for these; this is a
model, so it does.

Invariants
----------
close
    Closure uses the rebuilt outbox cycle, not a caller-supplied context.
bind
    Dispatch re-computes the 11-segment fingerprint; a planner-written
    fingerprint column is not a witness.
egress
    The outbound locator is compared to the event's ingest-owned source,
    not to the command's own locator.
role
    The planner transaction's writable set excludes status, approval,
    outbox, disposition source, and DELETE.
"""

from __future__ import annotations

import argparse
import json
from collections import deque
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class State:
    caller_cycle: int
    rebuilt_cycle: int | None
    planner_fingerprint: str
    recomputed_fingerprint: str
    command_locator: str
    event_source: str
    planner_wrote_status: bool
    closed: bool
    dispatched: bool
    submitted: bool
    closed_on_stale_cycle: bool
    dispatched_on_forged_fingerprint: bool
    submitted_on_self_locator: bool

    def key(self) -> tuple[object, ...]:
        return (
            self.caller_cycle,
            self.rebuilt_cycle,
            self.planner_fingerprint,
            self.recomputed_fingerprint,
            self.command_locator,
            self.event_source,
            self.planner_wrote_status,
            self.closed,
            self.dispatched,
            self.submitted,
            self.closed_on_stale_cycle,
            self.dispatched_on_forged_fingerprint,
            self.submitted_on_self_locator,
        )


@dataclass(frozen=True)
class Mechanisms:
    close_rebuild: bool = True
    bind_recompute: bool = True
    egress_event_source: bool = True
    role_revoke: bool = True

    @property
    def name(self) -> str:
        missing = [
            label
            for flag, label in (
                (self.close_rebuild, "close"),
                (self.bind_recompute, "bind"),
                (self.egress_event_source, "egress"),
                (self.role_revoke, "role"),
            )
            if not flag
        ]
        return "full" if not missing else "minus_" + "+".join(missing)


START = State(
    caller_cycle=1,
    rebuilt_cycle=1,
    planner_fingerprint="fp-true",
    recomputed_fingerprint="fp-true",
    command_locator="ingest",
    event_source="ingest",
    planner_wrote_status=False,
    closed=False,
    dispatched=False,
    submitted=False,
    closed_on_stale_cycle=False,
    dispatched_on_forged_fingerprint=False,
    submitted_on_self_locator=False,
)


def successors(state: State, mech: Mechanisms) -> list[tuple[str, State]]:
    out: list[tuple[str, State]] = []
    out.append(("planner_forges_fingerprint", replace(state, planner_fingerprint="fp-forged")))
    out.append(("planner_repoints_locator", replace(state, command_locator="foreign")))
    out.append(
        (
            "planner_supplies_stale_cycle",
            replace(state, caller_cycle=2, rebuilt_cycle=1),
        )
    )
    if mech.role_revoke:
        out.append(("planner_status_update_refused", state))
    else:
        out.append(
            (
                "planner_writes_closed",
                replace(state, planner_wrote_status=True, closed=True),
            )
        )
    cycles_match = state.rebuilt_cycle == state.caller_cycle
    close_ok = cycles_match if mech.close_rebuild else True
    if close_ok and not state.closed:
        out.append(
            (
                "close_accepted",
                replace(
                    state,
                    closed=True,
                    closed_on_stale_cycle=not cycles_match,
                ),
            )
        )
    else:
        out.append(("close_refused", state))
    fingerprints_match = state.planner_fingerprint == state.recomputed_fingerprint
    bind_ok = fingerprints_match if mech.bind_recompute else True
    if bind_ok and not state.dispatched:
        out.append(
            (
                "dispatch_accepted",
                replace(
                    state,
                    dispatched=True,
                    dispatched_on_forged_fingerprint=not fingerprints_match,
                ),
            )
        )
    else:
        out.append(("dispatch_refused", state))
    locators_match = state.command_locator == state.event_source
    egress_ok = locators_match if mech.egress_event_source else True
    if state.dispatched and egress_ok and not state.submitted:
        out.append(
            (
                "vendor_submit",
                replace(
                    state,
                    submitted=True,
                    submitted_on_self_locator=not locators_match,
                ),
            )
        )
    elif state.dispatched:
        out.append(("vendor_blocked", state))
    return out


def close_holds(state: State) -> bool:
    return not state.closed_on_stale_cycle


def bind_holds(state: State) -> bool:
    return not state.dispatched_on_forged_fingerprint


def egress_holds(state: State) -> bool:
    return not state.submitted_on_self_locator


def role_holds(state: State) -> bool:
    return not state.planner_wrote_status


INVARIANTS = (
    ("close", "closure uses rebuilt cycle", close_holds),
    ("bind", "dispatch re-computes fingerprint", bind_holds),
    ("egress", "egress witnesses event source", egress_holds),
    ("role", "planner cannot write CLOSED", role_holds),
)


def check(mech: Mechanisms) -> dict[str, Any]:
    seen: dict[tuple[object, ...], tuple[tuple[object, ...] | None, str]] = {
        START.key(): (None, "start")
    }
    queue: deque[State] = deque([START])
    violations: dict[str, list[str]] = {}
    states = 0
    while queue:
        state = queue.popleft()
        states += 1
        for inv_key, _label, holds in INVARIANTS:
            if inv_key not in violations and not holds(state):
                violations[inv_key] = _trace(seen, state.key())
        for label, nxt in successors(state, mech):
            key = nxt.key()
            if key in seen:
                continue
            seen[key] = (state.key(), label)
            queue.append(nxt)
    return {
        "mechanisms": mech.name,
        "states": states,
        "violations": {key: trace for key, trace in violations.items()},
    }


def _trace(
    seen: dict[tuple[object, ...], tuple[tuple[object, ...] | None, str]],
    key: tuple[object, ...],
) -> list[str]:
    steps: list[str] = []
    cursor: tuple[object, ...] | None = key
    while cursor is not None:
        parent, label = seen[cursor]
        if parent is None:
            break
        steps.append(label)
        cursor = parent
    return list(reversed(steps))


LADDER = (
    Mechanisms(),
    Mechanisms(close_rebuild=False),
    Mechanisms(bind_recompute=False),
    Mechanisms(egress_event_source=False),
    Mechanisms(role_revoke=False),
)


# Abstract steps → Injection knobs the production chain already implements.
# sql_bypass is emitted for the role CE but is outside the coverage-search
# cartesian (A0 is a login test, not a proposal mutation).
STEP_INJECTION: dict[str, dict[str, Any]] = {
    "planner_forges_fingerprint": {"mutate_after_approval": "target_forged_fingerprint"},
    "planner_repoints_locator": {"locator_swap": True},
    "planner_supplies_stale_cycle": {"bump_revision_after_activation": True},
    "planner_writes_closed": {"sql_bypass": "close"},
}


def emit_seeds() -> list[dict[str, Any]]:
    """TLC-trace seeds. The BFS below is a regression slice, not the source."""
    from tei_engine import emit_tlc_seeds

    wanted = ("close", "bind", "egress", "role")
    seeds: list[dict[str, Any]] = []
    seen: set[str] = set()
    for seed in emit_tlc_seeds():
        inv = seed["invariant"]
        if inv not in wanted or inv in seen:
            continue
        seen.add(inv)
        seeds.append(seed)
    return seeds


def render_markdown(results: list[dict[str, Any]]) -> str:
    lines = [
        "## Model check: write-path invariants",
        "",
        "| mechanisms | states | close | bind | egress | role |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        cells = []
        for key, _label, _holds in INVARIANTS:
            trace = result["violations"].get(key)
            cells.append("holds" if trace is None else f"violated ({len(trace)})")
        lines.append(
            f"| `{result['mechanisms']}` | {result['states']} | " + " | ".join(cells) + " |"
        )
    lines.append("")
    lines.append("### Shortest counterexamples")
    lines.append("")
    for result in results:
        for key, label, _holds in INVARIANTS:
            trace = result["violations"].get(key)
            if not trace:
                continue
            lines.append(f"**{label} under `{result['mechanisms']}`**")
            lines.append("")
            for index, step in enumerate(trace, start=1):
                lines.append(f"{index}. {step}")
            lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    results = [check(mech) for mech in LADDER]
    markdown = render_markdown(results)
    print(markdown)
    if args.out is not None:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "write-path.json").write_text(
            json.dumps(results, indent=2) + "\n", encoding="utf-8"
        )
        (args.out / "write-path.md").write_text(markdown + "\n", encoding="utf-8")
    failed = [r for r in results if r["mechanisms"] == "full" and r["violations"]]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
