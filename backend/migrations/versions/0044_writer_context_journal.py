"""Grant writer the context journal used by the close/verify transaction.

Revision ID: 0044_writer_context_journal
Revises: 0043_outbox_plan_revision
Create Date: 2026-09-10 00:00:00.000000+00:00

Actuation writer is not ALL TABLES. Receipt persistence still appends the
event context journal and bumps field versions in the same transaction as
the outbox update. Those two tables are part of the write path, not a
planner privilege.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0044_writer_context_journal"
down_revision = "0043_outbox_plan_revision"
branch_labels = None
depends_on = None

ACTUATION_ROLE = "actuation_writer"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"GRANT INSERT, UPDATE ON TABLE event_context_field_version TO {ACTUATION_ROLE}"
        )
    )
    op.execute(
        sa.text(f"GRANT INSERT ON TABLE event_context_journal TO {ACTUATION_ROLE}")
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"REVOKE INSERT, UPDATE ON TABLE event_context_field_version FROM {ACTUATION_ROLE}"
        )
    )
    op.execute(
        sa.text(f"REVOKE INSERT ON TABLE event_context_journal FROM {ACTUATION_ROLE}")
    )
