"""Add controlled CV import review batches and suggestions.

Revision ID: 20260723_0005
Revises: 20260723_0004
Create Date: 2026-07-23
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260723_0005"
down_revision = "20260723_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cv_import_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_filename", sa.String(500), nullable=False),
        sa.Column("content_hash", sa.String(64)),
        sa.Column("source_language", sa.String(5)),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending_review"),
        sa.Column("source_metadata", postgresql.JSONB()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "cv_import_suggestions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cv_import_batches.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("proposed_data", postgresql.JSONB(), nullable=False),
        sa.Column("source_excerpt", sa.Text()),
        sa.Column("confidence", sa.Float()),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("matched_entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("applied_entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("review_note", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "ix_cv_import_suggestions_profile_status",
        "cv_import_suggestions",
        ["profile_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cv_import_suggestions_profile_status",
        table_name="cv_import_suggestions",
    )
    op.drop_table("cv_import_suggestions")
    op.drop_table("cv_import_batches")
