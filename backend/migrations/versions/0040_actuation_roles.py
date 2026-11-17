"""Install planner / actuation database roles (unique write path).

Revision ID: 0040_actuation_roles
Revises: 0039_graph_resume_intent
Create Date: 2026-09-10 00:00:00.000000+00:00

The owner role that runs migrations keeps full rights. ``actuation_planner``
may write plan content. It cannot update ``security_event.status`` and cannot
insert into ``disposition_outbox``. ``actuation_writer`` is the only login that
can.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0040_actuation_roles"
down_revision = "0039_graph_resume_intent"
branch_labels = None
depends_on = None

PLANNER_ROLE = "actuation_planner"
ACTUATION_ROLE = "actuation_writer"
PLANNER_PASSWORD = "planner_role"
ACTUATION_PASSWORD = "actuation_role"


def upgrade() -> None:
    conn = op.get_bind()
    database = conn.execute(sa.text("SELECT current_database()")).scalar()
    op.execute(
        sa.text(
            f"""
            DO $$
            BEGIN
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{PLANNER_ROLE}') THEN
                CREATE ROLE {PLANNER_ROLE} LOGIN PASSWORD '{PLANNER_PASSWORD}';
              ELSE
                ALTER ROLE {PLANNER_ROLE} LOGIN PASSWORD '{PLANNER_PASSWORD}';
              END IF;
              IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ACTUATION_ROLE}') THEN
                CREATE ROLE {ACTUATION_ROLE} LOGIN PASSWORD '{ACTUATION_PASSWORD}';
              ELSE
                ALTER ROLE {ACTUATION_ROLE} LOGIN PASSWORD '{ACTUATION_PASSWORD}';
              END IF;
            END
            $$;
            """
        )
    )
    op.execute(sa.text(f'GRANT CONNECT ON DATABASE "{database}" TO {PLANNER_ROLE}, {ACTUATION_ROLE}'))
    op.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {PLANNER_ROLE}, {ACTUATION_ROLE}"))
    op.execute(
        sa.text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
            f"TO {PLANNER_ROLE}, {ACTUATION_ROLE}"
        )
    )
    op.execute(
        sa.text(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public "
            f"TO {PLANNER_ROLE}, {ACTUATION_ROLE}"
        )
    )
    op.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES "
            f"TO {PLANNER_ROLE}, {ACTUATION_ROLE}"
        )
    )
    # Table-level UPDATE still covers every column, so a column REVOKE is a
    # no-op. Revoke the table privilege and re-grant every column except status.
    op.execute(sa.text(f"REVOKE UPDATE ON TABLE security_event FROM {PLANNER_ROLE}"))
    op.execute(
        sa.text(
            f"""
            DO $$
            DECLARE
              cols text;
            BEGIN
              SELECT string_agg(quote_ident(column_name), ', ')
                INTO cols
                FROM information_schema.columns
               WHERE table_schema = 'public'
                 AND table_name = 'security_event'
                 AND column_name <> 'status';
              EXECUTE format(
                'GRANT UPDATE (%s) ON TABLE security_event TO {PLANNER_ROLE}',
                cols
              );
            END
            $$;
            """
        )
    )
    op.execute(sa.text(f"REVOKE INSERT, UPDATE, DELETE ON TABLE disposition_outbox FROM {PLANNER_ROLE}"))
    op.execute(sa.text(f"GRANT SELECT ON TABLE disposition_outbox TO {PLANNER_ROLE}"))


def downgrade() -> None:
    conn = op.get_bind()
    database = conn.execute(sa.text("SELECT current_database()")).scalar()
    op.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES "
            f"FROM {PLANNER_ROLE}, {ACTUATION_ROLE}"
        )
    )
    op.execute(
        sa.text(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {PLANNER_ROLE}, {ACTUATION_ROLE}")
    )
    op.execute(
        sa.text(
            f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {PLANNER_ROLE}, {ACTUATION_ROLE}"
        )
    )
    op.execute(sa.text(f"REVOKE USAGE ON SCHEMA public FROM {PLANNER_ROLE}, {ACTUATION_ROLE}"))
    op.execute(
        sa.text(f'REVOKE CONNECT ON DATABASE "{database}" FROM {PLANNER_ROLE}, {ACTUATION_ROLE}')
    )
    op.execute(sa.text(f"DROP ROLE IF EXISTS {PLANNER_ROLE}"))
    op.execute(sa.text(f"DROP ROLE IF EXISTS {ACTUATION_ROLE}"))
