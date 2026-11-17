"""Database roles that separate proposal writes from actuation writes.

The owner URL (``DATABASE_URL``) is for migrations. Runtime close and outbox
enqueue use ``actuation_writer``. A planner that only holds
``actuation_planner`` credentials cannot write ``security_event.status`` or
insert ``disposition_outbox`` rows — PostgreSQL refuses those statements, which
is what the A0 cases measure.

Role names are product-neutral so an anonymized artifact does not leak.
"""

from __future__ import annotations

from sqlalchemy.engine.url import make_url

PLANNER_ROLE = "actuation_planner"
ACTUATION_ROLE = "actuation_writer"
DEFAULT_PLANNER_PASSWORD = "planner_role"
DEFAULT_ACTUATION_PASSWORD = "actuation_role"


def rewrite_database_url(base_url: str, *, username: str, password: str) -> str:
    """Return *base_url* with the login replaced. Driver and host are unchanged."""
    url = make_url(base_url)
    return url.set(username=username, password=password).render_as_string(hide_password=False)


def derived_planner_url(
    owner_url: str,
    *,
    explicit: str = "",
    password: str = DEFAULT_PLANNER_PASSWORD,
) -> str:
    if explicit.strip():
        return explicit.strip()
    return rewrite_database_url(owner_url, username=PLANNER_ROLE, password=password)


def derived_actuation_url(
    owner_url: str,
    *,
    explicit: str = "",
    password: str = DEFAULT_ACTUATION_PASSWORD,
) -> str:
    if explicit.strip():
        return explicit.strip()
    return rewrite_database_url(owner_url, username=ACTUATION_ROLE, password=password)
