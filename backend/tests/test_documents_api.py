from uuid import uuid4


def test_document_context_requires_database(client) -> None:
    response = client.post(
        "/applications/document-context",
        json={
            "job_id": str(uuid4()),
            "profile_id": str(uuid4()),
            "language": "de",
        },
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "database_not_configured"


def test_document_context_rejects_unsupported_language(client) -> None:
    response = client.post(
        "/applications/document-context",
        json={
            "job_id": str(uuid4()),
            "profile_id": str(uuid4()),
            "language": "fr",
        },
    )

    assert response.status_code == 422


def test_document_rejects_unknown_document_type(client) -> None:
    response = client.post(
        f"/applications/{uuid4()}/documents",
        json={
            "document_type": "invented",
            "language": "en",
            "content": "Draft",
        },
    )

    assert response.status_code == 422
