import logging
from typing import Any
from uuid import UUID

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from app.core.errors import ApplicationError
from app.database.models import ReviewIssue, ReviewRun
from app.database.session import get_session_factory
from app.schemas.review import ReviewResult, ReviewType

logger = logging.getLogger(__name__)


def _session_factory():
    factory = get_session_factory()
    if factory is None:
        raise ApplicationError(
            "Review history requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    return factory


def _serialize_issue(issue: ReviewIssue) -> dict[str, Any]:
    return jsonable_encoder(
        {
            "id": issue.id,
            "field": issue.field,
            "issue_type": issue.issue_type,
            "severity": issue.severity,
            "message": issue.message,
            "evidence": issue.evidence,
            "suggested_value": issue.suggested_value,
            "position": issue.position,
        }
    )


def _serialize_run(review_run: ReviewRun) -> dict[str, Any]:
    return jsonable_encoder(
        {
            "id": review_run.id,
            "subject_type": review_run.subject_type,
            "subject_id": review_run.subject_id,
            "review_type": review_run.review_type,
            "status": review_run.status,
            "decision": review_run.decision,
            "overall_confidence": review_run.overall_confidence,
            "source_result": review_run.source_result,
            "corrected_result": review_run.corrected_result,
            "final_result": review_run.final_result,
            "field_confidence": review_run.field_confidence,
            "retry_instructions": review_run.retry_instructions,
            "context": review_run.context,
            "reviewer_model": review_run.reviewer_model,
            "workflow_version": review_run.workflow_version,
            "prompt_version": review_run.prompt_version,
            "duration_ms": review_run.duration_ms,
            "attempt": review_run.attempt,
            "technical_error": review_run.technical_error,
            "created_at": review_run.created_at,
            "updated_at": review_run.updated_at,
            "issues": [_serialize_issue(issue) for issue in review_run.issues],
        }
    )


async def store_review_result(
    *,
    subject_type: str,
    subject_id: UUID,
    source_result: dict[str, Any],
    review_result: ReviewResult,
    final_result: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    factory = _session_factory()
    try:
        async with factory() as session:
            review_run = ReviewRun(
                subject_type=subject_type,
                subject_id=subject_id,
                review_type=review_result.review_type,
                status=review_result.status,
                decision=review_result.decision,
                overall_confidence=review_result.overall_confidence,
                source_result=jsonable_encoder(source_result),
                corrected_result=jsonable_encoder(review_result.corrected_result),
                final_result=jsonable_encoder(final_result) if final_result is not None else None,
                field_confidence=jsonable_encoder(review_result.field_confidence),
                retry_instructions=list(review_result.retry_instructions),
                context=jsonable_encoder(context) if context is not None else None,
                reviewer_model=review_result.reviewer_model,
                workflow_version=review_result.workflow_version,
                prompt_version=review_result.prompt_version,
                duration_ms=review_result.duration_ms,
                attempt=review_result.attempt,
                technical_error=review_result.technical_error,
            )
            session.add(review_run)
            for position, issue in enumerate(review_result.issues):
                review_run.issues.append(
                    ReviewIssue(
                        field=issue.field,
                        issue_type=issue.issue_type,
                        severity=issue.severity,
                        message=issue.message,
                        evidence=issue.evidence,
                        suggested_value=jsonable_encoder(issue.suggested_value),
                        position=position,
                    )
                )
            await session.commit()
            await session.refresh(review_run, attribute_names=["issues"])
            return _serialize_run(review_run)
    except SQLAlchemyError as exception:
        logger.exception(
            "review_history_store_failed",
            extra={"subject_type": subject_type, "subject_id": str(subject_id)},
        )
        raise ApplicationError(
            "The review result could not be stored.",
            code="database_unavailable",
            status_code=503,
        ) from exception


async def list_review_history(
    *,
    subject_type: str,
    subject_id: UUID,
    review_type: ReviewType | None = None,
) -> list[dict[str, Any]]:
    factory = _session_factory()
    try:
        async with factory() as session:
            statement = (
                select(ReviewRun)
                .where(
                    ReviewRun.subject_type == subject_type,
                    ReviewRun.subject_id == subject_id,
                )
                .options(selectinload(ReviewRun.issues))
                .order_by(ReviewRun.created_at.desc(), ReviewRun.attempt.desc())
            )
            if review_type is not None:
                statement = statement.where(ReviewRun.review_type == review_type)
            rows = (await session.scalars(statement)).all()
            return [_serialize_run(row) for row in rows]
    except SQLAlchemyError as exception:
        logger.exception(
            "review_history_load_failed",
            extra={"subject_type": subject_type, "subject_id": str(subject_id)},
        )
        raise ApplicationError(
            "The review history could not be loaded.",
            code="database_unavailable",
            status_code=503,
        ) from exception