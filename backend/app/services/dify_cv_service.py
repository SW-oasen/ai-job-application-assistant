from typing import Any
from uuid import UUID

import httpx

from app.core.config import get_settings
from app.core.errors import ApplicationError


def _api_url(path: str) -> str:
    base = str(get_settings().dify_base_url).rstrip("/")
    if not base.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/{path.lstrip('/')}"


def _dify_error(response: httpx.Response, fallback: str) -> ApplicationError:
    try:
        body: Any = response.json()
    except ValueError:
        body = {}
    message = body.get("message") if isinstance(body, dict) else None
    return ApplicationError(
        message or fallback,
        code="dify_cv_workflow_failed",
        status_code=502,
        details={"dify_status": response.status_code},
    )


async def import_cv_pdf_with_dify(
    *,
    profile_id: UUID,
    filename: str,
    content: bytes,
    source_language: str,
) -> dict:
    settings = get_settings()
    if settings.dify_cv_workflow_api_key is None:
        raise ApplicationError(
            "Der Dify-CV-Workflow ist noch nicht konfiguriert. "
            "DIFY_CV_WORKFLOW_API_KEY fehlt im Backend.",
            code="dify_cv_workflow_not_configured",
            status_code=503,
        )

    token = settings.dify_cv_workflow_api_key.get_secret_value().strip()
    if not token:
        raise ApplicationError(
            "Der Dify-CV-Workflow ist noch nicht konfiguriert. "
            "DIFY_CV_WORKFLOW_API_KEY ist leer.",
            code="dify_cv_workflow_not_configured",
            status_code=503,
        )

    headers = {"Authorization": f"Bearer {token}"}
    user = f"profile-{profile_id}"
    timeout = httpx.Timeout(settings.dify_cv_workflow_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            upload = await client.post(
                _api_url("/files/upload"),
                headers=headers,
                data={"user": user},
                files={"file": (filename, content, "application/pdf")},
            )
            if upload.status_code != 201:
                raise _dify_error(upload, "Die PDF konnte nicht zu Dify hochgeladen werden.")
            upload_id = upload.json().get("id")
            if not upload_id:
                raise ApplicationError(
                    "Dify hat für die hochgeladene PDF keine Datei-ID zurückgegeben.",
                    code="dify_file_id_missing",
                    status_code=502,
                )

            run = await client.post(
                _api_url("/workflows/run"),
                headers={**headers, "Content-Type": "application/json"},
                json={
                    "inputs": {
                        "profile_id": str(profile_id),
                        "source_language": source_language,
                        "source_filename": filename,
                        "local_cv_pdf": [
                            {
                                "type": "document",
                                "transfer_method": "local_file",
                                "upload_file_id": upload_id,
                            }
                        ],
                    },
                    "response_mode": "blocking",
                    "user": user,
                },
            )
            if run.status_code != 200:
                raise _dify_error(run, "Der Dify-CV-Workflow konnte nicht ausgeführt werden.")
            result = run.json()
    except httpx.RequestError as exception:
        raise ApplicationError(
            "Die lokale Dify-Instanz ist für den CV-Import nicht erreichbar.",
            code="dify_unavailable",
            status_code=503,
        ) from exception

    data = result.get("data") or {}
    if data.get("status") != "succeeded":
        raise ApplicationError(
            data.get("error") or "Der Dify-CV-Workflow ist fehlgeschlagen.",
            code="dify_cv_workflow_failed",
            status_code=502,
        )
    outputs = data.get("outputs") or {}
    return {
        "workflow_run_id": data.get("id") or result.get("workflow_run_id"),
        "status": data.get("status"),
        "import_id": outputs.get("import_id"),
        "suggestion_count": outputs.get("suggestion_count", 0),
    }
