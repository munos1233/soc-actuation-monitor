"""Long-lived PROCESS_ROLE=planner child for Suite B planner writes and A0 SQL.

The parent (actuation) never issues planner DML in its own address space.
"""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import os
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

_peer: PlannerPeer | None = None


def _child_loop(cmd: mp.Queue[dict[str, Any]], res: mp.Queue[dict[str, Any]], owner_url: str) -> None:
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
    planner_url = derived_planner_url(owner_url)

    async def _handle(message: dict[str, Any]) -> Any:
        op = message["op"]
        if op == "factory_probe":
            try:
                get_session_provider().actuation_session_factory()
            except ActuationLoginForbidden:
                return {"factory_refused": True, "process_role": "planner"}
            return {"factory_refused": False, "process_role": "planner"}
        engine = create_async_engine(planner_url, poolclass=NullPool)
        factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
        try:
            if op == "sql":
                return await _run_sql(engine, message["statements"])
            if op == "insert_action":
                return await _insert_action(factory, message["fields"])
            if op == "update_action":
                return await _update_action(factory, message["action_id"], message["fields"])
            raise ValueError(f"unknown planner peer op {op!r}")
        finally:
            await engine.dispose()

    while True:
        message = cmd.get()
        if message.get("op") == "stop":
            res.put({"ok": True, "result": None})
            return
        try:
            result = asyncio.run(_handle(message))
            res.put({"ok": True, "result": result})
        except Exception as exc:  # noqa: BLE001 — parent scores or re-raises
            res.put({"ok": False, "error": f"{type(exc).__name__}: {exc}"})


async def _run_sql(engine: Any, statements: list[dict[str, Any]]) -> dict[str, Any]:
    info: dict[str, Any] = {"sqlstate": None, "error": None, "committed": False}
    try:
        async with engine.begin() as conn:
            for item in statements:
                await conn.execute(text(item["sql"]), item.get("params") or {})
        info["committed"] = True
    except OperationalError:
        raise
    except DBAPIError as exc:
        orig = getattr(exc, "orig", None)
        info["sqlstate"] = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
        info["error"] = str(exc.orig if orig is not None else exc)[:300]
        info["committed"] = False
    return info


async def _insert_action(factory: Any, fields: dict[str, Any]) -> str:
    from app.db import models as orm

    async with factory() as session:
        async with session.begin():
            session.add(orm.Action(**fields))
    return str(fields["action_id"])


async def _update_action(factory: Any, action_id: str, fields: dict[str, Any]) -> dict[str, Any]:
    from app.db import models as orm

    async with factory() as session:
        async with session.begin():
            row = await session.get(orm.Action, action_id, with_for_update=True)
            if row is None:
                raise RuntimeError(f"action not found: {action_id}")
            for key, value in fields.items():
                setattr(row, key, value)
    return {"action_id": action_id, "fields": list(fields)}


class PlannerPeer:
    def __init__(
        self,
        process: mp.Process,
        cmd: mp.Queue[dict[str, Any]],
        res: mp.Queue[dict[str, Any]],
    ) -> None:
        self._process = process
        self._cmd = cmd
        self._res = res

    @classmethod
    def start(cls, owner_url: str) -> PlannerPeer:
        ctx = mp.get_context("spawn")
        cmd: mp.Queue[dict[str, Any]] = ctx.Queue()
        res: mp.Queue[dict[str, Any]] = ctx.Queue()
        proc = ctx.Process(target=_child_loop, args=(cmd, res, owner_url), daemon=True)
        proc.start()
        return cls(proc, cmd, res)

    def call(self, message: dict[str, Any], *, timeout: float = 60) -> Any:
        if not self._process.is_alive():
            raise RuntimeError("planner peer process is not alive")
        self._cmd.put(message)
        payload = self._res.get(timeout=timeout)
        if not payload.get("ok"):
            raise RuntimeError(str(payload.get("error") or "planner peer failed"))
        return payload.get("result")

    def stop(self) -> None:
        if not self._process.is_alive():
            return
        self._cmd.put({"op": "stop"})
        try:
            self._res.get(timeout=10)
        except Exception:  # noqa: BLE001
            self._process.kill()
        self._process.join(timeout=5)


def ensure_planner_peer(owner_url: str) -> PlannerPeer:
    global _peer
    if _peer is None or not _peer._process.is_alive():
        _peer = PlannerPeer.start(owner_url)
        probe = _peer.call({"op": "factory_probe"})
        if not probe.get("factory_refused"):
            raise RuntimeError("planner peer constructed the writer factory")
    return _peer


def shutdown_planner_peer() -> None:
    global _peer
    if _peer is not None:
        _peer.stop()
        _peer = None


__all__ = [
    "PlannerPeer",
    "ensure_planner_peer",
    "shutdown_planner_peer",
]
