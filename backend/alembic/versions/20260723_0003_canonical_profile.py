"""Add editable canonical profile data with localized content and revisions.

Revision ID: 20260723_0003
Revises: 20260723_0002
Create Date: 2026-07-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260723_0003"
down_revision = "20260723_0002"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    ]


def _localized_table(name: str, parent_column: str, parent_table: str, constraint: str) -> None:
    op.create_table(
        name,
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            parent_column,
            UUID,
            sa.ForeignKey(f"{parent_table}.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("language", sa.String(5), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("bullets", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.UniqueConstraint(parent_column, "language", name=constraint),
    )


def upgrade() -> None:
    op.create_table(
        "profiles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("display_name", sa.String(300), nullable=False),
        sa.Column("default_language", sa.String(5), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    op.create_table(
        "skills",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "profile_id",
            UUID,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("canonical_name", sa.String(300), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("proficiency_level", sa.String(50)),
        sa.Column("years_experience", sa.Float()),
        sa.Column("last_used_at", sa.Date()),
        sa.Column("aliases", postgresql.JSONB(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("profile_id", "canonical_name", name="uq_profile_skill"),
    )
    _localized_table(
        "skill_localizations", "skill_id", "skills", "uq_skill_language"
    )
    op.create_table(
        "work_experiences",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "profile_id",
            UUID,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("company", sa.String(500), nullable=False),
        sa.Column("employment_type", sa.String(100)),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("location", sa.String(500)),
        sa.Column("remote_model", sa.String(50)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    _localized_table(
        "work_experience_localizations",
        "work_experience_id",
        "work_experiences",
        "uq_work_experience_language",
    )
    op.create_table(
        "education_entries",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "profile_id",
            UUID,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("institution", sa.String(500), nullable=False),
        sa.Column("start_date", sa.Date()),
        sa.Column("end_date", sa.Date()),
        sa.Column("location", sa.String(500)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    _localized_table(
        "education_localizations",
        "education_entry_id",
        "education_entries",
        "uq_education_language",
    )
    op.create_table(
        "certificates",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "profile_id",
            UUID,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("official_name", sa.String(500), nullable=False),
        sa.Column("issuer", sa.String(500), nullable=False),
        sa.Column("issued_at", sa.Date()),
        sa.Column("expires_at", sa.Date()),
        sa.Column("credential_id", sa.String(500)),
        sa.Column("verification_url", sa.String(2048)),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    _localized_table(
        "certificate_localizations",
        "certificate_id",
        "certificates",
        "uq_certificate_language",
    )
    op.create_table(
        "profile_references",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "profile_id",
            UUID,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("full_name", sa.String(500), nullable=False),
        sa.Column("organization", sa.String(500)),
        sa.Column("email", sa.String(500)),
        sa.Column("phone", sa.String(100)),
        sa.Column("preferred_language", sa.String(5)),
        sa.Column("usage_consent", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    _localized_table(
        "reference_localizations",
        "profile_reference_id",
        "profile_references",
        "uq_reference_language",
    )
    op.create_table(
        "profile_entity_revisions",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "profile_id",
            UUID,
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", UUID, nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(30), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("change_reason", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint(
            "entity_type",
            "entity_id",
            "revision",
            name="uq_profile_entity_revision",
        ),
    )


def downgrade() -> None:
    op.drop_table("profile_entity_revisions")
    op.drop_table("reference_localizations")
    op.drop_table("profile_references")
    op.drop_table("certificate_localizations")
    op.drop_table("certificates")
    op.drop_table("education_localizations")
    op.drop_table("education_entries")
    op.drop_table("work_experience_localizations")
    op.drop_table("work_experiences")
    op.drop_table("skill_localizations")
    op.drop_table("skills")
    op.drop_table("profiles")
