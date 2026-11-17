#!/usr/bin/env python3
"""Check TEI.tla with the shared engine and Java TLC.

    python eval/harness/run_tla.py --out eval/results/tla

`make paper-eval-tla` requires a JVM and a checksummed tla2tools.jar.
`--engine-only` keeps the same Next for CI hosts without Java; it must
not write tlc.ran=true.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODEL = REPO_ROOT / "eval" / "model"
FETCH = REPO_ROOT / "scripts" / "fetch_tlc.sh"
if str(MODEL) not in sys.path:
    sys.path.insert(0, str(MODEL))

from tei_engine import (  # noqa: E402
    ACTION_HONEST_ADVANCE,
    ACTION_PLANNER_FORGE,
    ACTION_PLANNER_STALE,
    LADDER,
    Mechanisms,
    close_witness_pair,
    emit_tlc_seeds,
    explore,
    explore_view_pair,
)


EXPECTED_CE = {
    "minus_close": "close",
    "minus_bind": "bind",
    "minus_egress": "egress",
    "minus_role": "role",
    "minus_verify": "verify",
    "minus_head": "head",
    "minus_cas": "cas",
}
ATTRIBUTE_ONLY_REQUIRED = ("close", "bind")

TLC_SPECS = (
    {
        "name": "full",
        "spec": "TEI.tla",
        "cfg": "tei.cfg",
        "log": "tlc-full.log",
        "expect_ce": False,
        "expect_actions": (),
    },
    {
        "name": "attribute_only",
        "spec": "TEI.tla",
        "cfg": "tei-attribute-only.cfg",
        "log": "tlc-attribute-only.log",
        "expect_ce": True,
        "expect_actions": (ACTION_PLANNER_STALE, ACTION_PLANNER_FORGE),
    },
    {
        "name": "view_pair",
        "spec": "TEIPair.tla",
        "cfg": "tei-view-pair.cfg",
        "log": "tlc-view-pair.log",
        "expect_ce": True,
        "expect_actions": (ACTION_HONEST_ADVANCE, ACTION_PLANNER_STALE),
    },
    {
        "name": "minus_cas",
        "spec": "TEI.tla",
        "cfg": "tei-minus-cas.cfg",
        "log": "tlc-minus-cas.log",
        "expect_ce": True,
        "expect_actions": (),
    },
)


def _java() -> str | None:
    for candidate in (
        shutil.which("java"),
        "/opt/homebrew/opt/openjdk@17/bin/java",
        "/opt/homebrew/opt/openjdk/bin/java",
        "/usr/libexec/java_home",
    ):
        if candidate is None:
            continue
        path = Path(candidate)
        if path.name == "java_home":
            continue
        if path.is_file():
            return str(path)
    return shutil.which("java")


def _sanitize_tlc_log(text: str) -> str:
    """Drop host paths so frozen logs can ship in the anonymous artifact."""
    text = text.replace(str(REPO_ROOT), ".")
    text = re.sub(r"/Users/[^/\s]+", "/home/reviewer", text)
    text = re.sub(r"/private/var/folders/\S+?/", "/tmp/", text)
    return text


def _parse_tlc(log_text: str) -> dict[str, object]:
    states = None
    match = re.search(r"(\d+)\s+states generated", log_text)
    if match:
        states = int(match.group(1))
    distinct = None
    match = re.search(r"(\d+)\s+distinct states found", log_text)
    if match:
        distinct = int(match.group(1))
    no_error = "No error has been found" in log_text
    invariant = None
    match = re.search(r"Invariant (\w+) is violated", log_text)
    if match:
        invariant = match.group(1)
    actions: list[str] = []
    for raw in re.findall(r"<(?:Action )?([A-Za-z][A-Za-z0-9_]*)\b", log_text):
        name = raw
        if name in {"Initial", "Init"}:
            continue
        if name.startswith("A_") or name.startswith("B_"):
            name = name.split("_", 1)[1]
        if name not in actions and name[0].isupper():
            actions.append(name)
    return {
        "states_generated": states,
        "distinct_states": distinct,
        "no_error": no_error,
        "violated_invariant": invariant,
        "actions": actions,
    }


def _run_one_tlc(java: str, jar: Path, spec: str, cfg: str, log_path: Path) -> dict[str, object]:
    proc = subprocess.run(
        [
            java,
            "-XX:+UseParallelGC",
            "-cp",
            str(jar),
            "tlc2.TLC",
            "-workers",
            "1",
            "-noTE",
            "-config",
            str(MODEL / cfg),
            str(MODEL / spec),
        ],
        cwd=str(MODEL),
        capture_output=True,
        text=True,
        check=False,
    )
    text = _sanitize_tlc_log(proc.stdout + "\n" + proc.stderr)
    log_path.write_text(text, encoding="utf-8")
    parsed = _parse_tlc(text)
    parsed["returncode"] = proc.returncode
    try:
        parsed["log"] = str(log_path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        parsed["log"] = str(log_path)
    parsed["spec"] = spec
    parsed["cfg"] = cfg
    return parsed


def _run_tlc(out_dir: Path, require: bool) -> dict[str, object]:
    java = _java()
    jar = MODEL / "tla2tools.jar"
    if not jar.is_file() and FETCH.is_file():
        fetch = subprocess.run(["bash", str(FETCH)], check=False)
        if fetch.returncode != 0 and require:
            return {
                "ran": False,
                "reason": "scripts/fetch_tlc.sh failed",
            }
    if java is None or not jar.is_file():
        payload = {
            "ran": False,
            "reason": "java or eval/model/tla2tools.jar missing",
        }
        if require:
            payload["error"] = "TLC is required; engine  states must not be reported as TLC"
        return payload
    checks: dict[str, object] = {}
    ok = True
    reasons: list[str] = []
    for item in TLC_SPECS:
        parsed = _run_one_tlc(java, jar, item["spec"], item["cfg"], out_dir / item["log"])
        checks[item["name"]] = parsed
        has_ce = bool(parsed.get("violated_invariant")) or not parsed.get("no_error")
        if item["expect_ce"]:
            if not has_ce:
                ok = False
                reasons.append(f"{item['name']} expected a CE")
            actions = set(parsed.get("actions") or [])
            missing = [name for name in item["expect_actions"] if name not in actions]
            if missing and item["name"] == "view_pair":
                ok = False
                reasons.append(f"{item['name']} missing actions {missing}")
            if missing and item["name"] == "attribute_only":
                # AttributeOnly may stop at the first invariant (close or bind).
                if ACTION_PLANNER_STALE not in actions and ACTION_PLANNER_FORGE not in actions:
                    ok = False
                    reasons.append(f"{item['name']} missing close/bind CE actions")
        elif has_ce:
            ok = False
            reasons.append(f"{item['name']} unexpectedly has a CE")
        if item["name"] == "full" and parsed.get("returncode") not in (0, None):
            ok = False
            reasons.append("full TLC returncode")
    return {
        "ran": True,
        "ok": ok,
        "reason": "; ".join(reasons) if reasons else None,
        "checks": checks,
        "java": java,
        "jar": str(jar.resolve().relative_to(REPO_ROOT)),
    }


def render_markdown(
    results: list[dict],
    tlc: dict[str, object],
    pair: dict[str, object],
    witness: dict[str, object],
) -> str:
    lines = [
        "## TEI.tla / TLC",
        "",
        "Source of truth: `eval/model/TEI.tla`. Engine: `eval/model/tei_engine.py`.",
        "Twin spec: `eval/model/TEIPair.tla`. View lemma: `eval/model/view_lemma.md`.",
        "",
        f"Java TLC: ran={tlc.get('ran')} ok={tlc.get('ok')} {tlc.get('reason') or ''}".rstrip(),
        "",
        "| mechanisms | engine states | close | bind | egress | role | verify | head | k8s_close | cas |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    keys = ("close", "bind", "egress", "role", "verify", "head", "k8s_close", "cas")
    for result in results:
        cells = []
        for key in keys:
            trace = result["violations"].get(key)
            cells.append("holds" if trace is None else f"CE {len(trace)}")
        lines.append(
            f"| `{result['mechanisms']}` | {result['states']} | "
            + " | ".join(cells)
            + " |"
        )
    lines.append("")
    lines.append("### Shortest counterexamples")
    lines.append("")
    for result in results:
        for key in keys:
            trace = result["violations"].get(key)
            if not trace:
                continue
            lines.append(f"**{key} under `{result['mechanisms']}`**")
            lines.append("")
            for index, step in enumerate(trace, start=1):
                lines.append(f"{index}. `{step}`")
            lines.append("")
    lines.append("### View indistinguishability")
    lines.append("")
    lines.append(
        f"Witness: `{witness.get('honest_action')}` vs "
        f"`{witness.get('stale_action')}`; same AttrView, CloseOK differs."
    )
    lines.append("")
    ce = pair.get("inv_view_close_ce")
    if ce:
        lines.append("Engine pair CE: " + " → ".join(f"`{step}`" for step in ce))
        lines.append("")
    checks = tlc.get("checks") if isinstance(tlc.get("checks"), dict) else {}
    if checks:
        lines.append("### Java TLC")
        lines.append("")
        for name, parsed in checks.items():
            if not isinstance(parsed, dict):
                continue
            inv = parsed.get("violated_invariant") or "no CE"
            distinct = parsed.get("distinct_states")
            actions = parsed.get("actions") or []
            lines.append(
                f"- `{name}` (`{parsed.get('cfg')}`): {inv}; "
                f"distinct={distinct}; actions={actions}"
            )
        lines.append("")
    lines.append("### Claim-CAS lemma")
    lines.append("")
    lines.append(
        "HeadUnique is the head layer; ClaimCAS is the status layer "
        "(lost effect, not dual-write). `minus_cas` violates InvCAS "
        "(claimCount=2). tei-reads-s.cfg is the dual of AttributeOnly: "
        "reading S, no CE. See `eval/model/cas_lemma.md` and "
        "`eval/model/view_lemma.md`."
    )
    lines.append("")
    return "\n".join(lines)


def _engine_ok(results: list[dict]) -> int:
    full = next(r for r in results if r["mechanisms"] == "full")
    if full["violations"]:
        return 1
    if not full["cas_status_layer_holds"]:
        return 1
    for mech in LADDER:
        if mech.name == "full":
            continue
        result = next(r for r in results if r["mechanisms"] == mech.name)
        if mech.name == "attribute_only":
            missing = [key for key in ATTRIBUTE_ONLY_REQUIRED if key not in result["violations"]]
            if missing:
                print(f"attribute_only missing CE {missing}", file=sys.stderr)
                return 1
            continue
        expected = EXPECTED_CE.get(mech.name)
        if expected and expected not in result["violations"]:
            print(f"missing CE for {mech.name}", file=sys.stderr)
            return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "eval" / "results" / "tla")
    parser.add_argument(
        "--engine-only",
        action="store_true",
        help="Skip TLC. Must not be used to claim tlc.ran=true.",
    )
    parser.add_argument(
        "--require-tlc",
        action="store_true",
        default=True,
        help="Fail if Java TLC cannot run the three configs (default).",
    )
    parser.add_argument(
        "--allow-missing-tlc",
        action="store_true",
        help="Do not fail when Java/jar is missing. tlc.ran stays false.",
    )
    args = parser.parse_args(argv)
    args.out = args.out.resolve()
    require = bool(args.require_tlc) and not args.allow_missing_tlc and not args.engine_only
    results = [explore(mech) for mech in LADDER]
    seeds = emit_tlc_seeds()
    witness = close_witness_pair()
    pair = explore_view_pair()
    args.out.mkdir(parents=True, exist_ok=True)
    if args.engine_only:
        tlc: dict[str, object] = {
            "ran": False,
            "reason": "engine-only; Java TLC was not run",
        }
    else:
        tlc = _run_tlc(args.out, require=require)
    payload = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source": "TEI.tla",
        "engine": "tei_engine.py",
        "tlc": tlc,
        "results": results,
        "seeds": seeds,
        "view": {
            "attr_view": witness["attr_view"],
            "same_view": witness["same_view"],
            "close_ok_honest": witness["close_ok_honest"],
            "close_ok_stale": witness["close_ok_stale"],
            "honest_action": witness["honest_action"],
            "stale_action": witness["stale_action"],
            "engine_pair": pair,
        },
    }
    markdown = render_markdown(results, tlc, pair, witness)
    (args.out / "latest.json").write_text(
        json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8"
    )
    (args.out / "latest.md").write_text(markdown + "\n", encoding="utf-8")
    (args.out / "tlc-traces.json").write_text(
        json.dumps(seeds, indent=2) + "\n", encoding="utf-8"
    )
    print(markdown)
    status = _engine_ok(results)
    if not witness["same_view"] or witness["close_ok_honest"] == witness["close_ok_stale"]:
        print("view witness pair failed", file=sys.stderr)
        return 1
    if pair["inv_view_close_holds"]:
        print("engine pair missed InvViewClose CE", file=sys.stderr)
        return 1
    if require and not tlc.get("ran"):
        print(tlc.get("reason") or "TLC did not run", file=sys.stderr)
        return 1
    if tlc.get("ran") and tlc.get("ok") is False:
        print(tlc.get("reason") or "TLC check failed", file=sys.stderr)
        return 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
