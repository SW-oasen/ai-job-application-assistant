"""Add LinkedIn URL to profile references.

Revision ID: 20260731_0022
Revises: 20260731_0021
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260731_0022"
down_revision: str | None = "20260731_0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "profile_references",
        sa.Column("linkedin_url", sa.String(length=2048), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("profile_references", "linkedin_url")
