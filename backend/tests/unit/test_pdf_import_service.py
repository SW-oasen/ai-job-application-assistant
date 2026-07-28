from io import BytesIO
from types import SimpleNamespace

import pytest
from starlette.datastructures import Headers, UploadFile

from app.importers.mineru_client import MinerUResult
from app.services import pdf_import_service


def pdf_upload(filename: str = "job.pdf") -> UploadFile:
    return UploadFile(
        file=BytesIO(b"%PDF-1.4 test"),
        filename=filename,
        headers=Headers({"content-type": "application/pdf"}),
    )


@pytest.mark.asyncio
async def test_uses_native_text_without_mineru(monkeypatch) -> None:
    monkeypatch.setattr(
        pdf_import_service,
        "extract_pdf_text",
        lambda content: "Data Engineer " * 50,
    )

    result = await pdf_import_service.import_pdf(pdf_upload())

    assert result.extraction_method == "native_pdf"
    assert result.mineru_task_id is None
    assert result.content_hash


@pytest.mark.asyncio
async def test_uses_mineru_for_insufficient_native_text(monkeypatch) -> None:
    monkeypatch.setattr(pdf_import_service, "extract_pdf_text", lambda content: "")

    class FakeMinerUClient:
        def __init__(self, **kwargs) -> None:
            pass

        async def parse_pdf(self, *, content: bytes, filename: str) -> MinerUResult:
            return MinerUResult(markdown="# OCR result", task_id="task-42")

    monkeypatch.setattr(pdf_import_service, "MinerUClient", FakeMinerUClient)

    result = await pdf_import_service.import_pdf(pdf_upload("../../unsafe name.pdf"))

    assert result.extraction_method == "mineru"
    assert result.filename == "unsafe_name.pdf"
    assert result.mineru_task_id == "task-42"
    assert "mineru_fallback_used" in result.warnings


@pytest.mark.asyncio
async def test_forwards_explicit_reimport_to_repository(monkeypatch) -> None:
    monkeypatch.setattr(
        pdf_import_service,
        "extract_pdf_text",
        lambda content: "Data Engineer " * 50,
    )
    captured = {}

    async def fake_persist(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            job_id="91e5c97c-9102-422d-be19-9c14c82ea81d",
            duplicate=False,
            reimported=True,
        )

    monkeypatch.setattr(pdf_import_service, "persist_imported_job", fake_persist)

    result = await pdf_import_service.import_pdf(
        pdf_upload(),
        replace_existing=True,
    )

    assert captured["replace_existing"] is True
    assert result.reimported is True
