"""Unit tests for the planner / actuation database login split."""

from __future__ import annotations

from app.db.actuation_roles import (
    ACTUATION_ROLE,
    DEFAULT_ACTUATION_PASSWORD,
    DEFAULT_PLANNER_PASSWORD,
    PLANNER_ROLE,
    derived_actuation_url,
    derived_planner_url,
    rewrite_database_url,
)


OWNER = "postgresql+asyncpg://shadowtrace:shadowtrace@localhost:55432/shadowtrace"


def test_rewrite_keeps_driver_host_and_database() -> None:
    rewritten = rewrite_database_url(OWNER, username="other", password="secret")
    assert rewritten == "postgresql+asyncpg://other:secret@localhost:55432/shadowtrace"


def test_derived_planner_login_is_not_the_owner() -> None:
    url = derived_planner_url(OWNER)
    assert PLANNER_ROLE in url
    assert DEFAULT_PLANNER_PASSWORD in url
    assert "shadowtrace:shadowtrace" not in url


def test_derived_actuation_login_is_not_the_planner() -> None:
    planner = derived_planner_url(OWNER)
    actuation = derived_actuation_url(OWNER)
    assert ACTUATION_ROLE in actuation
    assert DEFAULT_ACTUATION_PASSWORD in actuation
    assert planner != actuation


def test_explicit_url_wins_over_derived_password() -> None:
    explicit = "postgresql+asyncpg://actuation_planner:custom@db:5432/app"
    assert derived_planner_url(OWNER, explicit=explicit) == explicit
    assert derived_actuation_url(OWNER, explicit="  postgresql+asyncpg://w:p@h/db  ") == (
        "postgresql+asyncpg://w:p@h/db"
    )
