"""Link skills to concrete professional, project, and training evidence."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260805_0024"
down_revision: str | None = "20260801_0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skill_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("skill_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("skills.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_resource_type", sa.String(30), nullable=False),
        sa.Column("source_resource_id", postgresql.UUID(as_uuid=True)),
        sa.Column("experience_context", sa.String(30), nullable=False),
        sa.Column("evidence_text", sa.Text()),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("skill_id", "source_resource_type", "source_resource_id", name="uq_skill_evidence_source"),
    )
    op.create_index("ix_skill_evidence_skill_id", "skill_evidence", ["skill_id"])


def downgrade() -> None:
    op.drop_index("ix_skill_evidence_skill_id", table_name="skill_evidence")
    op.drop_table("skill_evidence")
