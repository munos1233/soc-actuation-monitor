"""Git identity for paper freeze JSON. Never invent a hash."""

from __future__ import annotations

import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]


def git_head(repo: Path | None = None) -> str:
    try:
        return (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                cwd=repo or _REPO,
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception:  # noqa: BLE001
        return "unknown"


def git_dirty(repo: Path | None = None) -> bool:
    try:
        out = subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=repo or _REPO,
            stderr=subprocess.DEVNULL,
        )
        return bool(out.strip())
    except Exception:  # noqa: BLE001
        return False
