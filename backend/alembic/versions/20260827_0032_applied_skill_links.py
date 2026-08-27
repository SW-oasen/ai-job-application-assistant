"""Move skill evidence ownership to concrete profile evidence entries."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260827_0032"
down_revision: str | None = "20260825_0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Retire broad categories. Ambiguous data/AI/ML entries deliberately land
    # in Others for a conscious post-migration review.
    op.execute("""
        UPDATE skills SET category = CASE
            WHEN lower(canonical_name) ~ '(react|angular|vue|svelte)' THEN 'frontend_development'
            WHEN lower(canonical_name) ~ '(langchain|langgraph|openai|llm|agent|prompt)' THEN 'ai_agents'
            WHEN lower(canonical_name) ~ '(scikit|sklearn|pytorch|tensorflow|forecast|predict)' THEN 'machine_learning_predictive_analytics'
            WHEN lower(canonical_name) ~ '(airflow|dbt|spark|kafka|etl|data warehouse)' THEN 'data_engineering'
            ELSE 'software_development_apis'
        END
        WHERE category = 'frameworks_libraries'
    """)
    op.execute("""
        UPDATE skills SET category = CASE
            WHEN lower(canonical_name) ~ '(langchain|langgraph|openai|llm|agent|prompt)' THEN 'ai_agents'
            WHEN lower(canonical_name) ~ '(scikit|sklearn|pytorch|tensorflow|forecast|predict)' THEN 'machine_learning_predictive_analytics'
            WHEN lower(canonical_name) ~ '(airflow|dbt|spark|kafka|etl|data warehouse)' THEN 'data_engineering'
            ELSE 'other'
        END
        WHERE category = 'data_ai_ml'
    """)
    # Manual training has no concrete profile entry. Preserve it as immutable
    # profile history before retiring this unsupported evidence form.
    op.execute("""
        INSERT INTO profile_entity_revisions
            (id, profile_id, entity_type, entity_id, revision, action, snapshot, change_reason)
        SELECT se.id, s.profile_id, 'legacy_skill_evidence', se.id, 1, 'archived',
               jsonb_build_object(
                   'skill_id', se.skill_id,
                   'source_resource_type', se.source_resource_type,
                   'source_resource_id', se.source_resource_id,
                   'experience_context', se.experience_context,
                   'evidence_text', se.evidence_text,
                   'confidence', se.confidence
               ),
               'Bei Umstellung auf angewandte Skills archiviert.'
        FROM skill_evidence se
        JOIN skills s ON s.id = se.skill_id
        WHERE se.source_resource_type = 'manual_training'
    """)
    op.execute("DELETE FROM skill_evidence WHERE source_resource_type = 'manual_training'")
    op.rename_table("skill_evidence", "applied_skill_links")
    op.execute("ALTER TABLE applied_skill_links RENAME CONSTRAINT uq_skill_evidence_source TO uq_applied_skill_link_source")
    op.drop_index("ix_skill_evidence_skill_id", table_name="applied_skill_links")
    op.create_index("ix_applied_skill_links_skill_id", "applied_skill_links", ["skill_id"])
    op.drop_column("applied_skill_links", "experience_context")
    op.drop_column("applied_skill_links", "evidence_text")
    op.drop_column("applied_skill_links", "confidence")


def downgrade() -> None:
    op.add_column("applied_skill_links", sa.Column("experience_context", sa.String(30), nullable=True))
    op.add_column("applied_skill_links", sa.Column("evidence_text", sa.Text(), nullable=True))
    op.add_column("applied_skill_links", sa.Column("confidence", sa.Float(), nullable=False, server_default="1"))
    op.drop_index("ix_applied_skill_links_skill_id", table_name="applied_skill_links")
    op.create_index("ix_skill_evidence_skill_id", "applied_skill_links", ["skill_id"])
    op.execute("ALTER TABLE applied_skill_links RENAME CONSTRAINT uq_applied_skill_link_source TO uq_skill_evidence_source")
    op.rename_table("applied_skill_links", "skill_evidence")
