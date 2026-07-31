"""Add portfolio projects as canonical profile evidence.

Revision ID: 20260730_0018
Revises: 20260730_0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260730_0018"
down_revision: str | None = "20260730_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    op.create_table(
        "portfolio_projects",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "profile_id",
            UUID,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical_name", sa.String(500), nullable=False),
        sa.Column("project_type", sa.String(100)),
        sa.Column("role", sa.String(300)),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("source_url", sa.String(2048)),
        sa.Column("repository_url", sa.String(2048)),
        sa.Column(
            "technologies",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "profile_id",
            "canonical_name",
            name="uq_profile_portfolio_project",
        ),
    )
    op.create_table(
        "portfolio_project_localizations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "portfolio_project_id",
            UUID,
            sa.ForeignKey("portfolio_projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language", sa.String(5), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column(
            "bullets",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.String(30), nullable=False),
        sa.UniqueConstraint(
            "portfolio_project_id",
            "language",
            name="uq_portfolio_project_language",
        ),
    )


def downgrade() -> None:
    op.drop_table("portfolio_project_localizations")
    op.drop_table("portfolio_projects")
