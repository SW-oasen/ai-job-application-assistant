"""Add profile evidence and explainable matching fields.

Revision ID: 20260723_0002
Revises: 20260723_0001
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260723_0002"
down_revision = "20260723_0001"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.add_column(
        "job_requirements",
        sa.Column("keywords", postgresql.JSONB(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "requirement_matches",
        sa.Column("explanation", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "requirement_matches",
        sa.Column("recommended_action", sa.Text()),
    )
    op.create_table(
        "profile_sources",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("source_metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "profile_evidence",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "profile_source_id",
            UUID,
            sa.ForeignKey("profile_sources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.String(500), nullable=False),
        sa.Column("evidence_text", sa.Text(), nullable=False),
        sa.Column("experience_context", sa.String(30), nullable=False),
        sa.Column("keywords", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("profile_evidence")
    op.drop_table("profile_sources")
    op.drop_column("requirement_matches", "recommended_action")
    op.drop_column("requirement_matches", "explanation")
    op.drop_column("job_requirements", "keywords")
