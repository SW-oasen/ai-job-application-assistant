from uuid import uuid4


def test_profile_admin_page_is_available(client) -> None:
    response = client.get("/profiles/admin")

    assert response.status_code == 200
    assert "Profilverwaltung" in response.text
    assert '<details class="panel editor-shell" id="editorDetails">' in response.text
    assert "CV-PDF über Dify importieren" in response.text
    assert 'id="openCvPdfImport">CV-PDF importieren' in response.text
    assert 'type="button" id="cancelProfile">Abbrechen' in response.text
    assert 'aria-label="Profil-ID"' not in response.text
    assert "ID kopieren" not in response.text
    assert "Konfliktauflösung" in response.text
    assert "Bestehenden Eintrag behalten" in response.text
    assert 'id="careerGoal"' in response.text
    assert 'id="targetRoles"' in response.text
    assert 'id="preferredWorkModels"' in response.text
    assert 'id="dealBreakers"' in response.text
    assert "Portfolio-Projekte" in response.text
    assert 'id="portfolioImportForm"' in response.text


def test_list_profiles_uses_service(client, monkeypatch) -> None:
    async def fake_list():
        return [{"id": str(uuid4()), "display_name": "Main Profile", "revision": 1}]

    monkeypatch.setattr("app.api.routes.profile.list_profiles", fake_list)
    response = client.get("/profiles")

    assert response.status_code == 200
    assert response.json()[0]["display_name"] == "Main Profile"


def test_skill_taxonomy_exposes_stable_dropdown_values(client) -> None:
    response = client.get("/profiles/taxonomy/skills")

    assert response.status_code == 200
    assert "programming_languages" in {
        item["value"] for item in response.json()["categories"]
    }
    assert [item["value"] for item in response.json()["levels"]] == [
        "basic",
        "intermediate",
        "advanced",
        "expert",
    ]


