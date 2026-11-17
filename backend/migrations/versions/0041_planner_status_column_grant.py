"""Fix planner UPDATE: table-level grant still wrote status.

Revision ID: 0041_planner_status_column_grant
Revises: 0040_actuation_roles
Create Date: 2026-09-10 00:00:00.000000+00:00

PostgreSQL table-level UPDATE allows every column. 0040's
``REVOKE UPDATE (status)`` therefore did not stop a planner login from writing
CLOSED. This revision revokes table-level UPDATE and grants every column
except ``status``.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0041_planner_status_column_grant"
down_revision = "0040_actuation_roles"
branch_labels = None
depends_on = None

PLANNER_ROLE = "actuation_planner"


def upgrade() -> None:
    op.execute(sa.text(f"REVOKE UPDATE ON TABLE security_event FROM {PLANNER_ROLE}"))
    op.execute(sa.text(f"REVOKE UPDATE (status) ON TABLE security_event FROM {PLANNER_ROLE}"))
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


def downgrade() -> None:
    op.execute(sa.text(f"GRANT UPDATE ON TABLE security_event TO {PLANNER_ROLE}"))
