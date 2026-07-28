from app.services.cv_import_service import (
    _conflict_details,
    _find_matching_entity,
    _structured_cv_to_suggestions,
)


def test_structured_cv_becomes_reviewable_profile_suggestions() -> None:
    suggestions = _structured_cv_to_suggestions(
        {
            "profile": {
                "name": "Ada Example",
                "email": "ada@example.invalid",
                "linkedin": "https://example.invalid/ada",
                "summary": "Job-specific text is not canonical.",
            },
            "skills": {
                "categories": [{"category": "Programming", "skills": ["Python"]}],
                "languages": [{"language": "Deutsch", "level": "Muttersprache"}],
            },
            "work_experience": [
                {
                    "company": "Example GmbH",
                    "job_title": "AI Engineer",
                    "start_date": "2024-01-01",
                    "end_date": "",
                    "activities": ["Built retrieval systems"],
                }
            ],
            "education": [],
            "certificates": [],
            "references": [],
        },
        "de",
    )

    assert [item.resource_type for item in suggestions] == [
        "profile",
        "skills",
        "skills",
        "experiences",
    ]
    assert suggestions[0].proposed_data == {
        "full_name": "Ada Example",
        "email": "ada@example.invalid",
        "linkedin_url": "https://example.invalid/ada",
    }
    assert "summary" not in suggestions[0].proposed_data
    assert suggestions[1].proposed_data["canonical_name"] == "Python"
    assert suggestions[1].proposed_data["category"] == "programming_languages"
    assert suggestions[2].proposed_data["category"] == "natural_languages"
    assert suggestions[2].proposed_data["proficiency_level"] == "expert"
    assert suggestions[3].proposed_data["localizations"][0]["title"] == "AI Engineer"


def test_reference_import_never_grants_usage_consent() -> None:
    suggestions = _structured_cv_to_suggestions(
        {
            "skills": {"categories": [], "languages": []},
            "references": [
                {
                    "name": "Ada Example",
                    "job_title": "CTO",
                    "company": "Example AG",
                    "linkedin": "https://example.invalid/ada",
                }
            ],
        },
        "en",
    )

    assert suggestions[0].proposed_data["usage_consent"] is False
    assert (
        suggestions[0].proposed_data["localizations"][0]["summary"]
        == "https://example.invalid/ada"
    )


def test_partial_cv_dates_become_reviewable_iso_dates() -> None:
    suggestions = _structured_cv_to_suggestions(
        {
            "skills": {"categories": [], "languages": []},
            "work_experience": [
                {
                    "company": "Example GmbH",
                    "job_title": "Engineer",
                    "start_date": "03 2021",
                    "end_date": "02/2024",
                    "activities": [],
                }
            ],
            "education": [
                {
                    "qualification": "M.Sc.",
                    "institution": "Example University",
                    "field": "Computer Science",
                    "date": "09 2020",
                }
            ],
            "certificates": [
                {
                    "name": "Certificate",
                    "institution": "Issuer",
                    "date": "04-2023",
                }
            ],
            "references": [],
        },
        "de",
    )

    assert suggestions[0].proposed_data["start_date"] == "2021-03-01"
    assert suggestions[0].proposed_data["end_date"] == "2024-02-29"
    assert suggestions[1].proposed_data["start_date"] is None
    assert suggestions[1].proposed_data["end_date"] == "2020-09-30"
    assert suggestions[2].proposed_data["issued_at"] == "2023-04-01"


def test_german_and_english_named_months_are_normalized() -> None:
    suggestions = _structured_cv_to_suggestions(
        {
            "skills": {"categories": [], "languages": []},
            "work_experience": [
                {
                    "company": "Example GmbH",
                    "job_title": "Engineer",
                    "start_date": "Okt 2021",
                    "end_date": "Oct 2025",
                    "activities": [],
                }
            ],
            "education": [
                {
                    "qualification": "M.Sc.",
                    "institution": "Example University",
                    "field": "Computer Science",
                    "date": "März 2020",
                }
            ],
            "certificates": [],
            "references": [],
        },
        "de",
    )

    assert suggestions[0].proposed_data["start_date"] == "2021-10-01"
    assert suggestions[0].proposed_data["end_date"] == "2025-10-31"
    assert suggestions[1].proposed_data["end_date"] == "2020-03-31"


def test_skill_duplicate_matching_is_case_and_punctuation_insensitive() -> None:
    existing = {
        "id": "skill-1",
        "canonical_name": "Scikit-learn",
        "category": "frameworks_libraries",
        "localizations": [],
    }
    matched = _find_matching_entity(
        "skills",
        {
            "canonical_name": "scikit learn",
            "category": "frameworks_libraries",
            "localizations": [],
        },
        {"skills": [existing]},
    )

    assert matched == existing
    assert (
        _conflict_details(
            {
                "canonical_name": "scikit learn",
                "category": "frameworks_libraries",
                "localizations": [],
            },
            existing,
        )["conflict_status"]
        == "duplicate"
    )


def test_matching_experience_with_changed_dates_is_a_conflict() -> None:
    existing = {
        "id": "experience-1",
        "company": "Example GmbH",
        "start_date": "2021-01-01",
        "end_date": "2024-12-31",
        "localizations": [{"language": "de", "title": "AI Engineer"}],
    }
    proposed = {
        "company": "example gmbh",
        "start_date": "2020-10-01",
        "end_date": "2024-12-31",
        "localizations": [{"language": "de", "title": "AI Engineer"}],
    }

    matched = _find_matching_entity(
        "experiences",
        proposed,
        {"experiences": [existing]},
    )
    details = _conflict_details(proposed, matched)

    assert matched == existing
    assert details["conflict_status"] == "conflict"
    assert {item["field"] for item in details["differences"]} == {"start_date"}


def test_reference_prefers_email_as_duplicate_identity() -> None:
    existing = {
        "id": "reference-1",
        "full_name": "Ada Example",
        "organization": "Old Company",
        "email": "ADA@example.invalid",
    }
    matched = _find_matching_entity(
        "references",
        {
            "full_name": "Ada Example",
            "organization": "New Company",
            "email": "ada@example.invalid",
        },
        {"references": [existing]},
    )

    assert matched == existing
    assert _conflict_details(
        {
            "full_name": "Ada Example",
            "organization": "New Company",
            "email": "ada@example.invalid",
        },
        existing,
    )["conflict_status"] == "conflict"