def test_create_skill_uses_validated_contract(client, monkeypatch) -> None:
    profile_id = uuid4()

    async def fake_create(received_profile_id, resource_type, payload):
        return {
            "id": str(uuid4()),
            "profile_id": str(received_profile_id),
            "canonical_name": payload.canonical_name,
            "resource_type": resource_type,
        }

    monkeypatch.setattr("app.api.routes.profile.create_resource", fake_create)
    response = client.post(
        f"/profiles/{profile_id}/skills",
        json={
            "canonical_name": "Python",
            "category": "programming_languages",
            "localizations": [
                {"language": "de", "title": "Python"},
                {"language": "en", "title": "Python"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["canonical_name"] == "Python"
    assert response.json()["resource_type"] == "skills"


def test_structured_portfolio_import_uses_review_service(client, monkeypatch) -> None:
    profile_id = uuid4()

    async def fake_import(received_profile_id, payload):
        return {
            "profile_id": str(received_profile_id),
            "source_filename": payload.source_name,
            "projects": payload.projects,
        }

    monkeypatch.setattr(
        "app.api.routes.profile.create_structured_portfolio_import",
        fake_import,
    )
    response = client.post(
        f"/profiles/{profile_id}/portfolio-imports/structured",
        json={
            "source_name": "GitHub Portfolio",
            "source_language": "de",
            "projects": [{"name": "Application Assistant"}],
        },
    )

    assert response.status_code == 200
    assert response.json()["source_filename"] == "GitHub Portfolio"
    assert response.json()["projects"][0]["name"] == "Application Assistant"


def test_portfolio_javascript_import_uses_source_parser(client, monkeypatch) -> None:
    profile_id = uuid4()

    async def fake_import(received_profile_id, payload):
        return {
            "profile_id": str(received_profile_id),
            "source_filename": payload.source_name,
            "export_name": payload.export_name,
        }

    monkeypatch.setattr(
        "app.api.routes.profile.create_portfolio_source_import",
        fake_import,
    )
    response = client.post(
        f"/profiles/{profile_id}/portfolio-imports/source",
        json={
            "source_name": "projects.js",
            "source_content": "const PROJECTS = [];",
        },
    )

    assert response.status_code == 200
    assert response.json()["export_name"] == "PROJECTS"


def test_delete_profile_resource_uses_service(client, monkeypatch) -> None:
    profile_id = uuid4()
    item_id = uuid4()
    received = {}

    async def fake_delete(received_profile_id, resource_type, received_item_id):
        received.update(
            profile_id=received_profile_id,
            resource_type=resource_type,
            item_id=received_item_id,
        )

    monkeypatch.setattr("app.api.routes.profile.delete_resource", fake_delete)
    response = client.delete(f"/profiles/{profile_id}/skills/{item_id}")

    assert response.status_code == 204
    assert received == {
        "profile_id": profile_id,
        "resource_type": "skills",
        "item_id": item_id,
    }


def test_profile_rejects_unsupported_language(client) -> None:
    response = client.post(
        "/profiles",
        json={"display_name": "Test Profile", "default_language": "fr"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_profile_accepts_structured_career_goals(client, monkeypatch) -> None:
    received = {}

    async def fake_create(payload):
        received.update(payload.model_dump())
        return {"id": str(uuid4()), **payload.model_dump(exclude={"change_reason"})}

    monkeypatch.setattr("app.api.routes.profile.create_profile", fake_create)
    response = client.post(
        "/profiles",
        json={
            "display_name": "Data Profile",
            "career_goal": "Datenprodukte mit messbarer Wirkung entwickeln.",
            "target_roles": [" Data Scientist ", "data scientist", "ML Engineer"],
            "target_industries": ["Energie"],
            "target_locations": ["Berlin"],
            "preferred_work_models": ["remote", "hybrid"],
            "preferred_employment_types": ["permanent"],
            "deal_breakers": ["Reine Vertriebsrolle"],
        },
    )

    assert response.status_code == 200
    assert received["target_roles"] == ["Data Scientist", "ML Engineer"]
    assert response.json()["preferred_work_models"] == ["remote", "hybrid"]


def test_profile_rejects_unknown_work_model(client) -> None:
    response = client.post(
        "/profiles",
        json={"display_name": "Test", "preferred_work_models": ["flexible"]},
    )

    assert response.status_code == 422


def test_create_cv_import_uses_review_contract(client, monkeypatch) -> None:
    profile_id = uuid4()

    async def fake_create(received_profile_id, payload):
        return {
            "id": str(uuid4()),
            "profile_id": str(received_profile_id),
            "source_filename": payload.source_filename,
            "suggestions": [
                {
                    "resource_type": item.resource_type,
                    "proposed_data": item.proposed_data,
                }
                for item in payload.suggestions
            ],
        }

    monkeypatch.setattr("app.api.routes.profile.create_cv_import", fake_create)
    response = client.post(
        f"/profiles/{profile_id}/cv-imports",
        json={
            "source_filename": "lebenslauf.pdf",
            "source_language": "de",
            "suggestions": [
                {
                    "resource_type": "skills",
                    "proposed_data": {
                        "canonical_name": "Python",
                        "category": "programming_languages",
                    },
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["source_filename"] == "lebenslauf.pdf"
    assert response.json()["suggestions"][0]["resource_type"] == "skills"


def test_cv_import_rejects_unknown_resource_type(client) -> None:
    response = client.post(
        f"/profiles/{uuid4()}/cv-imports",
        json={
            "source_filename": "cv.pdf",
            "suggestions": [
                {
                    "resource_type": "profile_text",
                    "proposed_data": {"summary": "job-specific"},
                }
            ],
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_cv_pdf_import_calls_dify_for_selected_profile(client, monkeypatch) -> None:
    profile_id = uuid4()
    received = {}

    async def fake_import(**kwargs):
        received.update(kwargs)
        return {
            "workflow_run_id": "run-1",
            "status": "succeeded",
            "import_id": "import-1",
            "suggestion_count": 7,
        }

    monkeypatch.setattr("app.api.routes.profile.import_cv_pdf_with_dify", fake_import)
    response = client.post(
        f"/profiles/{profile_id}/cv-imports/pdf",
        files={"file": ("Lebenslauf.pdf", b"%PDF-1.4 test", "application/pdf")},
        data={"source_language": "de"},
    )

    assert response.status_code == 200
    assert response.json()["suggestion_count"] == 7
    assert received["profile_id"] == profile_id
    assert received["filename"] == "Lebenslauf.pdf"
    assert received["source_language"] == "de"


def test_cv_pdf_import_rejects_non_pdf(client) -> None:
    response = client.post(
        f"/profiles/{uuid4()}/cv-imports/pdf",
        files={"file": ("cv.txt", b"not a pdf", "text/plain")},
        data={"source_language": "de"},
    )

    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_cv_file"
