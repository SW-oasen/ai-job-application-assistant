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
    assert "Bewerbungsdashboard" in response.text


def test_manage_page(client) -> None:
    response = client.get("/manage")

    assert response.status_code == 200
    assert "Zentralverwaltung" in response.text
    assert "Datei-Fallback" in response.text


def test_job_detail_page(client) -> None:
    response = client.get("/jobs/00000000-0000-0000-0000-000000000000")

    assert response.status_code == 200
    assert "Jobdetails" in response.text
    assert "Matching" in response.text
    assert '<details class="inline-editor" id="applicationEditor">' in response.text
    assert "Bewerbungsstatus und Unterlagen bearbeiten" in response.text


def test_jobs_page(client) -> None:
    response = client.get("/jobs")

    assert response.status_code == 200
    assert "Jobs und Bewerbungen" in response.text
