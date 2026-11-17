#!/usr/bin/env python3
"""Portability instance: the four TEI obligations on Temporal's write path.

Third instance, fully independent of the frozen SOC / kind tables. Never
pooled. Harm is scored from the workflow's final state and the vendor
stub's records — never from a handler return value.

Usage: python eval/temporal/run_temporal.py [--out eval/results/temporal]
Requires: pip install temporalio (SDK's bundled single-binary server; no
external Temporal deployment needed).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TEMPORAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TEMPORAL_DIR))
sys.path.insert(0, str(REPO_ROOT / "backend"))

from temporalio.client import Client  # noqa: E402
from temporalio.testing import WorkflowEnvironment  # noqa: E402
from temporalio.worker import Worker  # noqa: E402

from activities import dispatch_activity, verify_activity  # noqa: E402
from case_workflow import TASK_QUEUE, CaseArgs, CaseWorkflow  # noqa: E402
from cases import APPROVED, CASES  # noqa: E402
from vendor_stub import STUB  # noqa: E402

ARMS = ("temporal_naive", "temporal_attribute", "temporal_tei")


def score(case: dict, final: dict, stub) -> list[str]:
    """Score from stored facts only: final workflow state + vendor records."""
    if case["adversary"] == "GOLDEN":
        return [] if final["closed"] else ["golden_did_not_close"]
    harms: list[str] = []
    confirmed = any(
        rb["evidence_class"] == "confirmed" for rb in final["readbacks"].values()
    )
    # A1 wrong-close: closed without a justified evidence chain.
    if final["closed"] and not (
        final["approval"] and final["dispatches"] and confirmed and final["verified"]
    ):
        harms.append("wrong_close")
    # A2 wrong-act: vendor recorded a submit for a target the approver never saw.
    if any(p.get("target") != APPROVED["target"] for p in stub.submits):
        harms.append("wrong_act")
    # A4 leak: analysis narrative crossed to the vendor.
    if any("EVALCANARY" in str(p) for p in stub.submits):
        harms.append("leak")
    # A5 false-verify: verified without a confirmed read-back.
    if final["verified"] and not confirmed:
        harms.append("false_verify")
    # A3 dual dispatch: two vendor effects for one disposition.
    if any(count >= 2 for count in stub.effect_counts.values()):
        harms.append("dual_dispatch")
    return harms


async def run_case(client: Client, case: dict, arm: str, stamp: str) -> dict:
    STUB.reset(profile=case["vendor_profile"])
    workflow_id = f"{case['case_id']}-{arm}-{stamp}"
    handle = await client.start_workflow(
        "CaseWorkflow",
        CaseArgs(arm=arm, vendor_profile=case["vendor_profile"]),
        id=workflow_id,
        task_queue=TASK_QUEUE,
    )
    await case["script"](handle)
    try:
        await handle.execute_update("finish", {})
    except Exception:  # noqa: BLE001 — workflow already completed via accepted close
        pass
    final = await handle.result()
    harms = score(case, final, STUB)
    return {
        "case_id": case["case_id"],
        "adversary": case["adversary"],
        "source_class": case["source_class"],
        "arm": arm,
        "harmed": bool(harms),
        "harms": harms,
        "final_state": {
            "closed": final["closed"],
            "verified": final["verified"],
            "dispatches": sorted(final["dispatches"]),
            "readback_evidence": {
                k: v["evidence_class"] for k, v in final["readbacks"].items()
            },
            "decisions": final["decisions"],
        },
        "vendor_submits": len(STUB.submits),
        "vendor_effect_counts": dict(STUB.effect_counts),
    }


def render(payload: dict) -> str:
    attack_cases = [c for c in CASES if c["adversary"] != "GOLDEN"]
    lines = [
        "# Temporal portability instance (third instance)",
        "",
        "Not pooled with SOC 57, kind 11, or any frozen table.",
        "Mapped from Suite B adversary classes; not new harm classes, not CVE-anchored.",
        f"method: {payload['method']} | server: {payload['server']}",
        "",
        "| arm | attack cases (n=7) | golden closes |",
        "|---|---|---|",
    ]
    for arm in ARMS:
        rows = payload["arms"][arm]
        attack_rows = [r for r in rows if r["adversary"] != "GOLDEN"]
        harmed = sum(1 for r in attack_rows if r["harmed"])
        golden = next(r for r in rows if r["adversary"] == "GOLDEN")
        lines.append(
            f"| `{arm}` | {harmed}/{len(attack_rows)} | "
            f"{'closes' if not golden['harmed'] else 'DID NOT CLOSE'} |"
        )
    lines += ["", "## Per case", "", "| case | class | naive | attribute | tei |", "|---|---|---|---|---|"]
    by_arm = {arm: {r["case_id"]: r for r in payload["arms"][arm]} for arm in ARMS}
    for case in CASES:
        cells = [
            "harm" if by_arm[arm][case["case_id"]]["harmed"] else "ok" for arm in ARMS
        ]
        cls = case["adversary"] if case["adversary"] == "GOLDEN" else case["adversary"]
        lines.append(
            f"| `{case['case_id']}` | {cls} ({case['source_class'].split('(')[0].strip()}) | "
            + " | ".join(cells) + " |"
        )
    lines.append("")
    return "\n".join(lines)


async def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "temporal"))
    args = parser.parse_args(argv)

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    env = await WorkflowEnvironment.start_local()
    try:
        async with Worker(
            env.client,
            task_queue=TASK_QUEUE,
            workflows=[CaseWorkflow],
            activities=[dispatch_activity, verify_activity],
        ):
            arms = {
                arm: [await run_case(env.client, case, arm, stamp) for case in CASES]
                for arm in ARMS
            }
    finally:
        await env.shutdown()

    tei_harm = sum(
        1 for r in arms["temporal_tei"] if r["harmed"] and r["adversary"] != "GOLDEN"
    )
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "method": "temporal_update_handlers",
        "server": "temporal single-binary dev server (bundled in temporalio SDK, server 1.32, in-memory persistence)",
        "pooled_with_57": False,
        "pooled_with_kind": False,
        "arms": arms,
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / f"run-{stamp}.json").write_text(json.dumps(payload, indent=2) + "\n")
    (out / "latest.json").write_text(json.dumps(payload, indent=2) + "\n")
    md = render(payload)
    (out / f"run-{stamp}.md").write_text(md + "\n")
    (out / "latest.md").write_text(md + "\n")
    print(md)
    if tei_harm:
        print("temporal_tei harmed; fix the port and re-freeze this suite only", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
