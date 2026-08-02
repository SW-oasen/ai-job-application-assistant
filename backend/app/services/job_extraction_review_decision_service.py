from dataclasses import dataclass
from typing import Any

from app.core.errors import ApplicationError
from app.schemas.review import ReviewResult


@dataclass(frozen=True)
class ReviewedJobExtraction:
    metadata: dict[str, str | None]
    activities: list[dict[str, Any]]
    requirements: list[dict[str, Any]]
    requires_manual_review: bool


def apply_job_extraction_review(
    *,
    metadata: dict[str, str | None],
    activities: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    review_result: ReviewResult,
) -> ReviewedJobExtraction:
    if review_result.review_type != "job_extraction":
        raise ApplicationError(
            "Das Review-Ergebnis gehört nicht zu einer Job-Extraktion.",
            code="invalid_extraction_review",
            status_code=422,
        )
    if review_result.decision == "accept":
        return ReviewedJobExtraction(metadata, activities, requirements, False)
    if review_result.decision == "manual_review":
        return ReviewedJobExtraction(metadata, activities, requirements, True)
    if review_result.decision == "correct":
        corrected = review_result.corrected_result
        corrected_metadata = corrected.get("metadata")
        corrected_activities = corrected.get("activities")
        corrected_requirements = corrected.get("requirements")
        if not (
            isinstance(corrected_metadata, dict)
            and all(isinstance(key, str) and (isinstance(value, str) or value is None)
                    for key, value in corrected_metadata.items())
            and _is_list_of_activities(corrected_activities)
            and _is_list_of_requirements(corrected_requirements)
        ):
            raise ApplicationError(
                "Die korrigierte Job-Extraktion ist unvollständig oder ungültig.",
                code="invalid_extraction_correction",
                status_code=422,
            )
        return ReviewedJobExtraction(
            metadata=corrected_metadata,
            activities=corrected_activities,
            requirements=corrected_requirements,
            requires_manual_review=False,
        )
    raise ApplicationError(
        "Die Review-Entscheidung wird für die Job-Extraktion noch nicht unterstützt.",
        code="unsupported_extraction_review_decision",
        status_code=422,
    )


def _is_list_of_objects(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def _is_list_of_activities(value: object) -> bool:
    return _is_list_of_objects(value) and all(
        isinstance(item.get("activity"), str) and item["activity"].strip()
        for item in value
    )


def _is_list_of_requirements(value: object) -> bool:
    return _is_list_of_objects(value) and all(
        isinstance(item.get("requirement"), str) and item["requirement"].strip()
        for item in value
    )