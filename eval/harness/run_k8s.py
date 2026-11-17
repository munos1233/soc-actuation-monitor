#!/usr/bin/env python3
"""Kubernetes TEI instance. Never pooled with the SOC 57.

    python eval/harness/run_k8s.py --out eval/results/k8s
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.eval_suite.k8s_chain import run_k8s_suite  # noqa: E402
from app.eval_suite.k8s_world import Gates  # noqa: E402

_K8S = REPO_ROOT / "eval" / "k8s"
if str(_K8S) not in sys.path:
    sys.path.insert(0, str(_K8S))
from live_a0 import run_kind_a0  # noqa: E402


def _summarize(outcomes: list) -> dict[str, dict[str, str]]:
    by_adv: dict[str, Counter[str]] = {}
    for outcome in outcomes:
        bucket = by_adv.setdefault(outcome.adversary, Counter())
        bucket["n"] += 1
        bucket["harmed"] += int(outcome.harmed)
    return {
        adv: {"harmed": f"{c['harmed']}/{c['n']}"}
        for adv, c in sorted(by_adv.items())
    }


def render_markdown(naive: list, full: list) -> str:
    n_sum = _summarize(naive)
    f_sum = _summarize(full)
    lines = [
        "# Kubernetes TEI instance (not pooled with SOC 57)",
        "",
        "Lab control plane: RBAC + admission + etcd-like store. "
        "Author-controlled fixture; not a production cluster. "
        "Two cases (webhook-echoed observedReady, ingest identity spoof) "
        "are Kubernetes-native, not SOC Injection translations. "
        "Set TEI_K8S_LIVE=1 after eval/k8s/setup_kind.sh for kind A0 RBAC.",
        "",
        "| adversary | naive | full |",
        "|---|---|---|",
    ]
    for adv in ("A0", "A1", "A2", "A3", "A4", "A5"):
        lines.append(
            f"| {adv} | {n_sum.get(adv, {}).get('harmed', '—')} | "
            f"{f_sum.get(adv, {}).get('harmed', '—')} |"
        )
    n_h = sum(int(o.harmed) for o in naive)
    f_h = sum(int(o.harmed) for o in full)
    lines.append(f"| total | {n_h}/{len(naive)} | **{f_h}/{len(full)}** |")
    lines.append("")
    if f_h:
        lines.append("FULL HARM — do not freeze. Fix the TEI construction.")
        lines.append("")
        for outcome in full:
            if outcome.harmed:
                lines.append(f"- `{outcome.case_id}` {outcome.harms} {outcome.notes}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "k8s"))
    args = parser.parse_args(argv)
    naive = run_k8s_suite(Gates.naive(), config_name="naive")
    full = run_k8s_suite(Gates.full(), config_name="full")
    kind_a0 = run_kind_a0()
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "pooled_with_soc57": False,
        "naive": [o.as_json() for o in naive],
        "full": [o.as_json() for o in full],
        "naive_harmed": sum(int(o.harmed) for o in naive),
        "full_harmed": sum(int(o.harmed) for o in full),
        "n": len(naive),
        "kind_a0": kind_a0,
        "fixture": "in-process LabControlPlane",
    }
    extra = ""
    if kind_a0.get("skipped"):
        extra = f"\nkind A0: skipped ({kind_a0.get('reason')})\n"
    elif kind_a0.get("ok"):
        extra = "\nkind A0 RBAC: planner denied, writer allowed.\n"
    else:
        extra = "\nkind A0 RBAC: failed parity. See latest.json kind_a0.\n"
    rendered = render_markdown(naive, full) + extra
    print(rendered)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    text = json.dumps(payload, indent=2)
    (out / f"run-{stamp}.json").write_text(text, encoding="utf-8")
    (out / "latest.json").write_text(text, encoding="utf-8")
    (out / "latest.md").write_text(rendered, encoding="utf-8")
    return 1 if payload["full_harmed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
