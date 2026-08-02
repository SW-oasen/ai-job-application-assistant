import pytest

from app.core.errors import ApplicationError
from app.schemas.review import ReviewResult
from app.services.job_extraction_review_decision_service import apply_job_extraction_review


def _source_extraction() -> dict:
    return {
        "metadata": {"title": "Data Engineer", "company": "Example GmbH"},
        "activities": [{"activity": "Datenpipelines entwickeln"}],
        "requirements": [{"requirement": "Python"}],
    }


def _apply(review_result: ReviewResult):
    source = _source_extraction()
    return apply_job_extraction_review(
        metadata=source["metadata"],
        activities=source["activities"],
        requirements=source["requirements"],
        review_result=review_result,
    )


def test_accept_keeps_original_job_extraction() -> None:
    source = _source_extraction()

    result = _apply(
        ReviewResult(
            review_type="job_extraction",
            status="accepted",
            decision="accept",
        )
    )

    assert result.metadata == source["metadata"]
    assert result.activities == source["activities"]
    assert result.requirements == source["requirements"]
    assert result.requires_manual_review is False


def test_correct_replaces_only_with_complete_valid_extraction() -> None:
    result = _apply(
        ReviewResult(
            review_type="job_extraction",
            status="corrected",
            decision="correct",
            corrected_result={
                "metadata": {"title": "Senior Data Engineer", "company": "Example GmbH"},
                "activities": [{"activity": "Datenprodukte verantworten"}],
                "requirements": [{"requirement": "Python"}, {"requirement": "Docker"}],
            },
        )
    )

    assert result.metadata["title"] == "Senior Data Engineer"
    assert [item["requirement"] for item in result.requirements] == ["Python", "Docker"]
    assert result.requires_manual_review is False


def test_manual_review_preserves_original_job_extraction() -> None:
    source = _source_extraction()

    result = _apply(
        ReviewResult(
            review_type="job_extraction",
            status="manual_review_required",
            decision="manual_review",
            issues=[
                {
                    "field": "requirements",
                    "issue_type": "weak_evidence",
                    "severity": "high",
                    "message": "Anforderungen sind nicht ausreichend belegt.",
                }
            ],
        )
    )

    assert result.metadata == source["metadata"]
    assert result.requires_manual_review is True


def test_correct_rejects_incomplete_correction() -> None:
    with pytest.raises(ApplicationError, match="unvollständig oder ungültig") as error:
        _apply(
            ReviewResult(
                review_type="job_extraction",
                status="corrected",
                decision="correct",
                corrected_result={"metadata": {"title": "Data Engineer"}},
            )
        )

    assert error.value.code == "invalid_extraction_correction"


def test_correct_rejects_requirements_missing_the_requirement_key() -> None:
    with pytest.raises(ApplicationError, match="unvollständig oder ungültig") as error:
        _apply(
            ReviewResult(
                review_type="job_extraction",
                status="corrected",
                decision="correct",
                corrected_result={
                    "metadata": {"title": "Data Engineer", "company": "Example GmbH"},
                    "activities": [{"activity": "Datenprodukte verantworten"}],
                    "requirements": [{"skill": "Python"}],
                },
            )
        )

    assert error.value.code == "invalid_extraction_correction"


def test_retry_is_reserved_for_the_next_package() -> None:
    with pytest.raises(ApplicationError) as error:
        _apply(
            ReviewResult(
                review_type="job_extraction",
                status="retry_requested",
                decision="retry",
            )
        )

    assert error.value.code == "unsupported_extraction_review_decision"