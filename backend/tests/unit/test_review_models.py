from app.database.models import ReviewIssue, ReviewRun


def test_review_run_persists_generic_result_snapshots() -> None:
    table = ReviewRun.__table__

    assert {"source_result", "corrected_result", "final_result"} <= set(table.columns.keys())
    assert table.c.field_confidence.nullable is False
    assert table.c.retry_instructions.nullable is False
    assert {index.name for index in table.indexes} == {
        "ix_review_runs_subject",
        "ix_review_runs_type_status",
    }


def test_review_issue_is_owned_by_a_review_run() -> None:
    foreign_keys = ReviewIssue.__table__.c.review_run_id.foreign_keys

    assert len(foreign_keys) == 1
    assert next(iter(foreign_keys)).ondelete == "CASCADE"
    assert ReviewRun.issues.property.mapper.class_ is ReviewIssue
    assert ReviewIssue.review_run.property.mapper.class_ is ReviewRun