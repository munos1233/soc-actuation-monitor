"""Optional kind A0: planner SA cannot create privileged objects; writer can.

Requires TEI_K8S_LIVE=1 and a cluster created by setup_kind.sh. This is RBAC
parity, not the 22-case fixture.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any

NS = "tei-lab"
PLANNER = f"system:serviceaccount:{NS}:planner"
WRITER = f"system:serviceaccount:{NS}:writer"


def live_enabled() -> bool:
    return os.environ.get("TEI_K8S_LIVE", "").strip() in {"1", "true", "yes"}


def _kubectl(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["kubectl", *args],
        check=False,
        capture_output=True,
        text=True,
    )


def run_kind_a0() -> dict[str, Any]:
    if not live_enabled():
        return {"skipped": True, "reason": "TEI_K8S_LIVE unset"}
    if shutil.which("kubectl") is None:
        return {"skipped": True, "reason": "kubectl not installed"}
    checks = [
        ("planner_create_networkpolicy", PLANNER, "create", "networkpolicies"),
        ("writer_create_networkpolicy", WRITER, "create", "networkpolicies"),
        ("planner_delete_networkpolicy", PLANNER, "delete", "networkpolicies"),
        ("writer_delete_networkpolicy", WRITER, "delete", "networkpolicies"),
    ]
    rows: list[dict[str, str]] = []
    for name, who, verb, resource in checks:
        proc = _kubectl("auth", "can-i", verb, resource, f"--as={who}", "-n", NS)
        allowed = proc.stdout.strip() == "yes"
        rows.append(
            {
                "check": name,
                "as": who,
                "verb": verb,
                "allowed": "yes" if allowed else "no",
            }
        )
    planner_denied = all(
        row["allowed"] == "no" for row in rows if row["as"] == PLANNER
    )
    writer_allowed = all(row["allowed"] == "yes" for row in rows if row["as"] == WRITER)
    return {
        "skipped": False,
        "rows": rows,
        "planner_denied": planner_denied,
        "writer_allowed": writer_allowed,
        "ok": planner_denied and writer_allowed,
    }
