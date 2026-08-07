from app.parsers.job_role import extract_job_role


def test_extracts_role_without_seniority_from_title() -> None:
    assert extract_job_role("Senior Machine Learning Engineer", "") == "Machine Learning Engineer"


def test_lead_times_does_not_create_seniority_signal() -> None:
    from app.parsers.job_seniority import extract_job_seniority

    assert extract_job_seniority("capacities, costs and lead times") is None


def test_description_role_takes_precedence_when_explicitly_contextualized() -> None:
    assert extract_job_role(
        "Senior Data Scientist",
        "Your role: Machine Learning Engineer. You will build production models.",
    ) == "Machine Learning Engineer"
