import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.schemas.matching import MatchingWorkflowRequest
from app.services.job_matching_review_integration import review_stored_job_matching_if_configured

# Sandbox code-node failures surface as a raw Python traceback; only the final
# exception line is useful to a user, so extract it instead of showing the trace.
_TRACEBACK_EXCEPTION_LINE = re.compile(r"^[\w.]*Error: (?P<message>.+)$", re.MULTILINE)

_KNOWN_WORKFLOW_ERRORS: dict[str, str] = {
    "Keine prüfbaren Anforderungen in der Stellenanzeige erkannt": (
        "Für diese Stellenanzeige konnten keine prüfbaren Anforderungen ermittelt "
        "werden. Bitte Job-Metadaten prüfen oder die Anzeige erneut importieren."
    ),
}


def _workflow_url() -> str:
    base = str(get_settings().dify_base_url).rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/workflows/run"


def _friendly_workflow_failure_message(raw_error: str | None) -> tuple[str, str]:
    """Turn a raw Dify/sandbox error (possibly a full traceback) into a user message."""
    raw_error = (raw_error or "").strip()
    if not raw_error:
        return "Der Dify-Matching-Workflow ist fehlgeschlagen.", "dify_matching_workflow_failed"
    match = _TRACEBACK_EXCEPTION_LINE.search(raw_error)
    exception_message = match.group("message").strip() if match else raw_error
    for known_fragment, friendly_message in _KNOWN_WORKFLOW_ERRORS.items():
        if known_fragment in exception_message:
            return friendly_message, "matching_no_requirements"
    if match:
        return exception_message, "dify_matching_workflow_failed"
    return (
        f"Der Dify-Matching-Workflow ist fehlgeschlagen: {exception_message[:800]}",
        "dify_matching_workflow_failed",
    )


def _workflow_error(response: httpx.Response) -> ApplicationError:
    try:
        body: Any = response.json()
    except ValueError:
        body = {}
    message = body.get("message") if isinstance(body, dict) else None
    return ApplicationError(
        message or "Der Dify-Matching-Workflow konnte nicht ausgeführt werden.",
        code="dify_matching_workflow_failed",
        status_code=502,
        details={"dify_status": response.status_code},
    )


async def run_matching_workflow(payload: MatchingWorkflowRequest) -> dict:
    settings = get_settings()
    if settings.dify_matching_workflow_api_key is None:
        raise ApplicationError(
            "Matching ist noch nicht für die GUI konfiguriert. "
            "DIFY_MATCHING_WORKFLOW_API_KEY fehlt im Backend.",
            code="dify_matching_workflow_not_configured",
            status_code=503,
        )
    token = settings.dify_matching_workflow_api_key.get_secret_value().strip()
    if not token:
        raise ApplicationError(
            "Matching ist noch nicht für die GUI konfiguriert. "
            "DIFY_MATCHING_WORKFLOW_API_KEY ist leer.",
            code="dify_matching_workflow_not_configured",
            status_code=503,
        )

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(settings.dify_matching_workflow_timeout_seconds)
        ) as client:
            response = await client.post(
                _workflow_url(),
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "inputs": {
                        "job_id": str(payload.job_id),
                        "profile_id": str(payload.profile_id),
                    },
                    "response_mode": "blocking",
                    "user": f"matching-{payload.profile_id}",
                },
            )
    except httpx.RequestError as exception:
        raise ApplicationError(
            "Die lokale Dify-Instanz ist für das Matching nicht erreichbar.",
            code="dify_unavailable",
            status_code=503,
        ) from exception

    if response.status_code != 200:
        raise _workflow_error(response)
    result = response.json()
    data = result.get("data") or {}
    if data.get("status") != "succeeded":
        message, code = _friendly_workflow_failure_message(data.get("error"))
        raise ApplicationError(
            message,
            code=code,
            status_code=422 if code == "matching_no_requirements" else 502,
        )
    await review_stored_job_matching_if_configured(
        job_id=payload.job_id,
        profile_id=payload.profile_id,
    )
    return {
        "workflow_run_id": data.get("id") or result.get("workflow_run_id"),
        "status": data.get("status"),
        "job_id": str(payload.job_id),
        "profile_id": str(payload.profile_id),
        "outputs": data.get("outputs") or {},
    }
