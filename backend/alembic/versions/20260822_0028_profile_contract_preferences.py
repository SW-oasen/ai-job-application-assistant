"""Allow multiple structured contract preferences."""

from collections.abc import Sequence
import json

import sqlalchemy as sa
from alembic import op

revision: str = "20260822_0028"
down_revision: str | None = "20260822_0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("contract_preferences", sa.JSON(), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, contract_preference FROM profiles")
    ).mappings()
    for row in rows:
        preference = row["contract_preference"]
        preferences = [preference] if preference in {"permanent", "temporary"} else []
        connection.execute(
            sa.text("UPDATE profiles SET contract_preferences = :preferences WHERE id = :id"),
            {"preferences": json.dumps(preferences), "id": row["id"]},
        )
    op.drop_column("profiles", "contract_preference")


def downgrade() -> None:
    op.add_column("profiles", sa.Column("contract_preference", sa.String(20), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, contract_preferences FROM profiles")
    ).mappings()
    for row in rows:
        preferences = row["contract_preferences"] or []
        preference = "temporary" if "temporary" in preferences else "permanent" if "permanent" in preferences else None
        connection.execute(
            sa.text("UPDATE profiles SET contract_preference = :preference WHERE id = :id"),
            {"preference": preference, "id": row["id"]},
        )
    op.drop_column("profiles", "contract_preferences")
