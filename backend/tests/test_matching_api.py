from uuid import uuid4

from app.schemas.matching import MatchingContextResponse, MatchingResponse


def test_matching_endpoint_returns_summary(client, monkeypatch) -> None:
    job_id = uuid4()

    async def fake_evaluate(payload):
        return MatchingResponse(job_id=str(payload.job_id), matches=[], summary={})

    monkeypatch.setattr("app.api.routes.matching.evaluate_matching", fake_evaluate)
    response = client.post(
        "/matching/evaluate",
        json={
            "job_id": str(job_id),
            "requirements": [{"requirement": "Python"}],
            "evidence": [],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"job_id": str(job_id), "matches": [], "summary": {}}


def test_matching_endpoint_validates_job_id(client) -> None:
    response = client.post(
        "/matching/evaluate",
        json={"job_id": "not-a-uuid", "requirements": [{"requirement": "Python"}]},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_matching_admin_page_removed(client) -> None:
    response = client.get("/matching/admin")

    assert response.status_code == 404


def test_matching_jobs_uses_service(client, monkeypatch) -> None:
    job_id = uuid4()

    async def fake_jobs(profile_id=None, *, include_archived=False):
        assert profile_id is None
        assert include_archived is False
        return [{"id": str(job_id), "title": "AI Engineer"}]

    monkeypatch.setattr("app.api.routes.matching.list_matching_jobs", fake_jobs)
    response = client.get("/matching/jobs")

    assert response.status_code == 200
    assert response.json() == [{"id": str(job_id), "title": "AI Engineer"}]


def test_matching_jobs_can_include_archive(client, monkeypatch) -> None:
    async def fake_jobs(profile_id=None, *, include_archived=False):
        assert profile_id is None
        assert include_archived is True
        return []

    monkeypatch.setattr("app.api.routes.matching.list_matching_jobs", fake_jobs)
    response = client.get("/matching/jobs?include_archived=true")

    assert response.status_code == 200


def test_archive_and_restore_job_use_services(client, monkeypatch) -> None:
    job_id = uuid4()

    async def fake_archive(received_job_id, reason):
        assert received_job_id == job_id
        assert reason == "Geringer Ziel-Fit"
        return {"id": str(job_id), "archive_reason": reason}

    async def fake_restore(received_job_id):
        assert received_job_id == job_id
        return {"id": str(job_id), "archived_at": None}

    monkeypatch.setattr("app.api.routes.matching.archive_matching_job", fake_archive)
    monkeypatch.setattr("app.api.routes.matching.restore_matching_job", fake_restore)
    archived = client.post(
        f"/matching/jobs/{job_id}/archive",
        json={"reason": "Geringer Ziel-Fit"},
    )
    restored = client.post(f"/matching/jobs/{job_id}/restore")

    assert archived.status_code == 200
    assert archived.json()["archive_reason"] == "Geringer Ziel-Fit"
    assert restored.status_code == 200


def test_matching_job_detail_uses_service(client, monkeypatch) -> None:
    job_id = uuid4()

    async def fake_job(received_job_id):
        assert received_job_id == job_id
        return {"id": str(job_id), "title": "AI Engineer", "content": "Python"}

    monkeypatch.setattr("app.api.routes.matching.get_matching_job", fake_job)
    response = client.get(f"/matching/jobs/{job_id}")

    assert response.status_code == 200
    assert response.json()["content"] == "Python"


def test_job_review_history_uses_review_history_service(client, monkeypatch) -> None:
    job_id = uuid4()

    async def fake_history(*, subject_type, subject_id, review_type=None):
        assert subject_type == "job"
        assert subject_id == job_id
        assert review_type is None
        return [{"review_type": "job_extraction", "status": "accepted", "issues": []}]

    monkeypatch.setattr("app.api.routes.matching.list_review_history", fake_history)
    response = client.get(f"/matching/jobs/{job_id}/reviews")

    assert response.status_code == 200
    assert response.json()[0]["review_type"] == "job_extraction"


def test_edit_job_metadata_uses_service(client, monkeypatch) -> None:
    job_id = uuid4()

    async def fake_update(received_job_id, payload):
        assert received_job_id == job_id
        assert payload.title == "AI Engineer"
        assert payload.company == "Amoria Bond"
        assert payload.location == "Berlin Metropolitan Area"
        assert payload.contract_term == "unbefristet"
        assert payload.source_portal == "Indeed"
        return {"id": str(job_id), **payload.model_dump()}

    monkeypatch.setattr("app.api.routes.matching.update_job_metadata", fake_update)
    response = client.patch(
        f"/matching/jobs/{job_id}/metadata",
        json={
            "title": "AI Engineer",
            "company": "Amoria Bond",
            "location": "Berlin Metropolitan Area",
            "work_model": "Hybrid",
            "contract_term": "unbefristet",
            "source_portal": "Indeed",
        },
    )

    assert response.status_code == 200
    assert response.json()["company"] == "Amoria Bond"
    assert response.json()["contract_term"] == "unbefristet"
    assert response.json()["source_portal"] == "Indeed"


def test_edit_job_metadata_rejects_unsupported_language(client) -> None:
    response = client.patch(
        f"/matching/jobs/{uuid4()}/metadata",
        json={"language": "fr"},
    )

    assert response.status_code == 422


def test_delete_matching_job_uses_service(client, monkeypatch) -> None:
    job_id = uuid4()

    async def fake_delete(received_job_id):
        assert received_job_id == job_id

    monkeypatch.setattr("app.api.routes.matching.delete_matching_job", fake_delete)
    response = client.delete(f"/matching/jobs/{job_id}")

    assert response.status_code == 204
    assert response.content == b""


def test_stored_matching_results_use_job_and_profile(client, monkeypatch) -> None:
    job_id = uuid4()
    profile_id = uuid4()

    async def fake_results(received_job_id, received_profile_id):
        assert received_job_id == job_id
        assert received_profile_id == profile_id
        return {
            "job": {"id": str(job_id), "title": "AI Engineer"},
            "profile": {"id": str(profile_id), "display_name": "Main"},
            "matches": [],
            "summary": {},
        }

    monkeypatch.setattr("app.api.routes.matching.get_stored_matching", fake_results)
    response = client.get(
        f"/matching/results?job_id={job_id}&profile_id={profile_id}"
    )

    assert response.status_code == 200
    assert response.json()["profile"]["display_name"] == "Main"


def test_target_fit_uses_job_and_profile(client, monkeypatch) -> None:
    job_id = uuid4()
    profile_id = uuid4()

    async def fake_target_fit(received_job_id, received_profile_id):
        assert received_job_id == job_id
        assert received_profile_id == profile_id
        return {"level": "strong", "score": 90, "criteria": [], "exclusions": []}

    monkeypatch.setattr("app.api.routes.matching.get_target_fit", fake_target_fit)
    response = client.get(
        f"/matching/target-fit?job_id={job_id}&profile_id={profile_id}"
    )

    assert response.status_code == 200
    assert response.json()["score"] == 90


def test_matching_context_uses_job_and_profile_ids(client, monkeypatch) -> None:
    job_id = uuid4()
    profile_id = uuid4()

    async def fake_context(received_job_id, received_profile_id):
        assert received_job_id == job_id
        assert received_profile_id == profile_id
        return MatchingContextResponse(
            job_id=str(job_id),
            profile_id=str(profile_id),
            job_title="AI Engineer",
            job_language="de",
            job_content="Python und Machine Learning",
            evidence=[],
        )

    monkeypatch.setattr("app.api.routes.matching.get_matching_context", fake_context)
    response = client.get(
        f"/matching/context?job_id={job_id}&profile_id={profile_id}"
    )

    assert response.status_code == 200
    assert response.json()["job_content"] == "Python und Machine Learning"


def test_matching_accepts_profile_as_canonical_evidence_source(
    client, monkeypatch
) -> None:
    job_id = uuid4()
    profile_id = uuid4()

    async def fake_evaluate(payload):
        assert payload.profile_id == profile_id
        assert payload.evidence == []
        return MatchingResponse(job_id=str(payload.job_id), matches=[], summary={})

    monkeypatch.setattr("app.api.routes.matching.evaluate_matching", fake_evaluate)
    response = client.post(
        "/matching/evaluate",
        json={
            "job_id": str(job_id),
            "profile_id": str(profile_id),
            "requirements": [{"requirement": "Python"}],
        },
    )

    assert response.status_code == 200
def test_matching_run_requires_dify_configuration(client) -> None:
    response = client.post(
        "/matching/run",
        json={"job_id": str(uuid4()), "profile_id": str(uuid4())},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dify_matching_workflow_not_configured"
