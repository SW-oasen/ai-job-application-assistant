import pytest
from pydantic import ValidationError

from app.schemas.review import ReviewIssue, ReviewResult


def test_review_result_accepts_generic_json_correction_and_metadata() -> None:
    result = ReviewResult(
        review_type="job_extraction",
        status="corrected",
        decision="correct",
        overall_confidence=0.84,
        issues=[
            ReviewIssue(
                field="required_skills",
                issue_type="missing_value",
                severity="medium",
                message="Docker fehlt in der Extraktion.",
                evidence="Erfahrung mit Docker und containerisierten Anwendungen",
                suggested_value="Docker",
            )
        ],
        field_confidence={"required_skills": 0.76},
        corrected_result={"required_skills": ["Docker", "Python"], "remote": True},
        retry_instructions=["Prüfe Muss-Anforderungen erneut."],
        reviewer_model="reviewer-v1",
        workflow_version="2026-08-01",
        prompt_version="v1",
        duration_ms=1200,
        attempt=2,
    )

    payload = result.model_dump(mode="json")

    assert payload["corrected_result"]["required_skills"] == ["Docker", "Python"]
    assert payload["issues"][0]["severity"] == "medium"
    assert payload["attempt"] == 2
    assert payload["created_at"].endswith("Z")


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_review_result_rejects_out_of_range_overall_confidence(confidence: float) -> None:
    with pytest.raises(ValidationError):
        ReviewResult(
            review_type="job_matching",
            status="accepted",
            decision="accept",
            overall_confidence=confidence,
        )


def test_review_result_rejects_invalid_literal_values() -> None:
    with pytest.raises(ValidationError):
        ReviewResult(
            review_type="unknown_review",
            status="accepted",
            decision="accept",
        )

    with pytest.raises(ValidationError):
        ReviewIssue(
            field="requirements.python",
            issue_type="other",
            severity="urgent",
            message="Ungültige Schwere.",
        )


def test_review_result_rejects_non_json_correction_values() -> None:
    with pytest.raises(ValidationError):
        ReviewResult(
            review_type="job_extraction",
            status="corrected",
            corrected_result={"invalid": {"value"}},
        )