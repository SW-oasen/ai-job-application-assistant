"""Merge contract preferences into employment-type preferences."""

from collections.abc import Sequence
import json

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0029"
down_revision: str | None = "20260822_0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, preferred_employment_types, contract_preferences FROM profiles")
    ).mappings()
    for row in rows:
        values = list(row["preferred_employment_types"] or [])
        for value in row["contract_preferences"] or []:
            if value not in values:
                values.append(value)
        connection.execute(
            sa.text("UPDATE profiles SET preferred_employment_types = :values WHERE id = :id"),
            {"values": json.dumps(values), "id": row["id"]},
        )
    op.drop_column("profiles", "contract_preferences")


def downgrade() -> None:
    op.add_column("profiles", sa.Column("contract_preferences", sa.JSON(), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, preferred_employment_types FROM profiles")
    ).mappings()
    for row in rows:
        values = [value for value in row["preferred_employment_types"] or [] if value in {"permanent", "temporary"}]
        connection.execute(
            sa.text("UPDATE profiles SET contract_preferences = :values WHERE id = :id"),
            {"values": json.dumps(values), "id": row["id"]},
        )
