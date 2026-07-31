"""Add structured career goals to profiles.

Revision ID: 20260730_0017
Revises: 20260728_0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260730_0017"
down_revision: str | None = "20260728_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("career_goal", sa.Text()))
    for column_name in (
        "target_roles",
        "target_industries",
        "target_locations",
        "preferred_work_models",
        "preferred_employment_types",
        "deal_breakers",
    ):
        op.add_column(
            "profiles",
            sa.Column(
                column_name,
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )


def downgrade() -> None:
    for column_name in (
        "deal_breakers",
        "preferred_employment_types",
        "preferred_work_models",
        "target_locations",
        "target_industries",
        "target_roles",
    ):
        op.drop_column("profiles", column_name)
    op.drop_column("profiles", "career_goal")
