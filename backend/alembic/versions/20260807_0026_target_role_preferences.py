"""Add structured target role preferences and migrate legacy roles."""

from collections.abc import Sequence
import json
import sqlalchemy as sa
from alembic import op

revision: str = "20260807_0026"
down_revision: str | None = "20260805_0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _level(role: str) -> str | None:
    value = role.casefold()
    for token, level in (("principal", "Principal"), ("staff", "Staff"), ("lead", "Lead"),
                         ("leiter", "Lead"), ("head", "Lead"), ("senior", "Senior"),
                         ("junior", "Junior"), ("manager", "Manager")):
        if token in value:
            return level
    return None


def upgrade() -> None:
    op.add_column("profiles", sa.Column("target_role_preferences", sa.JSON(), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, target_roles FROM profiles")).mappings()
    for row in rows:
        roles = row["target_roles"] or []
        preferences = [{"role": role, "level": _level(role), "priority": index + 1}
                       for index, role in enumerate(roles)]
        connection.execute(
            sa.text("UPDATE profiles SET target_role_preferences = :preferences WHERE id = :id"),
            {"preferences": json.dumps(preferences), "id": row["id"]},
        )


def downgrade() -> None:
    op.drop_column("profiles", "target_role_preferences")
