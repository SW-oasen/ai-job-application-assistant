import hashlib
import re
from pathlib import PurePath

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.database.repositories.jobs import persist_imported_job
from app.parsers.html_to_markdown import html_to_document
from app.parsers.job_metadata import extract_job_metadata
from app.parsers.job_portals import normalize_job_document
from app.parsers.job_role import extract_job_role
from app.parsers.job_seniority import (
    ensure_seniority_requirement,
    extract_job_seniority,
)
from app.parsers.text_quality import assess_text_quality
from app.schemas.imports import HtmlImportResponse
from app.services.hybrid_job_extraction import extract_job_structure_hybrid
from app.services.job_extraction_review_integration import (
    review_job_extraction_if_configured,
    store_job_extraction_review_history,
)
from app.services.job_extraction_service import enrich_job_extraction

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

    return await import_html_content(
        _decode_html(content),
        filename=filename,
        content_hash=hashlib.sha256(content).hexdigest(),
    )


async def import_html_content(
    html: str,
    *,
    filename: str,
    source_url: str | None = None,
    content_hash: str | None = None,
    retrieval_method: str = "native_html",
) -> HtmlImportResponse:
    settings = get_settings()
    encoded = html.encode("utf-8")
    if len(encoded) > settings.html_import_max_bytes:
        raise ApplicationError(
            "The HTML document exceeds the maximum allowed size.",
            code="file_too_large",
            status_code=413,
            details={"max_bytes": settings.html_import_max_bytes},
        )
    if "<html" not in html[:10_000].lower() and "<!doctype html" not in html[:10_000].lower():
        raise ApplicationError(
            "The uploaded file is not recognizable HTML.",
            code="invalid_html",
            status_code=422,
        )

    document = html_to_document(html)
    normalized = normalize_job_document(
        document.markdown, title=document.title, source_url=source_url, raw_html=html
    )
    quality = assess_text_quality(
        document.plain_text,
        title=document.title,
        minimum_length=settings.url_import_min_text_length,
    )
    warnings = list(quality.warnings)
    if document.related_jobs_removed and not quality.sufficient:
        warnings.append("job_description_not_found")
    response = HtmlImportResponse(
        success=quality.sufficient,
        filename=filename,
        title=normalized.title,
        markdown=normalized.markdown,
        text_length=quality.text_length,
        content_hash=content_hash or hashlib.sha256(encoded).hexdigest(),
        warnings=warnings,
    )
    if not quality.sufficient:
        return response

    structure = await extract_job_structure_hybrid(normalized.markdown)
    extraction = await enrich_job_extraction(
        content=normalized.markdown,
        metadata=extract_job_metadata(
            normalized.markdown, source_filename=filename, source_url=source_url
        ),
        activities=structure.activities,
        requirements=structure.requirements,
        source_filename=filename,
        source_url=source_url,
    )
    seniority = extract_job_seniority(normalized.markdown)
    job_role = extract_job_role(
        extraction.metadata.get("title") or normalized.title, normalized.markdown
    )
    reviewed = await review_job_extraction_if_configured(
        content=normalized.markdown,
        metadata=extraction.metadata,
        activities=extraction.activities,
        requirements=extraction.requirements,
    )
    requirements = ensure_seniority_requirement(reviewed.requirements, seniority)
    response.warnings.extend(
        warning for warning in extraction.warnings if warning not in response.warnings
    )
    persisted = await persist_imported_job(
        source_type="html",
        source_url=source_url,
        source_filename=filename,
        title=reviewed.metadata.get("title") or normalized.title,
        raw_content=html,
        normalized_content=normalized.markdown,
        content_hash=response.content_hash,
        retrieval_method=retrieval_method,
        warnings=response.warnings,
        metadata_override=reviewed.metadata,
        extracted_json={
            "semantic_metadata": extraction.metadata_details,
            "activities": reviewed.activities,
            "requirements": requirements,
            "seniority": seniority,
            "role": job_role,
        },
        activities=reviewed.activities,
        requirements=requirements,
    )
    response.job_id = persisted.job_id
    response.duplicate = persisted.duplicate
    if persisted.job_id and reviewed.review_results:
        await store_job_extraction_review_history(
            job_id=persisted.job_id,
            original_metadata=extraction.metadata,
            original_activities=structure.activities,
            original_requirements=structure.requirements,
            reviewed=reviewed,
        )
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
