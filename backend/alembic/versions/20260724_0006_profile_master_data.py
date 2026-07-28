"""Add editable profile master data.

Revision ID: 20260724_0006
Revises: 20260723_0005
Create Date: 2026-07-24
"""

import sqlalchemy as sa

from alembic import op

revision = "20260724_0006"
down_revision = "20260723_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("full_name", sa.String(500)))
    op.add_column("profiles", sa.Column("nationality", sa.String(200)))
    op.add_column("profiles", sa.Column("phone", sa.String(100)))
    op.add_column("profiles", sa.Column("email", sa.String(500)))
    op.add_column("profiles", sa.Column("linkedin_url", sa.String(2048)))
    op.add_column("profiles", sa.Column("github_url", sa.String(2048)))
    op.add_column("profiles", sa.Column("portfolio_url", sa.String(2048)))


def downgrade() -> None:
    op.drop_column("profiles", "portfolio_url")
    op.drop_column("profiles", "github_url")
    op.drop_column("profiles", "linkedin_url")
    op.drop_column("profiles", "email")
    op.drop_column("profiles", "phone")
    op.drop_column("profiles", "nationality")
    op.drop_column("profiles", "full_name")
