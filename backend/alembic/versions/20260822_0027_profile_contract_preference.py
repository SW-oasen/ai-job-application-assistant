"""Add structured contract preferences to profiles."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0027"
down_revision: str | None = "20260807_0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("contract_preference", sa.String(20), nullable=True))
    op.add_column(
        "profiles", sa.Column("minimum_contract_duration_months", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("profiles", "minimum_contract_duration_months")
    op.drop_column("profiles", "contract_preference")
