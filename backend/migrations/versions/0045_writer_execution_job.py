"""Grant writer the execution-job rows locked during outbox delivery.

Revision ID: 0045_writer_execution_job
Revises: 0044_writer_context_journal
Create Date: 2026-09-10 00:00:00.000000+00:00

``SELECT FOR UPDATE`` on ``action_execution_job`` requires UPDATE. Receipt
projection also inserts ``action_target_result`` in the same writer
transaction. Those tables are part of the actuation write path, not planner
content.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0045_writer_execution_job"
down_revision = "0044_writer_context_journal"
branch_labels = None
depends_on = None

ACTUATION_ROLE = "actuation_writer"


def upgrade() -> None:
    op.execute(
        sa.text(f"GRANT UPDATE ON TABLE action_execution_job TO {ACTUATION_ROLE}")
    )
    op.execute(
        sa.text(
            f"GRANT INSERT, UPDATE ON TABLE action_target_result TO {ACTUATION_ROLE}"
        )
    )
    op.execute(
        sa.text(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ACTUATION_ROLE}"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(f"REVOKE UPDATE ON TABLE action_execution_job FROM {ACTUATION_ROLE}")
    )
    op.execute(
        sa.text(
            f"REVOKE INSERT, UPDATE ON TABLE action_target_result FROM {ACTUATION_ROLE}"
        )
    )
