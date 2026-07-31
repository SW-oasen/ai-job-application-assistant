"""Add contact people to application events.

Revision ID: 20260730_0019
Revises: 20260730_0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260730_0019"
down_revision: str | None = "20260730_0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "application_events",
        sa.Column("contact_person", sa.String(length=300), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("application_events", "contact_person")
