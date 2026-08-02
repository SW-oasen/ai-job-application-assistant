import pytest
from uuid import uuid4

from app.core.errors import ApplicationError
from app.schemas.review import ReviewResult
from app.services import job_matching_review_integration


class DisabledReviewService:
    def is_configured(self, review_type: str) -> bool:
        assert review_type == "job_matching"
        return False


@pytest.mark.asyncio
async def test_unconfigured_matching_review_does_not_load_or_store_results(monkeypatch) -> None:
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("Matching review must be inactive without configuration")

    monkeypatch.setattr(job_matching_review_integration, "get_stored_matching", fail_if_called)
    monkeypatch.setattr(job_matching_review_integration, "review_job_matching", fail_if_called)
    monkeypatch.setattr(job_matching_review_integration, "store_review_result", fail_if_called)

    await job_matching_review_integration.review_stored_job_matching_if_configured(
        job_id=uuid4(),
        profile_id=uuid4(),
        review_service=DisabledReviewService(),
    )


class EnabledReviewService:
    def is_configured(self, review_type: str) -> bool:
        assert review_type == "job_matching"
        return True


@pytest.mark.asyncio
async def test_configured_matching_review_loads_reviews_and_stores_result(monkeypatch) -> None:
    job_id = uuid4()
    profile_id = uuid4()
    matching = {
        "job": {"id": str(job_id), "title": "Engineer"},
        "profile": {"id": str(profile_id), "name": "Alex"},
        "matches": [{"requirement": "Python", "score": 0.9}],
        "qualification_fit": {"score": 0.9},
        "target_fit": {"score": 0.8},
        "recommendation": {"recommendation": "apply"},
    }
    captured: dict = {}

    async def get_matching(*args, **kwargs):
        assert args == (job_id, profile_id)
        return matching

    async def review_matching(**kwargs):
        captured["review"] = kwargs
        return ReviewResult(
            review_type="job_matching",
            status="accepted",
            decision="accept",
            overall_confidence=0.95,
        )

    async def store_result(**kwargs):
        captured["store"] = kwargs
        return {}

    monkeypatch.setattr(job_matching_review_integration, "get_stored_matching", get_matching)
    monkeypatch.setattr(job_matching_review_integration, "review_job_matching", review_matching)
    monkeypatch.setattr(job_matching_review_integration, "store_review_result", store_result)

    await job_matching_review_integration.review_stored_job_matching_if_configured(
        job_id=job_id,
        profile_id=profile_id,
        review_service=EnabledReviewService(),
    )

    assert captured["review"]["job"] == matching["job"]
    assert captured["review"]["profile"] == matching["profile"]
    assert captured["store"]["subject_id"] == job_id
    assert captured["store"]["final_result"]["matches"] == matching["matches"]
    assert captured["store"]["context"] == {"profile_id": str(profile_id)}


@pytest.mark.asyncio
async def test_failed_matching_review_is_stored_without_raising(monkeypatch) -> None:
    job_id = uuid4()
    profile_id = uuid4()
    captured: dict = {}

    async def get_matching(*args, **kwargs):
        return {
            "job": {},
            "profile": {},
            "matches": [],
            "qualification_fit": {},
            "target_fit": {},
            "recommendation": {},
        }

    async def fail_review(**kwargs):
        raise ApplicationError(
            "Der Dify-Review-Workflow konnte nicht ausgeführt werden.",
            code="review_workflow_failed",
            status_code=502,
        )

    async def store_result(**kwargs):
        captured.update(kwargs)
        return {}

    monkeypatch.setattr(job_matching_review_integration, "get_stored_matching", get_matching)
    monkeypatch.setattr(job_matching_review_integration, "review_job_matching", fail_review)
    monkeypatch.setattr(job_matching_review_integration, "store_review_result", store_result)

    await job_matching_review_integration.review_stored_job_matching_if_configured(
        job_id=job_id,
        profile_id=profile_id,
        review_service=EnabledReviewService(),
    )

    assert captured["review_result"].status == "failed"
    assert captured["final_result"] == {"matches": [], "qualification_fit": {}, "target_fit": {}, "recommendation": {}}