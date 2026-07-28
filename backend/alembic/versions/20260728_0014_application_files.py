"""Add centrally stored application PDF metadata.

Revision ID: 20260728_0014
Revises: 20260727_0013
Create Date: 2026-07-28
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "20260728_0014"
down_revision = "20260727_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_application_files_application_id",
        "application_files",
        ["application_id"],
    )
    op.create_index("ix_application_files_sha256", "application_files", ["sha256"])


def downgrade() -> None:
    op.drop_index("ix_application_files_sha256", table_name="application_files")
    op.drop_index("ix_application_files_application_id", table_name="application_files")
    op.drop_table("application_files")
