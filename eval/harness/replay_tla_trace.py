#!/usr/bin/env python3
"""Instantiate TEI.tla / TLC traces on both write-path instances.

    python eval/harness/replay_tla_trace.py --out eval/results/replay

SOC replay needs DATABASE_URL (production chain). Kubernetes replay uses
the lab control plane and always runs. A bypass under full refuses the freeze.
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
BACKEND = REPO_ROOT / "backend"
MODEL = REPO_ROOT / "eval" / "model"
for path in (BACKEND, MODEL):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tei_engine import STEP_INJECTION, emit_tlc_seeds  # noqa: E402


def _k8s_injection(knobs: dict[str, Any], invariant: str) -> Any:
    from app.eval_suite.k8s_cases import HARM_WRONG_ACT, K8sInjection

    return K8sInjection(
        case_id=f"tla_{invariant}",
        adversary="TLA",
        harm=HARM_WRONG_ACT,
        expected_mediator=invariant,
        description=f"TLC seed for {invariant}",
        planner_privilege=knobs.get("planner_privilege") or knobs.get("sql_bypass") and "create_networkpolicy",
        weak_ack=bool(knobs.get("weak_ack")),
        isolate_without_observe=bool(knobs.get("isolate_without_observe")),
        annotation_forge=knobs.get("mutate_after_approval") == "target_forged_fingerprint",
        self_witness_name=bool(knobs.get("self_witness_name") or knobs.get("locator_swap")),
        observer_mutate=bool(knobs.get("observer_mutate")),
        echo_observe=bool(knobs.get("echo_observe")),
        stale_approval=bool(knobs.get("bump_revision_after_activation")),
        dual_isolate=bool(knobs.get("race_terminal_heads")),
        duplicate_dispatch=bool(knobs.get("duplicate_entity_dispatch")),
    )


def replay_k8s(seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.eval_suite.k8s_chain import run_k8s_case
    from app.eval_suite.k8s_world import Gates

    rows: list[dict[str, Any]] = []
    for seed in seeds:
        case = _k8s_injection(seed.get("injection") or {}, seed["invariant"])
        naive = run_k8s_case(case, Gates.naive(), config_name="naive")
        full = run_k8s_case(case, Gates.full(), config_name="full")
        rows.append(
            {
                "chain": "k8s",
                "invariant": seed["invariant"],
                "trace": seed["trace"],
                "naive_harmed": naive.harmed,
                "full_harmed": full.harmed,
                "full_notes": full.notes,
            }
        )
    return rows


async def replay_soc(seeds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    from app.eval_suite.chain import (
        HARM_DUAL_DISPATCH,
        HARM_FALSE_VERIFY,
        HARM_LEAK,
        HARM_WRONG_ACT,
        HARM_WRONG_CLOSE,
        Injection,
        run_case,
    )

    harm_for = {
        "close": HARM_WRONG_CLOSE,
        "k8s_close": HARM_WRONG_CLOSE,
        "bind": HARM_WRONG_ACT,
        "egress": HARM_LEAK,
        "role": HARM_WRONG_CLOSE,
        "verify": HARM_FALSE_VERIFY,
        "head": HARM_DUAL_DISPATCH,
        "cas": HARM_DUAL_DISPATCH,
    }
    from app.eval_suite.configs import FULL, NAIVE, VendorColumn, harness_context
    from app.eval_suite.world import eval_world

    rows: list[dict[str, Any]] = []
    for seed in seeds:
        if seed["invariant"] == "k8s_close":
            continue
        knobs = dict(seed.get("injection") or {})
        knobs.pop("self_witness_name", None)
        knobs.pop("planner_privilege", None)
        knobs.pop("weak_ack", None)
        knobs.pop("isolate_without_observe", None)
        knobs.pop("observer_mutate", None)
        knobs.pop("echo_observe", None)
        if knobs.get("sql_bypass") and seed["invariant"] != "role":
            continue
        case = Injection(
            case_id=f"tla_{seed['invariant']}",
            adversary="TLA",
            harm=harm_for.get(seed["invariant"], HARM_WRONG_ACT),
            expected_mediator=seed["invariant"],
            description=f"TLC seed for {seed['invariant']}",
            **{k: v for k, v in knobs.items() if k in Injection.__dataclass_fields__},
        )
        pair: dict[str, bool] = {}
        for name, cfg in (("naive", NAIVE), ("full", FULL)):
            with harness_context(cfg, VendorColumn.MOCK):
                async with eval_world(
                    VendorColumn.MOCK, role_separation=cfg.role_separation
                ) as world:
                    outcome = await run_case(world, case, config_name=name)
                    pair[name] = bool(outcome.harmed)
        rows.append(
            {
                "chain": "soc",
                "invariant": seed["invariant"],
                "trace": seed["trace"],
                "naive_harmed": pair["naive"],
                "full_harmed": pair["full"],
            }
        )
    return rows


def render_markdown(k8s: list[dict[str, Any]], soc: list[dict[str, Any]] | None) -> str:
    lines = [
        "# TLC trace replay on both TEI instances",
        "",
        "Seeds are `tei_engine.emit_tlc_seeds()` (TEI.tla action names).",
        "k8s_close is Kubernetes-only; it is not replayed on the SOC chain.",
        "",
        "| chain | invariant | naive harmed | full harmed |",
        "|---|---|---|---|",
    ]
    for row in k8s + (soc or []):
        lines.append(
            f"| {row['chain']} | {row['invariant']} | "
            f"{int(row['naive_harmed'])} | {int(row['full_harmed'])} |"
        )
    lines.append("")
    return "\n".join(lines)


async def _run(skip_soc: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seeds = emit_tlc_seeds()
    k8s = replay_k8s(seeds)
    soc: list[dict[str, Any]] = []
    if not skip_soc:
        soc = await replay_soc(seeds)
    return k8s, soc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "replay"))
    parser.add_argument("--skip-soc", action="store_true")
    args = parser.parse_args(argv)
    k8s, soc = asyncio.run(_run(args.skip_soc))
    bypass = any(row["full_harmed"] for row in k8s + soc)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "TEI.tla",
        "step_injection": STEP_INJECTION,
        "k8s": k8s,
        "soc": soc,
        "bypass_found": bypass,
    }
    rendered = render_markdown(k8s, soc)
    print(rendered)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2)
    (out / "latest.json").write_text(text, encoding="utf-8")
    (out / "latest.md").write_text(rendered + "\n", encoding="utf-8")
    return 1 if bypass else 0


if __name__ == "__main__":
    raise SystemExit(main())
