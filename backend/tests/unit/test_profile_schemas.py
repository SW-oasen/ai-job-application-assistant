import pytest
from pydantic import ValidationError

from app.schemas.profile import (
    PortfolioProjectCreate,
    ReferenceCreate,
    SkillCreate,
    WorkExperienceCreate,
)


def test_skill_accepts_distinct_german_and_english_localizations() -> None:
    skill = SkillCreate(
        canonical_name="PostgreSQL",
        category="databases",
        localizations=[
            {"language": "de", "title": "PostgreSQL", "status": "approved"},
            {"language": "en", "title": "PostgreSQL", "status": "approved"},
        ],
    )

    assert [item.language for item in skill.localizations] == ["de", "en"]


def test_duplicate_localization_language_is_rejected() -> None:
    with pytest.raises(ValidationError):
        WorkExperienceCreate(
            company="Example GmbH",
            start_date="2024-01-01",
            localizations=[
                {"language": "de", "title": "Entwickler"},
                {"language": "de", "title": "Softwareentwickler"},
            ],
        )


def test_portfolio_project_accepts_evidence_fields() -> None:
    project = PortfolioProjectCreate(
        canonical_name="Application Assistant",
        role="Konzeption und Entwicklung",
        technologies=["Python", "FastAPI"],
        repository_url="https://github.com/example/application-assistant",
        localizations=[
            {
                "language": "de",
                "title": "KI-Bewerbungsassistent",
                "summary": "Evidenzbasiertes Matching.",
            }
        ],
    )

    assert project.technologies == ["Python", "FastAPI"]


def test_evidence_entries_accept_applied_skills() -> None:
    skill_id = "8bb4ecb4-ef8f-4d8a-8c8a-7f2f6d658913"
    experience = WorkExperienceCreate(
        company="Example GmbH",
        start_date="2024-01-01",
        applied_skill_ids=[skill_id],
    )

    assert [str(item) for item in experience.applied_skill_ids] == [skill_id]


def test_reference_accepts_linkedin_profile_url_only() -> None:
    reference = ReferenceCreate(
        full_name="Maria Mustermann",
        linkedin_url="https://www.linkedin.com/in/maria-mustermann",
    )

    assert str(reference.linkedin_url) == "https://www.linkedin.com/in/maria-mustermann"

    with pytest.raises(ValidationError):
        ReferenceCreate(
            full_name="Maria Mustermann",
            linkedin_url="https://example.com/maria-mustermann",
        )
