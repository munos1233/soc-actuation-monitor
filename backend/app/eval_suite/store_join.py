"""A1–A5 cells: needs_store_join vs request_closed.

The 16 OPA / HMAC residuals are exactly the needs_store_join cells.
This is completeness relative to the suite, not an open-world taxonomy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.eval_suite.cases import A1_CASES, A2_CASES, A3_CASES, A4_CASES, A5_CASES, Injection

TAXONOMY = Path(__file__).resolve().parents[3] / "eval" / "taxonomy" / "store_join.json"

NEEDS_STORE_JOIN_IDS = frozenset(json.loads(TAXONOMY.read_text(encoding="utf-8"))["needs_store_join_case_ids"])

A15_CASES: tuple[Injection, ...] = (*A1_CASES, *A2_CASES, *A3_CASES, *A4_CASES, *A5_CASES)


def classify(case_id: str) -> str:
    if case_id.startswith("a0_"):
        return "role_split"
    if case_id in NEEDS_STORE_JOIN_IDS:
        return "needs_store_join"
    return "request_closed"


def a15_cells() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for case in A15_CASES:
        for column in case.columns:
            if column == "sangfor_stub":
                continue
            rows.append((case.case_id, column))
    return rows


def needs_store_join_cells() -> list[tuple[str, str]]:
    return [row for row in a15_cells() if classify(row[0]) == "needs_store_join"]


def residual_case_ids(rows: list[dict[str, Any]], config: str) -> set[str]:
    out: set[str] = set()
    for row in rows:
        if row.get("config") != config:
            continue
        cid = str(row.get("case_id") or "")
        if cid.startswith("a0_"):
            continue
        if row.get("harmed"):
            out.add(cid)
    return out
