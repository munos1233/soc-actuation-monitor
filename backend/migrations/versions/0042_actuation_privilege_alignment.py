"""Align planner / writer GRANTs with the threat-model figure.

Revision ID: 0042_actuation_privilege_alignment
Revises: 0041_planner_status_column_grant
Create Date: 2026-09-10 00:00:00.000000+00:00

Planner login may write plan content. It cannot:

* update ``security_event.status`` or ``disposition_source_ref``
* update ``action.status``
* insert / update / delete ``approval_record``
* insert / update / delete ``disposition_outbox``
* delete ``security_event`` or ``action``

Actuation writer is no longer ALL TABLES. It may select broadly (close
rebuilds context from current rows) and write only the privileged path:
event status, outbox, source sequence, receipts, action writeback columns,
and the audit row written in the same close transaction.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0042_actuation_privilege_alignment"
down_revision = "0041_planner_status_column_grant"
branch_labels = None
depends_on = None

PLANNER_ROLE = "actuation_planner"
ACTUATION_ROLE = "actuation_writer"


def _grant_update_except(table: str, role: str, excluded: tuple[str, ...]) -> None:
    excluded_sql = ", ".join(f"'{name}'" for name in excluded)
    op.execute(sa.text(f"REVOKE UPDATE ON TABLE {table} FROM {role}"))
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
                 AND table_name = '{table}'
                 AND column_name NOT IN ({excluded_sql});
              IF cols IS NOT NULL THEN
                EXECUTE format(
                  'GRANT UPDATE (%s) ON TABLE {table} TO {role}',
                  cols
                );
              END IF;
            END
            $$;
            """
        )
    )


def upgrade() -> None:
    # Planner: threat-model shaded columns.
    _grant_update_except(
        "security_event",
        PLANNER_ROLE,
        ("status", "disposition_source_ref"),
    )
    _grant_update_except("action", PLANNER_ROLE, ("status",))
    op.execute(sa.text(f"REVOKE DELETE ON TABLE security_event FROM {PLANNER_ROLE}"))
    op.execute(sa.text(f"REVOKE DELETE ON TABLE action FROM {PLANNER_ROLE}"))
    op.execute(
        sa.text(
            f"REVOKE INSERT, UPDATE, DELETE ON TABLE approval_record FROM {PLANNER_ROLE}"
        )
    )
    op.execute(sa.text(f"GRANT SELECT ON TABLE approval_record TO {PLANNER_ROLE}"))
    op.execute(
        sa.text(
            f"REVOKE INSERT, UPDATE, DELETE ON TABLE disposition_outbox FROM {PLANNER_ROLE}"
        )
    )
    op.execute(sa.text(f"GRANT SELECT ON TABLE disposition_outbox TO {PLANNER_ROLE}"))

    # Writer: drop the all-tables write grant, then re-grant the write path.
    op.execute(
        sa.text(f"REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM {ACTUATION_ROLE}")
    )
    op.execute(sa.text(f"GRANT SELECT ON ALL TABLES IN SCHEMA public TO {ACTUATION_ROLE}"))
    op.execute(sa.text(f"GRANT UPDATE ON TABLE security_event TO {ACTUATION_ROLE}"))
    op.execute(
        sa.text(
            f"GRANT INSERT, UPDATE, DELETE ON TABLE disposition_outbox TO {ACTUATION_ROLE}"
        )
    )
    op.execute(sa.text(f"GRANT UPDATE ON TABLE source_object TO {ACTUATION_ROLE}"))
    op.execute(sa.text(f"GRANT UPDATE ON TABLE action TO {ACTUATION_ROLE}"))
    op.execute(
        sa.text(f"GRANT INSERT, UPDATE ON TABLE disposition_receipt TO {ACTUATION_ROLE}")
    )
    op.execute(sa.text(f"GRANT INSERT ON TABLE event_audit_log TO {ACTUATION_ROLE}"))
    op.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"REVOKE INSERT, UPDATE, DELETE ON TABLES FROM {ACTUATION_ROLE}"
        )
    )
    op.execute(
        sa.text(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            f"GRANT SELECT ON TABLES TO {ACTUATION_ROLE}"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public "
            f"TO {PLANNER_ROLE}, {ACTUATION_ROLE}"
        )
    )
    op.execute(sa.text(f"REVOKE UPDATE ON TABLE security_event FROM {PLANNER_ROLE}"))
    _grant_update_except("security_event", PLANNER_ROLE, ("status",))
    op.execute(
        sa.text(f"REVOKE INSERT, UPDATE, DELETE ON TABLE disposition_outbox FROM {PLANNER_ROLE}")
    )
    op.execute(sa.text(f"GRANT SELECT ON TABLE disposition_outbox TO {PLANNER_ROLE}"))
