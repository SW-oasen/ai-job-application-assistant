"""Replace waiting response with followed up application status.

Revision ID: 20260727_0012
Revises: 20260727_0011
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op

revision = "20260727_0012"
down_revision = "20260727_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE applications SET status = 'followed_up' "
            "WHERE status = 'waiting_response'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE application_events SET status = 'followed_up' "
            "WHERE status = 'waiting_response'"
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "UPDATE applications SET status = 'waiting_response' "
            "WHERE status = 'followed_up'"
        )
    )
    connection.execute(
        sa.text(
            "UPDATE application_events SET status = 'waiting_response' "
            "WHERE status = 'followed_up'"
        )
    )
