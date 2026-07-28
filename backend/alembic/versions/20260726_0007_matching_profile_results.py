"""Assign matching results to profiles.

Revision ID: 20260726_0007
Revises: 20260724_0006
Create Date: 2026-07-26
"""

import sqlalchemy as sa

from alembic import op

revision = "20260726_0007"
down_revision = "20260724_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "requirement_matches",
        sa.Column(
            "profile_id",
            sa.UUID(),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "requirement_matches",
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_requirement_matches_profile_id",
        "requirement_matches",
        ["profile_id"],
    )
    op.execute(
        """
        UPDATE requirement_matches
        SET profile_id = (SELECT id FROM profiles LIMIT 1)
        WHERE profile_id IS NULL
          AND (SELECT count(*) FROM profiles) = 1
        """
    )


def downgrade() -> None:
    op.drop_index(
        "ix_requirement_matches_profile_id",
        table_name="requirement_matches",
    )
    op.drop_column("requirement_matches", "evaluated_at")
    op.drop_column("requirement_matches", "profile_id")
