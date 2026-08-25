"""Add reviewable CV recommendations and document provenance."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260825_0031"
down_revision: str | None = "20260823_0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cv_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("master_profile_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("master_profiles.id"), nullable=False),
        sa.Column("master_profile_version", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(5), nullable=False),
        sa.Column("recommendation", postgresql.JSONB(), nullable=False),
        sa.Column("validation_warnings", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("workflow_run_id", sa.String(200)),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_cv_recommendations_application", "cv_recommendations", ["application_id"])
    op.add_column("generated_documents", sa.Column("source_master_profile_id", postgresql.UUID(as_uuid=True)))
    op.add_column("generated_documents", sa.Column("source_master_profile_version", sa.Integer()))
    op.add_column("generated_documents", sa.Column("source_recommendation_id", postgresql.UUID(as_uuid=True)))
    op.add_column("generated_documents", sa.Column("generation_metadata", postgresql.JSONB()))
    op.add_column("generated_documents", sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("generated_documents", "is_current")
    op.drop_column("generated_documents", "generation_metadata")
    op.drop_column("generated_documents", "source_recommendation_id")
    op.drop_column("generated_documents", "source_master_profile_version")
    op.drop_column("generated_documents", "source_master_profile_id")
    op.drop_index("ix_cv_recommendations_application", table_name="cv_recommendations")
    op.drop_table("cv_recommendations")
