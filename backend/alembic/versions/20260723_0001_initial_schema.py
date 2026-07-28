"""Create the Application Assistant core schema.

Revision ID: 20260723_0001
Revises:
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260723_0001"
down_revision = None
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "companies",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(300), nullable=False, unique=True),
        sa.Column("website", sa.String(2048)),
        sa.Column("industry", sa.String(300)),
        sa.Column("description", sa.Text()),
        sa.Column("location", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("company_id", UUID, sa.ForeignKey("companies.id")),
        sa.Column("title", sa.String(500)),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("source_filename", sa.String(500)),
        sa.Column("source_portal", sa.String(300)),
        sa.Column("location", sa.String(500)),
        sa.Column("work_model", sa.String(50)),
        sa.Column("employment_type", sa.String(100)),
        sa.Column("language", sa.String(50)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("published_at", sa.Date()),
        sa.Column("deadline", sa.Date()),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("raw_content", sa.Text()),
        sa.Column("normalized_content", sa.Text(), nullable=False),
        sa.Column("extracted_json", postgresql.JSONB()),
        sa.Column("prompt_version", sa.String(100)),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("retrieval_method", sa.String(50), nullable=False),
        sa.Column("import_warnings", postgresql.JSONB(), nullable=False),
    )
    op.create_index("ix_jobs_source_url", "jobs", ["source_url"])
    op.create_index("ix_jobs_content_hash", "jobs", ["content_hash"])
    op.create_table(
        "job_requirements",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("job_id", UUID, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("requirement_text", sa.Text(), nullable=False),
        sa.Column("normalized_value", sa.String(500)),
        sa.Column("priority", sa.String(30), nullable=False),
        sa.Column("evidence", sa.Text()),
        sa.Column("confidence", sa.Float()),
    )
    op.create_table(
        "applications",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("job_id", UUID, sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("next_action", sa.Text()),
        sa.Column("next_action_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "generated_documents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "application_id",
            UUID,
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("language", sa.String(50)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("prompt_version", sa.String(100)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "application_id",
            "document_type",
            "version",
            name="uq_generated_document_version",
        ),
    )
    op.create_table(
        "requirement_matches",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "job_requirement_id",
            UUID,
            sa.ForeignKey("job_requirements.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("profile_source", sa.String(500), nullable=False),
        sa.Column("match_level", sa.String(30), nullable=False),
        sa.Column("evidence", postgresql.JSONB(), nullable=False),
        sa.Column("gap", sa.Text()),
        sa.Column("confidence", sa.Float()),
    )


def downgrade() -> None:
    op.drop_table("requirement_matches")
    op.drop_table("generated_documents")
    op.drop_table("applications")
    op.drop_table("job_requirements")
    op.drop_index("ix_jobs_content_hash", table_name="jobs")
    op.drop_index("ix_jobs_source_url", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("companies")
