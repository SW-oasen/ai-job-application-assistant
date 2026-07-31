"""Add reversible job archiving.

Revision ID: 20260731_0021
Revises: 20260731_0020
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0021"
down_revision: str | None = "20260731_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("archived_at", sa.DateTime(timezone=True)))
    op.add_column("jobs", sa.Column("archive_reason", sa.String(500)))
    op.create_index("ix_jobs_archived_at", "jobs", ["archived_at"])


def downgrade() -> None:
    op.drop_index("ix_jobs_archived_at", table_name="jobs")
    op.drop_column("jobs", "archive_reason")
    op.drop_column("jobs", "archived_at")
