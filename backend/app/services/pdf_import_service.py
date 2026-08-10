import hashlib
import re
from pathlib import PurePath

from fastapi import UploadFile

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.database.repositories.jobs import persist_imported_job
from app.importers.mineru_client import MinerUClient
from app.importers.pdf_importer import (
    extract_pdf_text,
    normalize_native_pdf_text,
    pdf_text_has_broken_glyphs,
    pdf_text_is_sufficient,
    rasterize_pdf,
)
from app.parsers.job_seniority import (
    ensure_seniority_requirement,
    extract_job_seniority,
)
from app.parsers.job_role import extract_job_role
from app.parsers.job_structure import extract_job_structure
from app.services.hybrid_job_extraction import extract_job_structure_hybrid
from app.schemas.imports import PdfImportResponse
from app.services.job_extraction_review_integration import (
    review_job_extraction_if_configured,
    store_job_extraction_review_history,
)
from app.services.semantic_metadata_service import enrich_job_metadata

SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


async def import_pdf(
    file: UploadFile,
    *,
    replace_existing: bool = False,
) -> PdfImportResponse:
    settings = get_settings()
    filename = _safe_filename(file.filename)
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise ApplicationError(
            "Only PDF uploads are supported.",
            code="unsupported_file_type",
            status_code=415,
        )

    content = await file.read(settings.pdf_import_max_bytes + 1)
    await file.close()
    if len(content) > settings.pdf_import_max_bytes:
        raise ApplicationError(
            "The PDF exceeds the maximum allowed upload size.",
            code="file_too_large",
            status_code=413,
            details={"max_bytes": settings.pdf_import_max_bytes},
        )
    if not content.startswith(b"%PDF-"):
        raise ApplicationError(
            "The uploaded file is not a valid PDF.",
            code="invalid_pdf",
            status_code=422,
        )

    content_hash = hashlib.sha256(content).hexdigest()
    text = extract_pdf_text(content)
    if pdf_text_is_sufficient(
        text,
        minimum_length=settings.pdf_import_min_text_length,
    ):
        text = normalize_native_pdf_text(text)
        response = PdfImportResponse(
            success=True,
            filename=filename,
            extraction_method="native_pdf",
            markdown=text,
            text_length=len(text),
            content_hash=content_hash,
            warnings=[],
        )
        return await _persist_response(response, replace_existing=replace_existing)

    mineru_content = content
    mineru_filename = filename
    warnings = ["native_pdf_text_insufficient", "mineru_fallback_used"]
    if pdf_text_has_broken_glyphs(text):
        mineru_content = rasterize_pdf(
            content,
            image_format=settings.pdf_raster_image_format,
            colorspace=settings.pdf_raster_colorspace,
            dpi=settings.pdf_raster_dpi,
            jpeg_quality=settings.pdf_raster_jpeg_quality,
            max_pages=settings.pdf_raster_max_pages,
        )
        mineru_filename = f"{PurePath(filename).stem}_rasterized.pdf"
        warnings = [
            "native_pdf_broken_text_layer",
            "pdf_rasterized_for_ocr",
            "mineru_fallback_used",
        ]

    mineru = MinerUClient(
        base_url=str(settings.mineru_base_url),
        timeout_seconds=settings.mineru_timeout_seconds,
        backend=settings.mineru_backend,
    )
    result = await mineru.parse_pdf(
        content=mineru_content,
        filename=mineru_filename,
    )
    response = PdfImportResponse(
        success=True,
        filename=filename,
        extraction_method="mineru",
        markdown=result.markdown,
        text_length=len(" ".join(result.markdown.split())),
        content_hash=content_hash,
        mineru_task_id=result.task_id,
        warnings=warnings,
    )
    return await _persist_response(response, replace_existing=replace_existing)


async def _persist_response(
    response: PdfImportResponse,
    *,
    replace_existing: bool = False,
) -> PdfImportResponse:
    semantic = await enrich_job_metadata(
        response.markdown,
        source_filename=response.filename,
    )
    structure = await extract_job_structure_hybrid(response.markdown)
    seniority = extract_job_seniority(response.markdown)
    job_role = extract_job_role(semantic.metadata.get("title"), response.markdown)
    reviewed = await review_job_extraction_if_configured(
        content=response.markdown,
        metadata=semantic.metadata,
        activities=structure.activities,
        requirements=structure.requirements,
    )
    requirements = ensure_seniority_requirement(reviewed.requirements, seniority)
    response.warnings.extend(
        warning for warning in semantic.warnings if warning not in response.warnings
    )
    persisted = await persist_imported_job(
        source_type="pdf",
        source_url=None,
        source_filename=response.filename,
        title=None,
        raw_content=None,
        normalized_content=response.markdown,
        content_hash=response.content_hash,
        retrieval_method=response.extraction_method,
        warnings=response.warnings,
        replace_existing=replace_existing,
        metadata_override=reviewed.metadata,
        extracted_json={
            "semantic_metadata": semantic.details,
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
    response.reimported = persisted.reimported
    if persisted.job_id and reviewed.review_results:
        await store_job_extraction_review_history(
            job_id=persisted.job_id,
            original_metadata=semantic.metadata,
            original_activities=structure.activities,
            original_requirements=structure.requirements,
            reviewed=reviewed,
        )
    return response


def _safe_filename(filename: str | None) -> str:
    basename = PurePath((filename or "upload.pdf").replace("\\", "/")).name
    sanitized = SAFE_FILENAME_PATTERN.sub("_", basename).strip("._")
    if not sanitized:
        sanitized = "upload.pdf"
    if not sanitized.lower().endswith(".pdf"):
        sanitized = f"{sanitized}.pdf"
    return sanitized[:200]
