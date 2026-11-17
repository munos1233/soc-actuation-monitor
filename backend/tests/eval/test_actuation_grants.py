"""Live PostgreSQL GRANT checks for the planner / writer split.

Skipped when the isolated eval database is not reachable. Harm is SQLSTATE
42501, not a Python ``if``.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.actuation_roles import derived_actuation_url, derived_planner_url
from app.eval_suite.world import ensure_migrated

pytestmark = pytest.mark.asyncio

OWNER = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://shadowtrace:shadowtrace@127.0.0.1:55432/shadowtrace",
)


async def _connectable(url: str) -> bool:
    engine = create_async_engine(url)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False
    finally:
        await engine.dispose()


async def _sqlstate(url: str, sql: str, params: dict[str, object] | None = None) -> str | None:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text(sql), params or {})
        return None
    except DBAPIError as exc:
        orig = getattr(exc, "orig", None)
        return getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    finally:
        await engine.dispose()


@pytest.fixture(scope="module")
def planner_url() -> str:
    return derived_planner_url(OWNER)


@pytest.fixture(scope="module")
def writer_url() -> str:
    return derived_actuation_url(OWNER)


async def test_planner_cannot_write_privileged_columns(planner_url: str) -> None:
    if not await _connectable(OWNER):
        pytest.skip("eval postgres not reachable")
    os.environ["DATABASE_URL"] = OWNER
    get_settings.cache_clear()
    import app.eval_suite.world as world_mod

    world_mod._migrated = False
    try:
        await asyncio.to_thread(ensure_migrated)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"could not apply migrations: {exc}")
    if not await _connectable(planner_url):
        pytest.skip("eval postgres / planner role not reachable")
    statements = (
        "UPDATE security_event SET status = 'closed' WHERE false",
        "UPDATE security_event SET disposition_source_ref = '{}'::jsonb WHERE false",
        "UPDATE action SET status = 'approved' WHERE false",
        "INSERT INTO approval_record (approval_id, action_id, event_id, plan_revision, "
        "approval_cycle, required_level, decision) VALUES "
        "('apr-eval-grant', 'missing', 'missing', 1, 0, 'L2', 'approved')",
        "DELETE FROM security_event WHERE false",
        "INSERT INTO disposition_outbox (outbox_id, writeback_id, disposition_id, "
        "action_id, event_id, closure_cycle, source_record_id, source_locator_hash, "
        "source_sequence, intent_kind, logical_slot, idempotency_key, command_payload, "
        "command_payload_sha256) VALUES "
        "('obx-eval-grant', 'wbk-x', 'disp-x', 'missing', 'missing', 1, 'missing', "
        "'h', 1, 'event_status_update', 'terminal', 'idem-eval-grant', '{}'::jsonb, "
        "'0')",
    )
    for sql in statements:
        state = await _sqlstate(planner_url, sql)
        assert state == "42501", (sql, state)


async def test_writer_is_not_all_tables(writer_url: str) -> None:
    if not await _connectable(OWNER):
        pytest.skip("eval postgres not reachable")
    os.environ["DATABASE_URL"] = OWNER
    get_settings.cache_clear()
    import app.eval_suite.world as world_mod

    world_mod._migrated = False
    try:
        await asyncio.to_thread(ensure_migrated)
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"could not apply migrations: {exc}")
    if not await _connectable(writer_url):
        pytest.skip("eval postgres / writer role not reachable")
    # Writer may update event status; it must not create tenants or users.
    allowed = await _sqlstate(
        writer_url, "UPDATE security_event SET status = status WHERE false"
    )
    assert allowed is None
    forbidden = await _sqlstate(
        writer_url,
        "INSERT INTO approval_record (approval_id, action_id, event_id, plan_revision, "
        "approval_cycle, required_level, decision) VALUES "
        "('apr-writer-grant', 'missing', 'missing', 1, 0, 'L2', 'approved')",
    )
    assert forbidden == "42501", forbidden
    job_lock = await _sqlstate(
        writer_url,
        "UPDATE action_execution_job SET status = status WHERE false",
    )
    assert job_lock is None, job_lock
