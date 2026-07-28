"""Repair structured metadata inferred from native PDF text.

Revision ID: 20260727_0013
Revises: 20260727_0012
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op

from app.parsers.job_metadata import extract_job_metadata

revision = "20260727_0013"
down_revision = "20260727_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            "SELECT id, title, normalized_content "
            "FROM jobs WHERE source_type = 'pdf'"
        )
    ).mappings()
    for row in rows:
        metadata = extract_job_metadata(row["normalized_content"] or "")
        connection.execute(
            sa.text(
                "UPDATE jobs SET "
                "title = COALESCE(title, :title), "
                "location = COALESCE(:location, location), "
                "work_model = COALESCE(:work_model, work_model), "
                "employment_type = COALESCE(:employment_type, employment_type) "
                "WHERE id = :id"
            ),
            {
                "id": row["id"],
                "title": metadata["title"],
                "location": metadata["location"],
                "work_model": metadata["work_model"],
                "employment_type": metadata["employment_type"],
            },
        )


def downgrade() -> None:
    # Repaired values cannot be distinguished safely from original metadata.
    pass
