import pytest
from pydantic import ValidationError

from app.schemas.profile import SkillCreate, WorkExperienceCreate


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
