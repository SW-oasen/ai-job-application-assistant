"""Store extracted job activities separately from requirements.

Revision ID: 20260731_0020
Revises: 20260730_0019
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260731_0020"
down_revision: str | None = "20260730_0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "job_activities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "job_id",
            UUID,
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("activity_text", sa.Text(), nullable=False),
        sa.Column(
            "category",
            sa.String(100),
            nullable=False,
            server_default="responsibility",
        ),
        sa.Column("evidence", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column(
            "keywords",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_job_activities_job_id",
        "job_activities",
        ["job_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_job_activities_job_id", table_name="job_activities")
    op.drop_table("job_activities")
