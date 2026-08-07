from uuid import uuid4

import pytest

from app.schemas.review import ReviewResult
from app.services import review_history_service


class FakeSession:
    def __init__(self) -> None:
        self.rows = []
        self.deleted_statements = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    def add(self, row) -> None:
        self.rows.append(row)

    async def execute(self, statement) -> None:
        self.deleted_statements.append(statement)

    async def commit(self) -> None:
        return None

    async def refresh(self, row, attribute_names=None) -> None:
        return None


@pytest.mark.asyncio
async def test_store_review_result_preserves_snapshots_and_ordered_issues(monkeypatch) -> None:
    session = FakeSession()
    monkeypatch.setattr(review_history_service, "_session_factory", lambda: lambda: session)
    result = ReviewResult(
        review_type="job_extraction",
        status="corrected",
        decision="correct",
        overall_confidence=0.84,
        corrected_result={"requirements": ["Python", "Docker"]},
        field_confidence={"requirements": 0.84},
        issues=[
            {
                "field": "requirements",
                "issue_type": "missing_value",
                "severity": "high",
                "message": "Docker fehlt.",
                "suggested_value": "Docker",
            }
        ],
        attempt=2,
    )

    stored = await review_history_service.store_review_result(
        subject_type="job",
        subject_id=uuid4(),
        source_result={"requirements": ["Python"]},
        review_result=result,
        final_result={"requirements": ["Python", "Docker"]},
        context={"profile_id": str(uuid4())},
    )

    assert session.rows[0].source_result == {"requirements": ["Python"]}
    assert session.rows[0].corrected_result == {"requirements": ["Python", "Docker"]}
    assert session.rows[0].issues[0].position == 0
    assert stored["issues"][0]["suggested_value"] == "Docker"
    assert len(session.deleted_statements) == 1
