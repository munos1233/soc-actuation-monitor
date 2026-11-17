"""Planner-only process probe: the writer factory is a login this process lacks.

The Suite B parent is the actuation process. This probe additionally spawns a
child with PROCESS_ROLE=planner and no ACTUATION_DATABASE_URL and checks three
facts: the child cannot construct the writer factory, planner SQL is still
42501, and the actuation parent can still close a golden event.
"""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import os
from dataclasses import dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.eval_suite.chain import run_case
from app.eval_suite.configs import FULL, VendorColumn, harness_context
from app.eval_suite.gold import GOLDEN_CASES
from app.eval_suite.world import eval_world

PLANNER_STATEMENTS: tuple[str, ...] = (
    "UPDATE security_event SET status = 'closed' WHERE false",
    "INSERT INTO disposition_outbox (outbox_id, writeback_id, disposition_id, "
    "action_id, event_id, closure_cycle, source_record_id, source_locator_hash, "
    "source_sequence, intent_kind, logical_slot, idempotency_key, command_payload, "
    "command_payload_sha256) VALUES "
    "('obx-process-split', 'wbk-x', 'disp-x', 'missing', 'missing', 1, 'missing', "
    "'h', 1, 'event_status_update', 'terminal', 'idem-process-split', '{}'::jsonb, "
    "'0')",
)


def _planner_child(queue: mp.Queue[dict[str, Any]], owner_url: str) -> None:
    os.environ["PROCESS_ROLE"] = "planner"
    os.environ["DATABASE_URL"] = owner_url
    os.environ.pop("ACTUATION_DATABASE_URL", None)
    from app.core.config import get_settings
    from app.db.actuation_roles import derived_planner_url
    from app.db.session_provider import (
        ActuationLoginForbidden,
        get_session_provider,
        reset_session_provider,
    )

    get_settings.cache_clear()
    reset_session_provider()
    payload: dict[str, Any] = {
        "factory_refused": False,
        "factory_error": "",
        "sqlstates": [],
        "process_role": "",
    }
    try:
        settings = get_settings()
        payload["process_role"] = str(settings.process_role)
        try:
            get_session_provider().actuation_session_factory()
        except ActuationLoginForbidden:
            payload["factory_refused"] = True
        except Exception as exc:  # noqa: BLE001 — child reports, parent asserts
            payload["factory_error"] = f"{type(exc).__name__}: {exc}"

        planner_url = derived_planner_url(owner_url)

        async def _sqlstates() -> list[str | None]:
            states: list[str | None] = []
            engine = create_async_engine(planner_url)
            try:
                for sql in PLANNER_STATEMENTS:
                    try:
                        async with engine.begin() as conn:
                            await conn.execute(text(sql))
                        states.append(None)
                    except DBAPIError as exc:
                        orig = getattr(exc, "orig", None)
                        states.append(
                            getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
                        )
            finally:
                await engine.dispose()
            return states

        payload["sqlstates"] = asyncio.run(_sqlstates())
    except Exception as exc:  # noqa: BLE001
        payload["factory_error"] = f"{type(exc).__name__}: {exc}"
    queue.put(payload)


@dataclass
class ProcessSplitReport:
    parent_gold_closed: bool
    parent_gold_after_closed: bool
    child_factory_refused: bool
    child_sql_42501: bool
    child_process_role: str
    child_sqlstates: list[str | None]
    child_error: str

    def ok(self) -> bool:
        return (
            self.parent_gold_closed
            and self.parent_gold_after_closed
            and self.child_factory_refused
            and self.child_sql_42501
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "parent_gold_closed": self.parent_gold_closed,
            "parent_gold_after_closed": self.parent_gold_after_closed,
            "child_factory_refused": self.child_factory_refused,
            "child_sql_42501": self.child_sql_42501,
            "child_process_role": self.child_process_role,
            "child_sqlstates": self.child_sqlstates,
            "child_error": self.child_error,
            "ok": self.ok(),
        }


async def _close_gold(column: VendorColumn) -> bool:
    with harness_context(FULL, column):
        async with eval_world(column, role_separation=True) as world:
            outcome = await run_case(world, GOLDEN_CASES[0], config_name=FULL.name)
            return bool(outcome.closed)


async def run_process_split_probe(
    *,
    column: VendorColumn = VendorColumn.MOCK,
    owner_url: str | None = None,
) -> ProcessSplitReport:
    owner = owner_url or os.environ["DATABASE_URL"]
    parent_first = await _close_gold(column)
    ctx = mp.get_context("spawn")
    queue: mp.Queue[dict[str, Any]] = ctx.Queue()
    child = ctx.Process(target=_planner_child, args=(queue, owner))
    child.start()
    child.join(timeout=90)
    if child.is_alive():
        child.kill()
        child.join(timeout=5)
        raise RuntimeError("planner-role child did not exit")
    payload = queue.get_nowait()
    parent_after = await _close_gold(column)
    states = list(payload.get("sqlstates") or [])
    return ProcessSplitReport(
        parent_gold_closed=parent_first,
        parent_gold_after_closed=parent_after,
        child_factory_refused=bool(payload.get("factory_refused")),
        child_sql_42501=bool(states) and all(state == "42501" for state in states),
        child_process_role=str(payload.get("process_role") or ""),
        child_sqlstates=states,
        child_error=str(payload.get("factory_error") or ""),
    )


def render_process_split_markdown(report: ProcessSplitReport) -> str:
    lines = [
        "# Planner-only process role",
        "",
        f"ok={report.ok()}",
        "",
        "| check | result |",
        "|---|---|",
        f"| parent gold closed (actuation) | {report.parent_gold_closed} |",
        f"| child writer factory refused | {report.child_factory_refused} |",
        f"| child planner SQL 42501 | {report.child_sql_42501} |",
        f"| parent gold closed after child | {report.parent_gold_after_closed} |",
        "",
    ]
    if report.child_error:
        lines.append(f"Child error: `{report.child_error}`")
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "ProcessSplitReport",
    "render_process_split_markdown",
    "run_process_split_probe",
]
