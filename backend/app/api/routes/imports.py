import ipaddress
from pathlib import PurePath
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, File, Form, Header, UploadFile

from app.core.errors import ApplicationError
from app.schemas.imports import (
    BrowserCaptureRequest,
    HtmlImportResponse,
    JobReimportResponse,
    PdfImportResponse,
    UrlImportRequest,
    UrlImportResponse,
)
from app.services.html_import_service import import_html, import_html_content
from app.services.job_reimport_service import reimport_job
from app.services.pdf_import_service import import_pdf
from app.services.url_import_service import import_url

router = APIRouter(prefix="/imports", tags=["imports"])

CONTROLLED_URL_IMPORT_ERRORS = {
    "browser_import_failed",
    "browser_timeout",
    "source_http_error",
    "source_unavailable",
}


def _is_public_browser_source(source_url: str) -> bool:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").lower().rstrip(".")
    if (
        parsed.scheme not in {"http", "https"}
        or not host
        or parsed.username
        or parsed.password
        or host == "localhost"
        or host.endswith((".localhost", ".local", ".internal"))
    ):
        return False
    try:
        return ipaddress.ip_address(host).is_global
    except ValueError:
        return True


@router.post("/jobs/{job_id}/reimport", response_model=JobReimportResponse)
async def reimport_stored_job(job_id: UUID) -> JobReimportResponse:
    return await reimport_job(job_id)


@router.post("/url", response_model=UrlImportResponse)
async def import_job_url(payload: UrlImportRequest) -> UrlImportResponse:
    try:
        return await import_url(payload)
    except ApplicationError as exception:
        if exception.code not in CONTROLLED_URL_IMPORT_ERRORS:
            raise
        details = exception.details if isinstance(exception.details, dict) else None
        source_status = (details or {}).get("source_status")
        message = exception.message
        if source_status in {403, 429}:
            message = (
                f"Die Quellseite blockiert den automatisierten Abruf (HTTP {source_status}). "
                "Bitte die Stellenanzeige im Browser als PDF speichern und per PDF importieren."
            )
        return UrlImportResponse(
            success=False,
            source_url=payload.url,
            retrieval_method="browser" if payload.force_browser else "http",
            title=None,
            raw_html="",
            markdown="",
            content_hash="",
            text_length=0,
            quality_sufficient=False,
            browser_fallback_recommended=not payload.force_browser,
            warnings=[exception.code],
            error={
                "code": exception.code,
                "message": message,
                "details": details,
            },
        )


@router.post("/pdf", response_model=PdfImportResponse)
async def import_job_pdf(
    file: UploadFile = File(...),
    replace_existing: bool = Form(False),
) -> PdfImportResponse:
    return await import_pdf(file, replace_existing=replace_existing)


@router.post("/html", response_model=HtmlImportResponse)
async def import_job_html(file: UploadFile = File(...)) -> HtmlImportResponse:
    return await import_html(file)


@router.post("/browser-capture", response_model=HtmlImportResponse)
async def import_browser_capture(
    payload: BrowserCaptureRequest,
    x_browser_capture: str | None = Header(default=None),
) -> HtmlImportResponse:
    if x_browser_capture != "receiver-v1":
        raise ApplicationError(
            "Browser capture must be submitted by the local receiver page.",
            code="browser_capture_forbidden",
            status_code=403,
        )
    parsed = urlparse(payload.source_url)
    if not _is_public_browser_source(payload.source_url):
        raise ApplicationError(
            "This website is not enabled for browser capture.",
            code="browser_capture_source_forbidden",
            status_code=422,
        )
    filename = PurePath(parsed.path).name or f"{parsed.hostname}-job"
    return await import_html_content(
        payload.html,
        filename=f"{filename}.html",
        source_url=payload.source_url,
        retrieval_method="browser_capture",
    )
