"""Add generic review runs and issues.

Revision ID: 20260801_0023
Revises: 20260731_0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260801_0023"
down_revision: str | None = "20260731_0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "review_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("subject_type", sa.String(50), nullable=False),
        sa.Column("subject_id", UUID, nullable=False),
        sa.Column("review_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("decision", sa.String(30)),
        sa.Column("overall_confidence", sa.Float()),
        sa.Column("source_result", postgresql.JSONB()),
        sa.Column("corrected_result", postgresql.JSONB()),
        sa.Column("final_result", postgresql.JSONB()),
        sa.Column(
            "field_confidence",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "retry_instructions",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("context", postgresql.JSONB()),
        sa.Column("reviewer_model", sa.String(500)),
        sa.Column("workflow_version", sa.String(100)),
        sa.Column("prompt_version", sa.String(100)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("technical_error", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_review_runs_subject", "review_runs", ["subject_type", "subject_id"])
    op.create_index("ix_review_runs_type_status", "review_runs", ["review_type", "status"])
    op.create_table(
        "review_issues",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "review_run_id",
            UUID,
            sa.ForeignKey("review_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field", sa.String(500), nullable=False),
        sa.Column("issue_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("evidence", sa.Text()),
        sa.Column("suggested_value", postgresql.JSONB()),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index("ix_review_issues_review_run_id", "review_issues", ["review_run_id"])


def downgrade() -> None:
    op.drop_index("ix_review_issues_review_run_id", table_name="review_issues")
    op.drop_table("review_issues")
    op.drop_index("ix_review_runs_type_status", table_name="review_runs")
    op.drop_index("ix_review_runs_subject", table_name="review_runs")
    op.drop_table("review_runs")