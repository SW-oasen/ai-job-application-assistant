"""Add job portal names to applications and timeline events.

Revision ID: 20260728_0016
Revises: 20260728_0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0016"
down_revision: str | None = "20260728_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("application_portal_name", sa.String(100)),
    )
    op.add_column(
        "applications",
        sa.Column("response_portal_name", sa.String(100)),
    )
    op.add_column(
        "application_events",
        sa.Column("portal_name", sa.String(100)),
    )


def downgrade() -> None:
    op.drop_column("application_events", "portal_name")
    op.drop_column("applications", "response_portal_name")
    op.drop_column("applications", "application_portal_name")
