"""Keep only the latest review run per subject and review type.

Revision ID: 20260805_0025
Revises: 20260805_0024
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260805_0025"
down_revision: str | None = "20260805_0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DELETE FROM review_runs
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY subject_type, subject_id, review_type
                           ORDER BY created_at DESC, attempt DESC, id DESC
                       ) AS row_number
                FROM review_runs
            ) duplicates
            WHERE row_number > 1
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS ux_review_runs_latest_per_subject_type
        ON review_runs (subject_type, subject_id, review_type)
        """
    )


def downgrade() -> None:
    op.drop_index("ux_review_runs_latest_per_subject_type", table_name="review_runs")
