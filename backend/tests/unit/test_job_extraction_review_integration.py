import pytest

from app.core.errors import ApplicationError
from app.schemas.review import ReviewResult
from app.services import job_extraction_review_integration
from app.services.job_extraction_review_integration import review_job_extraction_if_configured


class DisabledReviewService:
    def is_configured(self, review_type: str) -> bool:
        assert review_type == "job_extraction"
        return False


@pytest.mark.asyncio
async def test_unconfigured_extraction_review_keeps_current_import_result() -> None:
    metadata = {"title": "Data Engineer", "company": "Example GmbH"}
    activities = [{"activity": "Datenpipelines entwickeln"}]
    requirements = [{"requirement": "Python"}]

    result = await review_job_extraction_if_configured(
        content="Stellenanzeige",
        metadata=metadata,
        activities=activities,
        requirements=requirements,
        review_service=DisabledReviewService(),
    )

    assert result.metadata == metadata
    assert result.activities == activities
    assert result.requirements == requirements
    assert result.review_results == ()


class EnabledReviewService:
    def is_configured(self, review_type: str) -> bool:
        assert review_type == "job_extraction"
        return True


@pytest.mark.asyncio
async def test_failed_extraction_review_keeps_import_result_and_records_failure(monkeypatch) -> None:
    metadata = {"title": "Data Engineer"}
    activities = [{"activity": "Datenpipelines entwickeln"}]
    requirements = [{"requirement": "Python"}]

    async def fail_review(*args, **kwargs):
        raise ApplicationError(
            "Der Dify-Review-Workflow konnte nicht ausgeführt werden.",
            code="review_workflow_failed",
            status_code=502,
        )

    monkeypatch.setattr(
        job_extraction_review_integration,
        "review_job_extraction_with_retry",
        fail_review,
    )

    result = await review_job_extraction_if_configured(
        content="Stellenanzeige",
        metadata=metadata,
        activities=activities,
        requirements=requirements,
        review_service=EnabledReviewService(),
    )

    assert result.metadata == metadata
    assert result.review_results[0].status == "failed"
    assert result.review_results[0].technical_error == (
        "review_workflow_failed: Der Dify-Review-Workflow konnte nicht ausgeführt werden."
    )