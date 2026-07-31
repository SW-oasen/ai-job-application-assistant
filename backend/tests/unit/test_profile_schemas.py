import pytest
from pydantic import ValidationError

from app.schemas.profile import PortfolioProjectCreate, SkillCreate, WorkExperienceCreate


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
