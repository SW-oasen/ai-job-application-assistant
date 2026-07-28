from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, Response, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.schemas.application_files import DocumentType
from app.services.application_file_service import (
    delete_application_file,
    get_application_file,
    list_application_files,
    store_application_file,
)

router = APIRouter(prefix="/applications", tags=["application-files"])


@router.post("/{application_id}/files", status_code=201)
async def upload_application_file(
    application_id: UUID,
    file: Annotated[UploadFile, File()],
    document_type: Annotated[DocumentType, Form()],
    submitted_at: Annotated[datetime | None, Form()] = None,
) -> dict:
    content = await file.read(get_settings().application_document_max_bytes + 1)
    return await store_application_file(
        application_id,
        document_type=document_type,
        filename=file.filename,
        content_type=file.content_type,
        content=content,
        submitted_at=submitted_at,
    )


@router.get("/{application_id}/files")
async def application_files(application_id: UUID) -> list[dict]:
    return await list_application_files(application_id)


@router.get("/{application_id}/files/{file_id}/content")
async def application_file_content(application_id: UUID, file_id: UUID) -> FileResponse:
    path, filename = await get_application_file(application_id, file_id)
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.delete("/{application_id}/files/{file_id}", status_code=204)
async def remove_application_file(application_id: UUID, file_id: UUID) -> Response:
    await delete_application_file(application_id, file_id)
    return Response(status_code=204)
