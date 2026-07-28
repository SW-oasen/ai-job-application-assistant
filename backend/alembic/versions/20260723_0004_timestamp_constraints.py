"""Align timestamp nullability with the ORM models.

Revision ID: 20260723_0004
Revises: 20260723_0003
Create Date: 2026-07-23
"""

from alembic import op

revision = "20260723_0004"
down_revision = "20260723_0003"
branch_labels = None
depends_on = None

TIMESTAMP_COLUMNS = {
    "applications": ("created_at", "updated_at"),
    "certificates": ("created_at", "updated_at"),
    "companies": ("created_at", "updated_at"),
    "education_entries": ("created_at", "updated_at"),
    "generated_documents": ("created_at",),
    "jobs": ("imported_at",),
    "profile_entity_revisions": ("created_at",),
    "profile_evidence": ("created_at",),
    "profile_references": ("created_at", "updated_at"),
    "profile_sources": ("created_at", "updated_at"),
    "profiles": ("created_at", "updated_at"),
    "skills": ("created_at", "updated_at"),
    "work_experiences": ("created_at", "updated_at"),
}


def upgrade() -> None:
    for table_name, columns in TIMESTAMP_COLUMNS.items():
        for column_name in columns:
            op.alter_column(table_name, column_name, nullable=False)


def downgrade() -> None:
    for table_name, columns in TIMESTAMP_COLUMNS.items():
        for column_name in columns:
            op.alter_column(table_name, column_name, nullable=True)
