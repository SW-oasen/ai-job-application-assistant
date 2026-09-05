def test_health_returns_service_metadata(client) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "application-assistant-backend",
        "version": "0.1.0",
    }
    assert response.headers["X-Request-ID"]


def test_health_preserves_caller_request_id(client) -> None:
    response = client.get("/health", headers={"X-Request-ID": "dify-test-request"})

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "dify-test-request"


def test_home_page(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Bewerbungsassistent" in response.text
    assert 'href="/manage">Verwaltung</a>' in response.text
    assert 'href="/matching/admin"' not in response.text
    assert 'href="/jobs">' not in response.text


def test_manage_page(client) -> None:
    response = client.get("/manage")

    assert response.status_code == 200
    assert "Verwaltung" in response.text
    assert "Jobs und Bewerbungen" in response.text
    assert "Datei-Fallback" in response.text
    assert 'href="/browser-import"' in response.text
    assert "sourceName" not in response.text
    assert "importiert" in response.text


def test_job_detail_page(client) -> None:
    response = client.get("/jobs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 200
    assert "Jobdetails" in response.text
    assert 'id="archiveJob"' in response.text
    assert "Matching" in response.text
    assert '<details class="inline-editor" id="applicationEditor">' in response.text
    assert "Verlauf und Unterlagen bearbeiten" in response.text
    assert "Intern weitergeleitet" in response.text
    assert 'id="contactPerson"' in response.text
    assert 'id="matchingSummary"' in response.text
    assert "Qualifikations-Fit:" in response.text
    assert "Matching-Details anzeigen" in response.text
    assert "Matching starten" in response.text
    assert "Matching neu berechnen" in response.text
    assert 'request("/matching/run"' in response.text
    assert 'class="requirement-detail"' in response.text
    assert "Array.isArray(match.evidence)" in response.text
    assert "esc(item.evidence_text||\"\")" in response.text
    assert 'textContent=data.company||"Firma unbekannt"' in response.text
    assert "Erkannte Stellendetails" in response.text
    assert "<summary>Importierter Referenztext</summary>" in response.text


def test_browser_import_setup_page(client) -> None:
    response = client.get("/browser-import")

    assert response.status_code == 200
    assert "Browser-Import einrichten" in response.text
    assert "javascript:" in response.text
    assert "/imports/browser-capture" in response.text
    assert "beliebigen öffentlichen Jobportal" in response.text


def test_browser_import_receiver_page(client) -> None:
    response = client.get("/browser-import/receive")

    assert response.status_code == 200
    assert "application-assistant-ready" in response.text
    assert 'fetch("/imports/browser-capture"' in response.text
