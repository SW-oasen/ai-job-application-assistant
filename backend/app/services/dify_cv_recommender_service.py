"""Dify client for structured, source-referenced CV recommendations."""

import json
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import ApplicationError


async def run_cv_recommender_workflow(*, job: dict, master_profile: str, inventory: dict, language: str, user: str) -> tuple[dict, str | None]:
    settings = get_settings()
    if settings.dify_cv_recommender_workflow_api_key is None or not settings.dify_cv_recommender_workflow_api_key.get_secret_value().strip():
        raise ApplicationError("Der Dify-CV-Recommender ist noch nicht konfiguriert. DIFY_CV_RECOMMENDER_WORKFLOW_API_KEY fehlt.", code="dify_cv_recommender_not_configured", status_code=503)
    base = str(settings.dify_base_url).rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(settings.dify_cv_recommender_workflow_timeout_seconds)) as client:
            response = await client.post(
                f"{base}/workflows/run",
                headers={"Authorization": f"Bearer {settings.dify_cv_recommender_workflow_api_key.get_secret_value().strip()}", "Content-Type": "application/json"},
                json={"inputs": {"language": language, "job_context": json.dumps(job, ensure_ascii=False), "master_profile": master_profile, "source_inventory": json.dumps(inventory, ensure_ascii=False)}, "response_mode": "blocking", "user": user},
            )
    except httpx.RequestError as error:
        raise ApplicationError("Die lokale Dify-Instanz ist für den CV-Recommender nicht erreichbar.", code="dify_unavailable", status_code=503) from error
    if response.status_code != 200:
        raise ApplicationError("Der Dify-CV-Recommender konnte nicht ausgeführt werden.", code="dify_cv_recommender_failed", status_code=502, details={"dify_status": response.status_code})
    body: Any = response.json()
    data = body.get("data") or {}
    if data.get("status") != "succeeded":
        raise ApplicationError(data.get("error") or "Der Dify-CV-Recommender ist fehlgeschlagen.", code="dify_cv_recommender_failed", status_code=502)
    raw = (data.get("outputs") or {}).get("recommendation_json")
    try:
        recommendation = json.loads(raw) if isinstance(raw, str) else raw
    except json.JSONDecodeError as error:
        raise ApplicationError("Der Dify-CV-Recommender lieferte kein gültiges JSON.", code="dify_cv_recommender_invalid_output", status_code=502) from error
    if not isinstance(recommendation, dict):
        raise ApplicationError("Der Dify-CV-Recommender lieferte keine Recommendation.", code="dify_cv_recommender_invalid_output", status_code=502)
    return recommendation, data.get("id") or body.get("workflow_run_id")
