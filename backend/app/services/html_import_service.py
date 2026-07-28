import hashlib
import re
from pathlib import PurePath

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.database.repositories.jobs import persist_imported_job
from app.parsers.html_to_markdown import html_to_document
from app.parsers.text_quality import assess_text_quality
from app.schemas.imports import HtmlImportResponse
from app.services.semantic_metadata_service import enrich_job_metadata

SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")
HTML_CONTENT_TYPES = {
    "text/html",
    "application/xhtml+xml",
    "application/octet-stream",
}


async def import_html(file: UploadFile) -> HtmlImportResponse:
    settings = get_settings()
    filename = _safe_filename(file.filename)
    if file.content_type not in HTML_CONTENT_TYPES:
        raise ApplicationError(
            "Only HTML uploads are supported.",
            code="unsupported_file_type",
            status_code=415,
        )

    content = await file.read(settings.html_import_max_bytes + 1)
    await file.close()
    if len(content) > settings.html_import_max_bytes:
        raise ApplicationError(
            "The HTML file exceeds the maximum allowed upload size.",
            code="file_too_large",
            status_code=413,
            details={"max_bytes": settings.html_import_max_bytes},
        )

    html = _decode_html(content)
    if "<html" not in html[:10_000].lower() and "<!doctype html" not in html[:10_000].lower():
        raise ApplicationError(
            "The uploaded file is not recognizable HTML.",
            code="invalid_html",
            status_code=422,
        )

    document = html_to_document(html)
    quality = assess_text_quality(
        document.plain_text,
        title=document.title,
        minimum_length=settings.url_import_min_text_length,
    )
    response = HtmlImportResponse(
        success=quality.sufficient,
        filename=filename,
        title=document.title,
        markdown=document.markdown,
        text_length=quality.text_length,
        content_hash=hashlib.sha256(content).hexdigest(),
        warnings=quality.warnings,
    )
    if not quality.sufficient:
        return response

    semantic = await enrich_job_metadata(
        document.markdown,
        source_filename=filename,
    )
    response.warnings.extend(
        warning for warning in semantic.warnings if warning not in response.warnings
    )
    persisted = await persist_imported_job(
        source_type="html",
        source_url=None,
        source_filename=filename,
        title=document.title,
        raw_content=html,
        normalized_content=document.markdown,
        content_hash=response.content_hash,
        retrieval_method="native_html",
        warnings=response.warnings,
        metadata_override=semantic.metadata,
        extracted_json=(
            {"semantic_metadata": semantic.details}
            if semantic.details
            else None
        ),
    )
    response.job_id = persisted.job_id
    response.duplicate = persisted.duplicate
    return response


def _decode_html(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1252", errors="replace")


def _safe_filename(filename: str | None) -> str:
    basename = PurePath((filename or "upload.html").replace("\\", "/")).name
    sanitized = SAFE_FILENAME_PATTERN.sub("_", basename).strip("._")
    if not sanitized:
        sanitized = "upload.html"
    if not sanitized.lower().endswith((".html", ".htm")):
        sanitized = f"{sanitized}.html"
    return sanitized[:200]
