"""Lattice projector still matches frozen pairs; live is a Make path."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_project_only_matches_frozen_pairs(tmp_path: Path) -> None:
    harness = ROOT / "eval" / "harness" / "run_lattice.py"
    proc = subprocess.run(
        [
            sys.executable,
            str(harness),
            "--project-only",
            "--out",
            str(tmp_path),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    payload = (tmp_path / "latest.json").read_text()
    assert "close_and_bind" in payload
    assert '"live": null' in payload or '"live":null' in payload.replace(" ", "")
