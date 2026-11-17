#!/usr/bin/env python3
"""Kind TEI instance: Gatekeeper/attribute vs TEI webhook vs naive.

Headline C5 table. Never copies the fixture 22/22. Fails if kind is required
and the cluster is missing. In-process corpus scoring is for tests only and
is labelled method=shared_predicates — not a kind freeze.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "eval" / "k8s"))

from app.eval_suite.kind_corpus import (  # noqa: E402
    attack_cases,
    golden_cases,
    real_api_cases,
    run_kind_corpus,
    tei_lab_mapped_cases,
)

ARMS = ("kind_naive", "kind_attribute", "kind_tei")


def _kind_ready() -> tuple[bool, str]:
    kind_bin = REPO_ROOT / "eval" / "k8s" / "bin"
    os.environ["PATH"] = f"{kind_bin}:{os.environ.get('PATH', '')}"
    if shutil.which("kubectl") is None:
        return False, "kubectl not installed"
    if shutil.which("kind") is None:
        return False, "kind not installed"
    proc = subprocess.run(
        ["kubectl", "config", "current-context"],
        capture_output=True,
        text=True,
        check=False,
    )
    ctx = (proc.stdout or "").strip()
    if "tei-lab" in ctx:
        return True, ctx
    if os.environ.get("TEI_K8S_KIND", "").strip() in {"1", "true"}:
        return False, f"TEI_K8S_KIND set but kubectl context is {ctx or 'unset'}"
    return False, f"kubectl context is {ctx or 'unset'}; need kind tei-lab or TEI_K8S_KIND=1"


def _attribute_baseline() -> str:
    override = os.environ.get("TEI_K8S_ATTRIBUTE_BASELINE", "").strip()
    if override:
        return override
    marker = REPO_ROOT / "eval" / "k8s" / ".attribute-baseline"
    if marker.is_file():
        return marker.read_text(encoding="utf-8").strip() or "gatekeeper"
    proc = subprocess.run(
        ["kubectl", "get", "constrainttemplate"],
        capture_output=True,
        text=True,
        check=False,
    )
    return "gatekeeper" if proc.returncode == 0 else "validatingadmissionpolicy"


def _arm_counts(rows: list, cases) -> str:
    ids = {case.case_id for case in cases}
    subset = [r for r in rows if r["case_id"] in ids]
    harmed = sum(1 for r in subset if r["harmed"])
    return f"{harmed}/{len(subset)}"


def _golden_cell(rows: list) -> str:
    ids = {case.case_id for case in golden_cases()}
    subset = [r for r in rows if r["case_id"] in ids]
    blocked = sum(1 for r in subset if r["harmed"])
    return "passes" if blocked == 0 else f"BLOCKED {blocked}"


def render(payload: dict) -> str:
    lines = [
        "# Kubernetes TEI instance (kind / mapped sample)",
        "",
        "Not pooled with SOC 57. Not the fixture 22/22.",
        "Mapped, not reproduced on the original product.",
        "Real-API subset and tei.lab mapped subset are not merged.",
        f"method: {payload['method']}",
        f"attribute baseline: {payload.get('attribute_baseline', 'n/a')}",
        "",
        "| arm | attack (n=11) | real-API attack | tei.lab attack | golden persists |",
        "|---|---|---|---|---|",
    ]
    for arm in ARMS:
        rows = payload["arms"][arm]
        lines.append(
            f"| `{arm}` | {_arm_counts(rows, attack_cases())} | "
            f"{_arm_counts(rows, [c for c in real_api_cases() if c in attack_cases()])} | "
            f"{_arm_counts(rows, [c for c in tei_lab_mapped_cases() if c in attack_cases()])} | "
            f"{_golden_cell(rows)} |"
        )
    by = {arm: {r["case_id"]: r["harmed"] for r in payload["arms"][arm]} for arm in ARMS}

    def _table(title: str, cases) -> None:
        lines.append("")
        lines.append(title)
        lines.append("")
        lines.append("| case | sample | naive | attribute | tei |")
        lines.append("|---|---|---|---|---|")
        for case in cases:
            is_golden = case in golden_cases()
            if is_golden:
                cells = [
                    ("blocked" if by[arm][case.case_id] else "persists")
                    for arm in ARMS
                ]
            else:
                cells = [("harm" if by[arm][case.case_id] else "ok") for arm in ARMS]
            label = " *(golden)*" if is_golden else ""
            lines.append(
                f"| `{case.case_id}`{label} | `{case.sample_id}` | " + " | ".join(cells) + " |"
            )

    _table(
        "## Real API (`networking.k8s.io` / ownerRef / ClusterRole)",
        real_api_cases(),
    )
    _table(
        "## Still `tei.lab` mapped (not merged into the real-API column)",
        tei_lab_mapped_cases(),
    )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(REPO_ROOT / "eval" / "results" / "k8s-kind"))
    parser.add_argument(
        "--allow-shared-predicates",
        action="store_true",
        help="tests only: score tei_admit without kind. Forbidden as a paper freeze.",
    )
    args = parser.parse_args(argv)
    ready, reason = _kind_ready()
    if not ready and os.environ.get("TEI_K8S_KIND", "").strip() in {"1", "true"}:
        setup = subprocess.run(
            ["bash", str(REPO_ROOT / "eval" / "k8s" / "setup_kind.sh")],
            check=False,
        )
        if setup.returncode != 0:
            print(
                f"kind cluster required for C5 headline; setup failed ({reason}); "
                "refusing fixture fallback",
                file=sys.stderr,
            )
            out = Path(args.out)
            out.mkdir(parents=True, exist_ok=True)
            payload = {
                "generated_at": datetime.now(UTC).isoformat(),
                "failed": True,
                "reason": f"setup_kind.sh exit {setup.returncode}; {reason}",
                "copied_fixture_22": False,
            }
            (out / "latest.json").write_text(json.dumps(payload, indent=2) + "\n")
            return 1
        ready, reason = _kind_ready()
    if not ready and not args.allow_shared_predicates:
        print(
            f"kind cluster required for C5 headline; refusing fixture fallback ({reason})",
            file=sys.stderr,
        )
        out = Path(args.out)
        out.mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(UTC).isoformat(),
            "failed": True,
            "reason": reason,
            "copied_fixture_22": False,
        }
        (out / "latest.json").write_text(json.dumps(payload, indent=2) + "\n")
        return 1
    if ready and not args.allow_shared_predicates:
        from live_corpus import run_live_corpus  # noqa: WPS433

        method = os.environ.get("TEI_K8S_METHOD_LABEL", "").strip() or "kind_cluster"
        attribute_baseline = _attribute_baseline()
        arms = {arm: run_live_corpus(arm, attribute_baseline) for arm in ARMS}
    else:
        method = "shared_predicates"
        attribute_baseline = "gatekeeper"
        arms = {arm: run_kind_corpus(arm) for arm in ARMS}
    tei_harm = sum(1 for r in arms["kind_tei"] if r["harmed"])
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "method": method,
        "attribute_baseline": attribute_baseline,
        "pooled_with_57": False,
        "fixture_22": False,
        "copied_fixture_22": False,
        "arms": arms,
    }
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    md = render(payload)
    (out / "latest.json").write_text(json.dumps(payload, indent=2) + "\n")
    (out / "latest.md").write_text(md + "\n")
    print(md)
    if tei_harm:
        print("kind_tei harmed; fix TEI admission and re-freeze this suite only", file=sys.stderr)
        return 1
    if method == "shared_predicates":
        print("shared_predicates is not a kind freeze", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
