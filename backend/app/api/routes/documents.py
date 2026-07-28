from uuid import UUID

from fastapi import APIRouter

from app.schemas.documents import DocumentContextRequest, GeneratedDocumentCreate
from app.services.document_service import (
    list_generated_documents,
    prepare_document_context,
    store_generated_document,
)

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/document-context")
async def document_context(payload: DocumentContextRequest) -> dict:
    return await prepare_document_context(payload)


@router.post("/{application_id}/documents", status_code=201)
async def create_document(
    application_id: UUID,
    payload: GeneratedDocumentCreate,
) -> dict:
    return await store_generated_document(application_id, payload)


@router.get("/{application_id}/documents")
async def documents(application_id: UUID) -> list[dict]:
    return await list_generated_documents(application_id)
