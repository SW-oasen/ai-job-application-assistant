"""Add application status tracking and event history.

Revision ID: 20260727_0010
Revises: 20260726_0009
Create Date: 2026-07-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260727_0010"
down_revision = "20260726_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("applications", sa.Column("application_channel", sa.String(50)))
    op.add_column("applications", sa.Column("response_channel", sa.String(50)))
    op.add_column(
        "applications",
        sa.Column("status_changed_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "application_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
        ),
        sa.Column(
            "application_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30)),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("channel", sa.String(50)),
        sa.Column("note", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_application_events_application_id",
        "application_events",
        ["application_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_events_application_id",
        table_name="application_events",
    )
    op.drop_table("application_events")
    op.drop_column("applications", "status_changed_at")
    op.drop_column("applications", "response_channel")
    op.drop_column("applications", "application_channel")
