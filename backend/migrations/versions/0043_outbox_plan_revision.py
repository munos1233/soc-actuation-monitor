"""Persist plan_revision on disposition_outbox (ISSUE-092).

Revision ID: 0043_outbox_plan_revision
Revises: 0042_actuation_privilege_alignment
Create Date: 2026-09-10 00:00:00.000000+00:00

The closure gate rebuilds from current rows. A head that never stored the
plan revision it was bound to cannot be treated as evidence for that cycle.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0043_outbox_plan_revision"
down_revision = "0042_actuation_privilege_alignment"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "disposition_outbox",
        sa.Column("plan_revision", sa.Integer(), nullable=True),
    )
    op.execute(
        sa.text(
            "UPDATE disposition_outbox SET plan_revision = closure_cycle "
            "WHERE plan_revision IS NULL"
        )
    )


def downgrade() -> None:
    op.drop_column("disposition_outbox", "plan_revision")
