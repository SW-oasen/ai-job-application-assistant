from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.errors import ApplicationError
from app.services.application_file_service import storage_path, store_application_file


def test_upload_application_pdf_uses_service(client, monkeypatch) -> None:
    application_id, file_id = uuid4(), uuid4()

    async def fake_store(received_application_id, **values):
        assert received_application_id == application_id
        assert values["document_type"] == "resume"
        assert values["filename"] == "Lebenslauf.pdf"
        assert values["content"].startswith(b"%PDF-")
        assert values["submitted_at"].year == 2026
        return {"id": str(file_id), "application_id": str(application_id)}

    monkeypatch.setattr(
        "app.api.routes.application_files.store_application_file",
        fake_store,
    )
    response = client.post(
        f"/applications/{application_id}/files",
        data={"document_type": "resume", "submitted_at": "2026-07-28T12:00:00Z"},
        files={"file": ("Lebenslauf.pdf", b"%PDF-1.7\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["id"] == str(file_id)


def test_upload_rejects_unknown_document_type(client) -> None:
    response = client.post(
        f"/applications/{uuid4()}/files",
        data={"document_type": "invented"},
        files={"file": ("file.pdf", b"%PDF-1.7\n%%EOF", "application/pdf")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_list_application_files_uses_service(client, monkeypatch) -> None:
    application_id = uuid4()

    async def fake_list(received_application_id):
        assert received_application_id == application_id
        return [{"id": str(uuid4()), "document_type": "cover_letter"}]

    monkeypatch.setattr(
        "app.api.routes.application_files.list_application_files",
        fake_list,
    )
    response = client.get(f"/applications/{application_id}/files")

    assert response.status_code == 200
    assert response.json()[0]["document_type"] == "cover_letter"


def test_delete_application_file_uses_service(client, monkeypatch) -> None:
    application_id, file_id = uuid4(), uuid4()

    async def fake_delete(received_application_id, received_file_id):
        assert received_application_id == application_id
        assert received_file_id == file_id

    monkeypatch.setattr(
        "app.api.routes.application_files.delete_application_file",
        fake_delete,
    )
    response = client.delete(f"/applications/{application_id}/files/{file_id}")

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_store_rejects_non_pdf_before_database_access() -> None:
    with pytest.raises(ApplicationError) as error:
        await store_application_file(
            uuid4(),
            document_type="resume",
            filename="resume.pdf",
            content_type="application/pdf",
            content=b"not a pdf",
            submitted_at=datetime.now(timezone.utc),
        )

    assert error.value.code == "invalid_application_pdf"


def test_storage_path_rejects_traversal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.application_file_service.get_settings",
        lambda: SimpleNamespace(application_documents_path=tmp_path),
    )

    with pytest.raises(ApplicationError) as error:
        storage_path("../outside.pdf")

    assert error.value.code == "invalid_storage_key"
