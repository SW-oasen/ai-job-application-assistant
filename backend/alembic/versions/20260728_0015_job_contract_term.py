"""Add structured job contract term metadata.

Revision ID: 20260728_0015
Revises: 20260728_0014
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260728_0015"
down_revision: str | None = "20260728_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("contract_term", sa.String(200)))


def downgrade() -> None:
    op.drop_column("jobs", "contract_term")
