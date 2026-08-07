import json
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.core.config import ReviewWorkflowSettings
from app.core.errors import ApplicationError
from app.services.review_service import (
    ReviewService,
    _normalize_review_confidences,
    _serialize_workflow_input,
)


def _workflow() -> ReviewWorkflowSettings:
    return ReviewWorkflowSettings(
        api_key="test-token",
        reviewer_model="reviewer-v1",
        workflow_version="workflow-v1",
        prompt_version="prompt-v1",
    )


def test_serialize_workflow_input_normalizes_datetime_and_uuid() -> None:
    identifier = uuid4()
    timestamp = datetime(2026, 8, 2, 15, 44, 52, tzinfo=timezone.utc)

    result = json.loads(
        _serialize_workflow_input({"id": identifier, "updated_at": timestamp})
    )

    assert result == {"id": str(identifier), "updated_at": "2026-08-02T15:44:52+00:00"}


def test_normalize_review_confidences_converts_percentages_to_fractions() -> None:
    result = _normalize_review_confidences(
        {"overall_confidence": 85, "field_confidence": {"matches": 90, "fit": 0.8}}
    )

    assert result == {
        "overall_confidence": 0.85,
        "field_confidence": {"matches": 0.9, "fit": 0.8},
    }


def test_normalize_review_result_adds_configured_metadata() -> None:
    result = ReviewService._normalize_result(
        review_type="job_extraction",
        workflow=_workflow(),
        outputs={
            "review_json": {
                "review_type": "job_extraction",
                "status": "accepted",
                "decision": "accept",
                "overall_confidence": 0.91,
            }
        },
        attempt=1,
        duration_ms=45,
    )

    assert result.reviewer_model == "reviewer-v1"
    assert result.workflow_version == "workflow-v1"
    assert result.prompt_version == "prompt-v1"
    assert result.duration_ms == 45


def test_normalize_review_result_rejects_wrong_review_type() -> None:
    with pytest.raises(ApplicationError, match="unpassenden Review-Typ") as error:
        ReviewService._normalize_result(
            review_type="job_extraction",
            workflow=_workflow(),
            outputs={
                "review_json": {
                    "review_type": "job_matching",
                    "status": "accepted",
                }
            },
            attempt=1,
            duration_ms=45,
        )

    assert error.value.code == "review_workflow_invalid_output"


def test_review_rejects_missing_workflow_configuration() -> None:
    service = ReviewService(workflows={})

    with pytest.raises(ApplicationError, match="kein Workflow aktiviert") as error:
        service._workflow_for("job_extraction")

    assert error.value.code == "review_workflow_not_configured"


@pytest.mark.parametrize("payload", ["not-json", {"status": "accepted"}])
def test_normalize_review_result_rejects_invalid_output(payload: object) -> None:
    with pytest.raises(ApplicationError) as error:
        ReviewService._normalize_result(
            review_type="job_extraction",
            workflow=_workflow(),
            outputs={"review_json": payload},
            attempt=1,
            duration_ms=45,
        )

    assert error.value.code == "review_workflow_invalid_output"