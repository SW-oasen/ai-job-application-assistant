from uuid import uuid4


def test_create_application_uses_service(client, monkeypatch) -> None:
    job_id, profile_id, application_id = uuid4(), uuid4(), uuid4()

    async def fake_create(payload):
        assert payload.job_id == job_id
        assert payload.profile_id == profile_id
        assert payload.status == "applied"
        assert payload.portal_name == "LinkedIn"
        return {"application": {"id": str(application_id)}, "events": []}

    monkeypatch.setattr(
        "app.api.routes.applications.create_application",
        fake_create,
    )
    response = client.post(
        "/applications",
        json={
            "job_id": str(job_id),
            "profile_id": str(profile_id),
            "status": "applied",
            "channel": "job_portal",
            "portal_name": "LinkedIn",
        },
    )

    assert response.status_code == 201
    assert response.json()["application"]["id"] == str(application_id)


def test_get_application_for_job_uses_profile(client, monkeypatch) -> None:
    job_id, profile_id = uuid4(), uuid4()

    async def fake_get(received_job_id, received_profile_id):
        assert received_job_id == job_id
        assert received_profile_id == profile_id
        return {"application": None, "events": []}

    monkeypatch.setattr(
        "app.api.routes.applications.get_application_for_job",
        fake_get,
    )
    response = client.get(
        f"/applications/by-job/{job_id}?profile_id={profile_id}"
    )

    assert response.status_code == 200
    assert response.json()["application"] is None


def test_update_application_validates_status(client) -> None:
    response = client.patch(
        f"/applications/{uuid4()}",
        json={"status": "made_up"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_application_event_validates_channel(client) -> None:
    response = client.post(
        f"/applications/{uuid4()}/events",
        json={"event_type": "communication", "channel": "carrier_pigeon"},
    )

    assert response.status_code == 422


def test_internal_forwarded_event_keeps_status_optional(client, monkeypatch) -> None:
    application_id = uuid4()

    async def fake_add(received_application_id, payload):
        assert received_application_id == application_id
        assert payload.event_type == "internal_forwarded"
        assert payload.status is None
        assert payload.contact_person == "Maria Mustermann"
        return {"id": str(uuid4()), "event_type": payload.event_type}

    monkeypatch.setattr(
        "app.api.routes.applications.add_application_event",
        fake_add,
    )
    response = client.post(
        f"/applications/{application_id}/events",
        json={
            "event_type": "internal_forwarded",
            "channel": "email",
            "contact_person": "Maria Mustermann",
            "note": "An die zuständigen Kollegen weitergeleitet.",
        },
    )

    assert response.status_code == 201
    assert response.json()["event_type"] == "internal_forwarded"


def test_update_application_event_uses_service(client, monkeypatch) -> None:
    application_id, event_id = uuid4(), uuid4()

    async def fake_update(received_application_id, received_event_id, payload):
        assert received_application_id == application_id
        assert received_event_id == event_id
        assert payload.status == "followed_up"
        return {"application": {"id": str(application_id)}, "events": []}

    monkeypatch.setattr(
        "app.api.routes.applications.update_application_event",
        fake_update,
    )
    response = client.patch(
        f"/applications/{application_id}/events/{event_id}",
        json={
            "status": "followed_up",
            "occurred_at": "2026-07-27T12:00:00Z",
            "channel": "email",
            "note": "Nachgefragt",
        },
    )

    assert response.status_code == 200
    assert response.json()["application"]["id"] == str(application_id)


def test_delete_application_event_uses_service(client, monkeypatch) -> None:
    application_id, event_id = uuid4(), uuid4()

    async def fake_delete(received_application_id, received_event_id):
        assert received_application_id == application_id
        assert received_event_id == event_id

    monkeypatch.setattr(
        "app.api.routes.applications.delete_application_event",
        fake_delete,
    )
    response = client.delete(
        f"/applications/{application_id}/events/{event_id}"
    )

    assert response.status_code == 204
    assert response.content == b""
