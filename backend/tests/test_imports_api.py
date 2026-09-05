from app.core.errors import ApplicationError
from app.schemas.imports import (
    HtmlImportResponse,
    JobReimportResponse,
    PdfImportResponse,
    UrlImportResponse,
)


def test_import_url_returns_normalized_response(client, monkeypatch) -> None:
    async def fake_import(payload):
        return UrlImportResponse(
            success=True,
            source_url=payload.url,
            retrieval_method="http",
            title="Data Engineer",
            raw_html="<h1>Data Engineer</h1>",
            markdown="# Data Engineer",
            content_hash="a" * 64,
            text_length=13,
            quality_sufficient=False,
            browser_fallback_recommended=True,
            warnings=["content_below_minimum_length"],
        )

    monkeypatch.setattr("app.api.routes.imports.import_url", fake_import)
    response = client.post(
        "/imports/url",
        json={"url": "https://example.com/job", "force_browser": False},
    )

    assert response.status_code == 200
    assert response.json()["source_type"] == "url"
    assert response.json()["browser_fallback_recommended"] is True


def test_import_url_rejects_unknown_fields(client) -> None:
    response = client.post(
        "/imports/url",
        json={"url": "https://example.com/job", "unexpected": True},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert response.json()["error"]["request_id"]


def test_blocked_source_returns_controlled_failure(client, monkeypatch) -> None:
    async def blocked_import(payload):
        raise ApplicationError(
            "The source returned HTTP 403 in the browser.",
            code="source_http_error",
            status_code=502,
            details={"source_status": 403},
        )

    monkeypatch.setattr("app.api.routes.imports.import_url", blocked_import)
    response = client.post(
        "/imports/url",
        json={"url": "https://example.com/job", "force_browser": True},
    )

    assert response.status_code == 200
    assert response.json()["success"] is False
    assert response.json()["job_id"] is None
    assert response.json()["error"]["code"] == "source_http_error"
    assert "PDF" in response.json()["error"]["message"]


def test_pdf_import_rejects_non_pdf(client) -> None:
    response = client.post(
        "/imports/pdf",
        files={"file": ("job.txt", b"not a pdf", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_file_type"


def test_pdf_import_forwards_replace_existing(client, monkeypatch) -> None:
    captured = {}

    async def fake_import(file, *, replace_existing=False):
        captured["replace_existing"] = replace_existing
        return PdfImportResponse(
            success=True,
            filename="job.pdf",
            extraction_method="native_pdf",
            markdown="Data Engineer",
            text_length=13,
            content_hash="a" * 64,
            warnings=[],
            job_id="91e5c97c-9102-422d-be19-9c14c82ea81d",
            reimported=True,
        )

    monkeypatch.setattr("app.api.routes.imports.import_pdf", fake_import)
    response = client.post(
        "/imports/pdf",
        files={"file": ("job.pdf", b"%PDF-1.4 test", "application/pdf")},
        data={"replace_existing": "true"},
    )

    assert response.status_code == 200
    assert captured["replace_existing"] is True
    assert response.json()["reimported"] is True


def test_reimports_stored_job_without_upload(client, monkeypatch) -> None:
    job_id = "91e5c97c-9102-422d-be19-9c14c82ea81d"

    async def fake_reimport(received_job_id):
        assert str(received_job_id) == job_id
        return JobReimportResponse(
            job_id=received_job_id,
            source_type="pdf",
            retrieval_method="native_pdf",
            language="de",
            warnings=[],
        )

    monkeypatch.setattr("app.api.routes.imports.reimport_job", fake_reimport)
    response = client.post(f"/imports/jobs/{job_id}/reimport")

    assert response.status_code == 200
    assert response.json()["reimported"] is True
    assert response.json()["language"] == "de"


def test_html_import_accepts_single_file_document(client) -> None:
    html = (
        "<!doctype html><html><head><title>Data Analyst</title>"
        "<script>throw new Error('must not run')</script></head><body><main>"
        "<h1>Data Analyst</h1><p>"
        + ("Analyse Daten SQL Python Power BI Berichte. " * 30)
        + "</p></main></body></html>"
    )
    response = client.post(
        "/imports/html",
        files={"file": ("indeed-singlefile.html", html.encode(), "text/html")},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["source_type"] == "html"
    assert "must not run" not in response.json()["markdown"]


def test_html_import_rejects_non_html(client) -> None:
    response = client.post(
        "/imports/html",
        files={"file": ("job.html", b"plain text only", "text/html")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_html"


def test_browser_capture_imports_rendered_public_job_page(client, monkeypatch) -> None:
    captured = {}

    async def fake_import(html, **kwargs):
        captured["html"] = html
        captured.update(kwargs)
        return HtmlImportResponse(
            success=True,
            filename="viewjob.html",
            title="Data Analyst",
            markdown="Data Analyst",
            text_length=12,
            content_hash="a" * 64,
            warnings=[],
            job_id="91e5c97c-9102-422d-be19-9c14c82ea81d",
        )

    monkeypatch.setattr(
        "app.api.routes.imports.import_html_content",
        fake_import,
    )
    response = client.post(
        "/imports/browser-capture",
        headers={"X-Browser-Capture": "receiver-v1"},
        json={
            "source_url": "https://careers.example.com/jobs/data-analyst",
            "html": "<!doctype html><html><body>Data Analyst</body></html>",
        },
    )

    assert response.status_code == 200
    assert captured["source_url"] == "https://careers.example.com/jobs/data-analyst"
    assert captured["retrieval_method"] == "browser_capture"


def test_browser_capture_rejects_missing_receiver_header(client) -> None:
    response = client.post(
        "/imports/browser-capture",
        json={
            "source_url": "https://de.indeed.com/viewjob?jk=abc",
            "html": "<!doctype html><html><body>Data Analyst</body></html>",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "browser_capture_forbidden"


def test_browser_capture_allows_cors_preflight_from_job_portal(client) -> None:
    response = client.options(
        "/imports/browser-capture",
        headers={
            "Origin": "https://job.deloitte.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 204
    assert response.headers["access-control-allow-origin"] == "https://job.deloitte.com"
    assert "X-Browser-Capture" in response.headers["access-control-allow-headers"]


def test_browser_capture_rejects_local_source(client) -> None:
    response = client.post(
        "/imports/browser-capture",
        headers={"X-Browser-Capture": "receiver-v1"},
        json={
            "source_url": "http://127.0.0.1:9000/job",
            "html": "<!doctype html><html><body>Data Analyst</body></html>",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "browser_capture_source_forbidden"


def test_browser_capture_rejects_non_http_source(client) -> None:
    response = client.post(
        "/imports/browser-capture",
        headers={"X-Browser-Capture": "receiver-v1"},
        json={
            "source_url": "file:///tmp/job.html",
            "html": "<!doctype html><html><body>Data Analyst</body></html>",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "browser_capture_source_forbidden"
