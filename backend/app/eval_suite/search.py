"""Coverage-guided search over already-implemented Injection knobs.

The handwritten A0–A5 set can be accused of suite overfitting. This search
enumerates a cartesian subset of planner-writable and vendor-receipt knobs the
chain already implements, seeds it from the write-path BFS counterexamples, and
prefers unseen coverage tuples. It does not invent privileges or new mediators.

Bypass under full: harmed, or CLOSED on a skip_report case. Finding either
refuses the freeze.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from itertools import product
from pathlib import Path
from typing import Any

from app.eval_suite.chain import HARM_WRONG_ACT, Injection, run_case
from app.eval_suite.configs import FULL, MonitorConfig, VendorColumn, harness_context
from app.eval_suite.vendor import ReceiptProfile
from app.eval_suite.world import eval_world

DEFAULT_BUDGET = 512

MUTATE_VALUES: tuple[str | None, ...] = (
    None,
    "target",
    "target_forged_fingerprint",
    "tool",
    "plan_revision",
    "level_downgrade",
)

# SIMULATED_CONFIRM is a pseudo-live-only receipt; mock search omits it.
RECEIPT_PROFILES: tuple[ReceiptProfile, ...] = (
    ReceiptProfile.STRONG,
    ReceiptProfile.WEAK_ACK,
    ReceiptProfile.DROPPED_READBACK,
    ReceiptProfile.LYING_SUCCESS,
    ReceiptProfile.FLAKY_READBACK,
)

FLAG_NAMES: tuple[str, ...] = (
    "skip_report",
    "locator_swap",
    "rewrite_idempotency_key",
    "strip_outbox_revision",
    "bump_revision_after_activation",
)


def _model_dir() -> Path:
    return Path(__file__).resolve().parents[3] / "eval" / "model"


def load_model_seeds() -> list[dict[str, Any]]:
    model_dir = _model_dir()
    if str(model_dir) not in sys.path:
        sys.path.insert(0, str(model_dir))
    from write_path_invariants import emit_seeds

    return emit_seeds()


@dataclass(frozen=True)
class SearchSpec:
    mutate_after_approval: str | None
    receipt_profile: ReceiptProfile
    skip_report: bool
    locator_swap: bool
    rewrite_idempotency_key: bool
    strip_outbox_revision: bool
    bump_revision_after_activation: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "mutate_after_approval": self.mutate_after_approval,
            "receipt_profile": self.receipt_profile.value,
            "skip_report": self.skip_report,
            "locator_swap": self.locator_swap,
            "rewrite_idempotency_key": self.rewrite_idempotency_key,
            "strip_outbox_revision": self.strip_outbox_revision,
            "bump_revision_after_activation": self.bump_revision_after_activation,
        }

    def key(self) -> tuple[object, ...]:
        return (
            self.mutate_after_approval,
            self.receipt_profile.value,
            self.skip_report,
            self.locator_swap,
            self.rewrite_idempotency_key,
            self.strip_outbox_revision,
            self.bump_revision_after_activation,
        )


def enumerate_search_space() -> list[SearchSpec]:
    space: list[SearchSpec] = []
    for mutate, profile, flags in product(
        MUTATE_VALUES,
        RECEIPT_PROFILES,
        product((False, True), repeat=len(FLAG_NAMES)),
    ):
        knobs = dict(zip(FLAG_NAMES, flags, strict=True))
        space.append(
            SearchSpec(
                mutate_after_approval=mutate,
                receipt_profile=profile,
                **knobs,
            )
        )
    return space


def spec_from_injection_knobs(knobs: dict[str, Any]) -> SearchSpec | None:
    """Map a model seed onto the cartesian space; A0 sql_bypass is out of scope."""
    if knobs.get("sql_bypass"):
        return None
    return SearchSpec(
        mutate_after_approval=knobs.get("mutate_after_approval"),
        receipt_profile=ReceiptProfile(knobs.get("receipt_profile", ReceiptProfile.STRONG)),
        skip_report=bool(knobs.get("skip_report", False)),
        locator_swap=bool(knobs.get("locator_swap", False)),
        rewrite_idempotency_key=bool(knobs.get("rewrite_idempotency_key", False)),
        strip_outbox_revision=bool(knobs.get("strip_outbox_revision", False)),
        bump_revision_after_activation=bool(
            knobs.get("bump_revision_after_activation", False)
        ),
    )


def model_seed_specs() -> list[SearchSpec]:
    specs: list[SearchSpec] = []
    seen: set[tuple[object, ...]] = set()
    for seed in load_model_seeds():
        spec = spec_from_injection_knobs(seed.get("injection") or {})
        if spec is None or spec.key() in seen:
            continue
        seen.add(spec.key())
        specs.append(spec)
    return specs


def coverage_key(outcome: Any) -> tuple[object, ...]:
    return (
        bool(outcome.closed),
        bool(outcome.harmed),
        frozenset(outcome.blocked_errors),
        bool(outcome.entity_submits > 0),
    )


def is_bypass(spec: SearchSpec, outcome: Any) -> bool:
    if outcome.harmed:
        return True
    return bool(spec.skip_report and outcome.closed)


def _injection_for(spec: SearchSpec, index: int) -> Injection:
    return Injection(
        case_id=f"search_{index:04d}",
        adversary="S",
        harm=HARM_WRONG_ACT,
        expected_mediator=None,
        description="Coverage search over implemented Injection knobs.",
        mutate_after_approval=spec.mutate_after_approval,
        receipt_profile=spec.receipt_profile,
        skip_report=spec.skip_report,
        locator_swap=spec.locator_swap,
        rewrite_idempotency_key=spec.rewrite_idempotency_key,
        duplicate_entity_dispatch=spec.rewrite_idempotency_key,
        strip_outbox_revision=spec.strip_outbox_revision,
        bump_revision_after_activation=spec.bump_revision_after_activation,
        worker_ticks=2 if spec.receipt_profile is ReceiptProfile.FLAKY_READBACK else 1,
    )


def order_candidates(space: list[SearchSpec]) -> list[SearchSpec]:
    """Model CEs first, then the rest in a stable order."""
    seeds = model_seed_specs()
    seed_keys = {spec.key() for spec in seeds}
    rest = [spec for spec in space if spec.key() not in seed_keys]
    return [*seeds, *rest]


@dataclass
class SearchReport:
    budget: int
    space_size: int = 0
    attempted: int = 0
    new_coverage: int = 0
    bypass_found: bool = False
    winning_spec: dict[str, Any] | None = None
    traces: list[dict[str, Any]] = field(default_factory=list)
    coverage: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "budget": self.budget,
            "space_size": self.space_size,
            "attempted": self.attempted,
            "new_coverage": self.new_coverage,
            "bypass_found": self.bypass_found,
            "winning_spec": self.winning_spec,
            "new_harm_class": self.bypass_found,
            "traces": self.traces,
            "coverage": self.coverage,
        }


async def run_coverage_search(
    *,
    column: VendorColumn = VendorColumn.MOCK,
    config: MonitorConfig = FULL,
    budget: int = DEFAULT_BUDGET,
) -> SearchReport:
    space = enumerate_search_space()
    report = SearchReport(budget=max(1, budget), space_size=len(space))
    seen_coverage: set[tuple[object, ...]] = set()
    ordered = order_candidates(space)
    with harness_context(config, column):
        async with eval_world(column, role_separation=config.role_separation) as world:
            for spec in ordered:
                if report.attempted >= report.budget:
                    break
                case = _injection_for(spec, report.attempted)
                outcome = await run_case(world, case, config_name=config.name)
                report.attempted += 1
                key = coverage_key(outcome)
                novel = key not in seen_coverage
                if novel:
                    seen_coverage.add(key)
                    report.new_coverage += 1
                    report.coverage.append(
                        {
                            "closed": outcome.closed,
                            "harmed": outcome.harmed,
                            "blocked": list(outcome.blocked_errors),
                            "entity_submit": outcome.entity_submits > 0,
                        }
                    )
                trace = {
                    "spec": spec.as_json(),
                    "closed": outcome.closed,
                    "harmed": outcome.harmed,
                    "entity_submits": outcome.entity_submits,
                    "blocked": list(outcome.blocked_errors),
                    "novel_coverage": novel,
                }
                report.traces.append(trace)
                if is_bypass(spec, outcome):
                    report.bypass_found = True
                    report.winning_spec = spec.as_json()
                    break
    return report


def render_search_markdown(report: SearchReport) -> str:
    lines = [
        "# Coverage search over implemented Injection knobs",
        "",
        (
            f"Budget {report.budget}; space {report.space_size}; "
            f"attempted {report.attempted}; coverage cells {report.new_coverage}."
        ),
        "",
    ]
    if report.bypass_found:
        lines.append(f"Found a bypass: `{report.winning_spec}`.")
    else:
        lines.append(
            "No new harm class within the implemented-knob space under the full "
            "configuration. This is not a claim that the threat distribution is "
            "exhausted."
        )
    lines.append("")
    lines.append("| closed | harmed | entity_submit | blocked |")
    lines.append("|---|---|---|---|")
    for cell in report.coverage:
        blocked = ", ".join(cell.get("blocked") or []) or "—"
        lines.append(
            f"| {cell['closed']} | {cell['harmed']} | {cell['entity_submit']} | {blocked} |"
        )
    return "\n".join(lines)


__all__ = [
    "DEFAULT_BUDGET",
    "FLAG_NAMES",
    "MUTATE_VALUES",
    "RECEIPT_PROFILES",
    "SearchSpec",
    "coverage_key",
    "enumerate_search_space",
    "is_bypass",
    "load_model_seeds",
    "model_seed_specs",
    "order_candidates",
    "render_search_markdown",
    "run_coverage_search",
    "spec_from_injection_knobs",
]
