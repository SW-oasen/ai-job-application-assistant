"""Remove obsolete change reasons from profile revisions.

Revision ID: 20260827_0033
Revises: 20260827_0032
"""

from alembic import op
import sqlalchemy as sa


revision = "20260827_0033"
down_revision = "20260827_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("profile_entity_revisions", "change_reason")


def downgrade() -> None:
    op.add_column("profile_entity_revisions", sa.Column("change_reason", sa.Text(), nullable=True))
