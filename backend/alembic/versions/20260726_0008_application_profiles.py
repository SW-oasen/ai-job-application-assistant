"""Bind applications to canonical profiles.

Revision ID: 20260726_0008
Revises: 20260726_0007
Create Date: 2026-07-26
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260726_0008"
down_revision = "20260726_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "applications",
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_applications_profile_id",
        "applications",
        "profiles",
        ["profile_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_unique_constraint(
        "uq_application_job_profile",
        "applications",
        ["job_id", "profile_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_application_job_profile", "applications", type_="unique")
    op.drop_constraint("fk_applications_profile_id", "applications", type_="foreignkey")
    op.drop_column("applications", "profile_id")
