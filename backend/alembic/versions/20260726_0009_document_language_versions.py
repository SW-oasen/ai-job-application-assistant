"""Version generated documents independently per language.

Revision ID: 20260726_0009
Revises: 20260726_0008
Create Date: 2026-07-26
"""

from alembic import op

revision = "20260726_0009"
down_revision = "20260726_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_generated_document_version",
        "generated_documents",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_generated_document_version",
        "generated_documents",
        ["application_id", "document_type", "language", "version"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_generated_document_version",
        "generated_documents",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_generated_document_version",
        "generated_documents",
        ["application_id", "document_type", "version"],
    )
