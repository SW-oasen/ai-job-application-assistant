from app.parsers.job_seniority import (
    ensure_seniority_requirement,
    extract_job_seniority,
)


def test_extracts_explicit_professional_seniority_with_years() -> None:
    seniority = extract_job_seniority(
        "Mindestens 3 Jahre Berufserfahrung sowie eigenverantwortliche Entwicklung "
        "und Architekturentscheidungen."
    )

    assert seniority == {
        "level": "professional",
        "confidence": 0.92,
        "years_required": 3.0,
        "signals": ["Mindestens 3 Jahre Berufserfahrung sowie eigenverantwortliche Entwicklung und Architekturentscheidungen."],
    }


def test_explicit_years_add_a_matching_requirement_once() -> None:
    seniority = extract_job_seniority("At least 5 years of professional experience.")
    requirements = ensure_seniority_requirement([], seniority)

    assert requirements[0]["normalized_value"] == "min_years:5"
    assert ensure_seniority_requirement(requirements, seniority) == requirements


def test_does_not_infer_seniority_from_other_team_members() -> None:
    seniority = extract_job_seniority(
        "Unser Team besteht aus Expert:innen. Du bringst erste praktische Erfahrungen mit."
    )

    assert seniority is not None
    assert seniority["level"] == "junior"
