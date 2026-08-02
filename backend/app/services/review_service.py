import json
import time
from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import ReviewWorkflowSettings, get_settings
from app.core.errors import ApplicationError
from app.schemas.review import ReviewResult, ReviewType


def _workflow_url(base_url: object) -> str:
    base = str(base_url).rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/workflows/run"


def _parse_review_output(outputs: dict[str, Any]) -> dict[str, Any]:
    payload = outputs.get("review_json", outputs.get("review", outputs))
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not isinstance(payload, dict):
        raise ValueError("Review workflow output is not an object.")
    return payload


class ReviewService:
    def __init__(
        self,
        *,
        workflows: Mapping[str, ReviewWorkflowSettings] | None = None,
        base_url: object | None = None,
    ) -> None:
        settings = get_settings()
        self._workflows = dict(workflows) if workflows is not None else settings.review_workflows
        self._base_url = base_url if base_url is not None else settings.dify_base_url

    async def review(
        self,
        *,
        review_type: ReviewType,
        source_data: dict[str, Any],
        generated_result: dict[str, Any],
        context: dict[str, Any] | None = None,
        attempt: int = 1,
        retry_instructions: list[str] | None = None,
    ) -> ReviewResult:
        workflow = self._workflow_for(review_type)
        started_at = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(workflow.timeout_seconds)) as client:
                response = await client.post(
                    _workflow_url(self._base_url),
                    headers={
                        "Authorization": f"Bearer {workflow.api_key.get_secret_value()}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "inputs": {
                            "review_type": review_type,
                            "source_data_json": json.dumps(source_data, ensure_ascii=False),
                            "generated_result_json": json.dumps(generated_result, ensure_ascii=False),
                            "context_json": json.dumps(context or {}, ensure_ascii=False),
                            "retry_instructions_json": json.dumps(
                                retry_instructions or [], ensure_ascii=False
                            ),
                            "attempt": str(attempt),
                        },
                        "response_mode": "blocking",
                        "user": f"review-{review_type}",
                    },
                )
        except httpx.RequestError as exception:
            raise ApplicationError(
                "Der Dify-Review-Workflow ist nicht erreichbar.",
                code="review_workflow_unavailable",
                status_code=503,
            ) from exception

        if response.status_code != 200:
            raise ApplicationError(
                "Der Dify-Review-Workflow konnte nicht ausgeführt werden.",
                code="review_workflow_failed",
                status_code=502,
                details={"dify_status": response.status_code},
            )
        try:
            response_data = response.json()
        except ValueError as exception:
            raise ApplicationError(
                "Der Dify-Review-Workflow hat keine gültige Antwort geliefert.",
                code="review_workflow_invalid_output",
                status_code=502,
            ) from exception
        data = response_data.get("data") if isinstance(response_data, dict) else None
        data = data or {}
        if data.get("status") != "succeeded":
            raise ApplicationError(
                "Der Dify-Review-Workflow ist fehlgeschlagen.",
                code="review_workflow_failed",
                status_code=502,
            )
        return self._normalize_result(
            review_type=review_type,
            workflow=workflow,
            outputs=data.get("outputs") or {},
            attempt=attempt,
            duration_ms=round((time.perf_counter() - started_at) * 1000),
        )

    def _workflow_for(self, review_type: ReviewType) -> ReviewWorkflowSettings:
        workflow = self._workflows.get(review_type)
        if workflow is None or not workflow.enabled:
            raise ApplicationError(
                f"Für den Review-Typ '{review_type}' ist kein Workflow aktiviert.",
                code="review_workflow_not_configured",
                status_code=503,
            )
        if workflow.api_key is None or not workflow.api_key.get_secret_value().strip():
            raise ApplicationError(
                f"Für den Review-Typ '{review_type}' fehlt der Dify-API-Schlüssel.",
                code="review_workflow_not_configured",
                status_code=503,
            )
        return workflow

    def is_configured(self, review_type: ReviewType) -> bool:
        workflow = self._workflows.get(review_type)
        return bool(
            workflow
            and workflow.enabled
            and workflow.api_key
            and workflow.api_key.get_secret_value().strip()
        )

    @staticmethod
    def _normalize_result(
        *,
        review_type: ReviewType,
        workflow: ReviewWorkflowSettings,
        outputs: dict[str, Any],
        attempt: int,
        duration_ms: int,
    ) -> ReviewResult:
        try:
            result = ReviewResult.model_validate(_parse_review_output(outputs))
        except (ValidationError, ValueError, json.JSONDecodeError) as exception:
            raise ApplicationError(
                "Der Dify-Review-Workflow hat kein gültiges Review-Ergebnis geliefert.",
                code="review_workflow_invalid_output",
                status_code=502,
            ) from exception
        if result.review_type != review_type:
            raise ApplicationError(
                "Der Dify-Review-Workflow hat einen unpassenden Review-Typ geliefert.",
                code="review_workflow_invalid_output",
                status_code=502,
            )
        return result.model_copy(
            update={
                "reviewer_model": result.reviewer_model or workflow.reviewer_model,
                "workflow_version": result.workflow_version or workflow.workflow_version,
                "prompt_version": result.prompt_version or workflow.prompt_version,
                "duration_ms": result.duration_ms if result.duration_ms is not None else duration_ms,
                "attempt": attempt,
            }
        )