from fastapi import APIRouter, File, Form, UploadFile

from app.core.errors import ApplicationError
from app.schemas.imports import (
    HtmlImportResponse,
    PdfImportResponse,
    UrlImportRequest,
    UrlImportResponse,
)
from app.services.html_import_service import import_html
from app.services.pdf_import_service import import_pdf
from app.services.url_import_service import import_url

router = APIRouter(prefix="/imports", tags=["imports"])

CONTROLLED_URL_IMPORT_ERRORS = {
    "browser_import_failed",
    "browser_timeout",
    "source_http_error",
    "source_unavailable",
}


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
