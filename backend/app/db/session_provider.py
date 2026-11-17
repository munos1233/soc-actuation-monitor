"""Process-local database session ownership (ISSUE-118).

Each OS process (FastAPI worker, Celery child) owns exactly one ``SessionProvider``.
API processes use a pooled engine; Celery worker children use ``NullPool`` so
``asyncio.run`` per task never reuses connections bound to a prior event loop.

Tests inject an alternate provider via ``set_session_provider`` without touching
hidden module caches.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator
from typing import Literal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import ProcessRole, get_settings


class ActuationLoginForbidden(RuntimeError):
    """Raised when PROCESS_ROLE=planner asks for the writer factory."""

logger = logging.getLogger(__name__)

PoolPolicy = Literal["pooled", "nullpool"]

_provider: SessionProvider | None = None


class SessionProvider:
    """Owns the owner engine plus optional planner / actuation factories."""

    __slots__ = (
        "_actuation_factory",
        "_actuation_url",
        "_database_url",
        "_engine",
        "_factory",
        "_forbid_actuation",
        "_planner_factory",
        "_planner_url",
        "_pool",
        "_process_role",
        "_side_engines",
    )

    def __init__(
        self,
        database_url: str,
        *,
        pool: PoolPolicy = "pooled",
        planner_url: str | None = None,
        actuation_url: str | None = None,
        process_role: ProcessRole | str = ProcessRole.MONOLITH,
    ) -> None:
        role = ProcessRole(process_role)
        self._process_role = role
        self._forbid_actuation = role is ProcessRole.PLANNER
        self._database_url = database_url
        self._planner_url = planner_url
        self._actuation_url = None if self._forbid_actuation else actuation_url
        self._pool = pool
        self._engine: AsyncEngine | None = None
        self._factory: async_sessionmaker[AsyncSession] | None = None
        self._planner_factory: async_sessionmaker[AsyncSession] | None = None
        self._actuation_factory: async_sessionmaker[AsyncSession] | None = None
        self._side_engines: list[AsyncEngine] = []

    @property
    def database_url(self) -> str:
        return self._database_url

    @property
    def pool_policy(self) -> PoolPolicy:
        return self._pool

    @property
    def is_engine_initialized(self) -> bool:
        return self._engine is not None

    def engine(self) -> AsyncEngine:
        if self._engine is None:
            kwargs: dict[str, object] = {"pool_pre_ping": True}
            if self._pool == "nullpool":
                kwargs["poolclass"] = NullPool
            self._engine = create_async_engine(self._database_url, **kwargs)
            logger.debug(
                "SessionProvider engine created (pool=%s, url=%s)",
                self._pool,
                self._database_url.split("@")[-1],
            )
        return self._engine

    def session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._factory is None:
            self._factory = async_sessionmaker(
                bind=self.engine(),
                expire_on_commit=False,
                autoflush=False,
            )
        return self._factory

    def _side_factory(self, url: str | None) -> async_sessionmaker[AsyncSession]:
        if not url or url == self._database_url:
            return self.session_factory()
        kwargs: dict[str, object] = {"pool_pre_ping": True}
        if self._pool == "nullpool":
            kwargs["poolclass"] = NullPool
        engine = create_async_engine(url, **kwargs)
        self._side_engines.append(engine)
        return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)

    def planner_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._planner_factory is None:
            self._planner_factory = self._side_factory(self._planner_url)
        return self._planner_factory

    @property
    def process_role(self) -> ProcessRole:
        return self._process_role

    def actuation_session_factory(self) -> async_sessionmaker[AsyncSession]:
        if self._forbid_actuation:
            raise ActuationLoginForbidden(
                "PROCESS_ROLE=planner forbids constructing the actuation writer factory"
            )
        if self._actuation_factory is None:
            self._actuation_factory = self._side_factory(self._actuation_url)
        return self._actuation_factory

    async def ping_postgres(self) -> bool:
        """Return True when ``SELECT 1`` succeeds via the process-local engine."""
        try:
            async with self.engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception:  # noqa: BLE001 — health must never raise
            return False

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            logger.debug("SessionProvider engine disposed (pool=%s)", self._pool)
        for engine in self._side_engines:
            await engine.dispose()
        self._engine = None
        self._factory = None
        self._planner_factory = None
        self._actuation_factory = None
        self._side_engines = []


async def ping_postgres_url(
    database_url: str,
    *,
    pool: PoolPolicy = "nullpool",
) -> bool:
    """Run ``SELECT 1`` against *database_url* without touching the process provider."""
    engine: AsyncEngine | None = None
    try:
        kwargs: dict[str, object] = {"pool_pre_ping": True}
        if pool == "nullpool":
            kwargs["poolclass"] = NullPool
        engine = create_async_engine(database_url, **kwargs)
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 — health must never raise
        return False
    finally:
        if engine is not None:
            await engine.dispose()


def peek_session_provider() -> SessionProvider | None:
    """Return the current provider without creating one (tests/diagnostics)."""
    return _provider


def _dispose_provider_sync(provider: SessionProvider) -> None:
    """Best-effort synchronous dispose when no event loop is running."""
    if not provider.is_engine_initialized:
        return
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(provider.dispose())
    else:
        logger.warning(
            "SessionProvider engine not disposed synchronously because an event loop "
            "is running; await reset_session_provider_async() instead"
        )


def _provider_from_settings(*, pool: PoolPolicy) -> SessionProvider:
    settings = get_settings()
    return SessionProvider(
        settings.database_url,
        pool=pool,
        planner_url=settings.resolved_planner_database_url(),
        actuation_url=settings.resolved_actuation_database_url(),
        process_role=settings.process_role,
    )


def get_session_provider(*, pool: PoolPolicy = "pooled") -> SessionProvider:
    """Return the process-local provider, creating a pooled one on first use."""
    global _provider
    if _provider is None:
        _provider = _provider_from_settings(pool=pool)
    elif _provider.pool_policy != pool:
        logger.warning(
            "get_session_provider(pool=%r) ignored: provider already initialized "
            "with pool=%r; use init_worker_session_provider() for Celery workers",
            pool,
            _provider.pool_policy,
        )
    return _provider


def init_worker_session_provider() -> SessionProvider:
    """Initialize a NullPool provider in a Celery worker child (post-fork)."""
    global _provider
    if _provider is not None:
        _dispose_provider_sync(_provider)
    _provider = _provider_from_settings(pool="nullpool")
    return _provider


def set_session_provider(provider: SessionProvider | None) -> None:
    """Replace the process-local provider, disposing the previous engine when set."""
    global _provider
    if _provider is not None and _provider is not provider:
        _dispose_provider_sync(_provider)
    _provider = provider


def reset_session_provider() -> None:
    """Dispose (when possible) and clear the process-local provider (sync tests)."""
    global _provider
    if _provider is None:
        return
    provider = _provider
    _provider = None
    _dispose_provider_sync(provider)


async def reset_session_provider_async() -> None:
    """Dispose and clear the process-local provider (async tests / teardown)."""
    global _provider
    if _provider is None:
        return
    provider = _provider
    _provider = None
    await provider.dispose()


async def dispose_session_provider() -> None:
    """Dispose and clear the current process-local provider."""
    global _provider
    if _provider is not None:
        await _provider.dispose()
    _provider = None


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding an async session with rollback on error."""
    factory = get_session_provider().session_factory()
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
