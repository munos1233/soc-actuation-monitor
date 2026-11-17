"""PROCESS_ROLE=planner must not construct the writer factory.

Monolith owner-fallback is unchanged. Live spawn is the paper probe, not this
file; these tests stay in-process so CI does not require the eval database.
"""

from __future__ import annotations

import pytest

from app.core.config import ProcessRole, Settings, get_settings
from app.db.session_provider import (
    ActuationLoginForbidden,
    SessionProvider,
    get_session_provider,
    reset_session_provider,
)
from app.eval_suite.planner_peer import PlannerPeer

OWNER = "postgresql+asyncpg://owner:owner@localhost:5432/app"
WRITER = "postgresql+asyncpg://writer:writer@localhost:5432/app"
PLANNER = "postgresql+asyncpg://planner:planner@localhost:5432/app"


def test_planner_peer_refuses_writer_factory() -> None:
    peer = PlannerPeer.start(OWNER)
    try:
        probe = peer.call({"op": "factory_probe"})
        assert probe["factory_refused"] is True
        assert probe["process_role"] == "planner"
    finally:
        peer.stop()


def test_planner_role_forbids_writer_factory_even_when_url_is_passed() -> None:
    provider = SessionProvider(
        OWNER,
        planner_url=PLANNER,
        actuation_url=WRITER,
        process_role=ProcessRole.PLANNER,
    )
    assert provider.process_role is ProcessRole.PLANNER
    with pytest.raises(ActuationLoginForbidden, match="planner"):
        provider.actuation_session_factory()


def test_monolith_still_falls_back_to_owner_when_actuation_url_missing() -> None:
    provider = SessionProvider(OWNER, process_role=ProcessRole.MONOLITH)
    assert provider.actuation_session_factory() is provider.session_factory()


def test_actuation_role_may_build_writer_factory() -> None:
    provider = SessionProvider(
        OWNER,
        actuation_url=WRITER,
        process_role=ProcessRole.ACTUATION,
    )
    factory = provider.actuation_session_factory()
    assert factory is not provider.session_factory()


def test_settings_default_process_role_is_monolith_for_local_debug() -> None:
    settings = Settings(APP_ENV="development")
    assert settings.process_role is ProcessRole.MONOLITH


def test_production_settings_default_process_role_is_planner() -> None:
    from tests.test_support.production_settings import production_settings_kwargs

    settings = Settings(**production_settings_kwargs())
    assert settings.process_role is ProcessRole.PLANNER


def test_planner_deps_return_remote_and_never_build_writer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import asyncio

    monkeypatch.setenv("PROCESS_ROLE", "planner")
    get_settings.cache_clear()
    reset_session_provider()
    from app.api.v1 import deps
    from app.services.actuation_remote import RemoteDispositionSync, RemoteStateMachine

    deps.reset_deps()
    try:
        machine = asyncio.run(deps.get_state_machine())
        sync = asyncio.run(deps.get_disposition_sync())
        assert isinstance(machine, RemoteStateMachine)
        assert isinstance(sync, RemoteDispositionSync)
        with pytest.raises(ActuationLoginForbidden):
            get_session_provider().actuation_session_factory()
    finally:
        deps.reset_deps()
        reset_session_provider()
        get_settings.cache_clear()


def test_get_session_provider_honors_planner_role(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PROCESS_ROLE", "planner")
    get_settings.cache_clear()
    reset_session_provider()
    try:
        provider = get_session_provider()
        assert provider.process_role is ProcessRole.PLANNER
        with pytest.raises(ActuationLoginForbidden):
            provider.actuation_session_factory()
    finally:
        reset_session_provider()
        get_settings.cache_clear()
