import hashlib
import os
import tempfile
import uuid
from datetime import datetime
from pathlib import Path, PurePath

from sqlalchemy import select

from app.core.config import get_settings
from app.core.errors import ApplicationError
from app.database.models import Application, ApplicationFile
from app.database.session import get_session_factory

PDF_CONTENT_TYPES = {"application/pdf", "application/octet-stream"}


def _session_factory():
    factory = get_session_factory()
    if factory is None:
        raise ApplicationError(
            "Application file storage requires a configured database.",
            code="database_not_configured",
            status_code=503,
        )
    return factory


def _safe_original_filename(filename: str | None) -> str:
    name = PurePath((filename or "document.pdf").replace("\\", "/")).name.strip()
    if not name or name in {".", ".."}:
        name = "document.pdf"
    return name[:500]


def storage_path(storage_key: str) -> Path:
    root = get_settings().application_documents_path.resolve()
    candidate = (root / storage_key).resolve()
    if candidate == root or root not in candidate.parents:
        raise ApplicationError(
            "Invalid application document storage key.",
            code="invalid_storage_key",
            status_code=500,
        )
    return candidate


def remove_stored_files(storage_keys: list[str]) -> None:
    for storage_key in storage_keys:
        path = storage_path(storage_key)
        path.unlink(missing_ok=True)
        try:
            path.parent.rmdir()
        except OSError:
            pass


def _file_dict(item: ApplicationFile) -> dict:
    return {
        "id": str(item.id),
        "application_id": str(item.application_id),
        "document_type": item.document_type,
        "original_filename": item.original_filename,
        "mime_type": item.mime_type,
        "file_size": item.file_size,
        "sha256": item.sha256,
        "submitted_at": item.submitted_at,
        "created_at": item.created_at,
    }


async def store_application_file(
    application_id,
    *,
    document_type: str,
    filename: str | None,
    content_type: str | None,
    content: bytes,
    submitted_at: datetime | None,
) -> dict:
    settings = get_settings()
    original_filename = _safe_original_filename(filename)
    if content_type not in PDF_CONTENT_TYPES or not original_filename.lower().endswith(".pdf"):
        raise ApplicationError(
            "Only PDF application documents are supported.",
            code="unsupported_application_file",
            status_code=415,
        )
    if not content or not content.startswith(b"%PDF-"):
        raise ApplicationError(
            "The uploaded file is not a valid PDF.",
            code="invalid_application_pdf",
            status_code=422,
        )
    if len(content) > settings.application_document_max_bytes:
        raise ApplicationError(
            "The application document exceeds the allowed file size.",
            code="application_file_too_large",
            status_code=413,
        )

    file_id = uuid.uuid4()
    storage_key = f"{application_id}/{file_id}.pdf"
    target = storage_path(storage_key)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise ApplicationError(
            "The application document storage is not writable.",
            code="application_storage_unavailable",
            status_code=503,
        ) from error
    temporary_path: Path | None = None

    async with _session_factory()() as session:
        if await session.get(Application, application_id) is None:
            raise ApplicationError(
                "Application not found.",
                code="application_not_found",
                status_code=404,
            )
        try:
            with tempfile.NamedTemporaryFile(
                dir=target.parent,
                prefix=f".{file_id}-",
                suffix=".tmp",
                delete=False,
            ) as temporary:
                temporary.write(content)
                temporary.flush()
                os.fsync(temporary.fileno())
                temporary_path = Path(temporary.name)
            os.replace(temporary_path, target)
            temporary_path = None

            item = ApplicationFile(
                id=file_id,
                application_id=application_id,
                document_type=document_type,
                storage_key=storage_key,
                original_filename=original_filename,
                mime_type="application/pdf",
                file_size=len(content),
                sha256=hashlib.sha256(content).hexdigest(),
                submitted_at=submitted_at,
            )
            session.add(item)
            await session.commit()
            await session.refresh(item)
            return _file_dict(item)
        except Exception:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            target.unlink(missing_ok=True)
            raise


async def list_application_files(application_id) -> list[dict]:
    async with _session_factory()() as session:
        if await session.get(Application, application_id) is None:
            raise ApplicationError(
                "Application not found.",
                code="application_not_found",
                status_code=404,
            )
        items = (
            await session.scalars(
                select(ApplicationFile)
                .where(ApplicationFile.application_id == application_id)
                .order_by(ApplicationFile.created_at.desc())
            )
        ).all()
        return [_file_dict(item) for item in items]


async def get_application_file(application_id, file_id) -> tuple[Path, str]:
    async with _session_factory()() as session:
        item = await session.get(ApplicationFile, file_id)
        if item is None or item.application_id != application_id:
            raise ApplicationError(
                "Application file not found.",
                code="application_file_not_found",
                status_code=404,
            )
        path = storage_path(item.storage_key)
        if not path.is_file():
            raise ApplicationError(
                "The stored application file is missing.",
                code="application_file_missing",
                status_code=410,
            )
        return path, item.original_filename


async def delete_application_file(application_id, file_id) -> None:
    async with _session_factory()() as session:
        item = await session.get(ApplicationFile, file_id)
        if item is None or item.application_id != application_id:
            raise ApplicationError(
                "Application file not found.",
                code="application_file_not_found",
                status_code=404,
            )
        storage_key = item.storage_key
        await session.delete(item)
        await session.commit()
    remove_stored_files([storage_key])
