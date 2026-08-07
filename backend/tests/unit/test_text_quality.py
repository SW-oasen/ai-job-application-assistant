from app.parsers.text_quality import assess_text_quality


def test_marks_complete_content_as_sufficient() -> None:
    result = assess_text_quality(
        "A" * 500,
        title="Data Engineer",
        minimum_length=500,
    )

    assert result.sufficient is True
    assert result.warnings == []


def test_recommends_fallback_for_short_block_page() -> None:
    result = assess_text_quality(
        "Access denied. Verify you are human.",
        title=None,
        minimum_length=500,
    )

    assert result.sufficient is False
    assert set(result.warnings) == {
        "content_below_minimum_length",
        "title_not_detected",
        "possible_login_or_bot_protection",
    }


def test_allows_complete_job_with_login_text_in_page_chrome() -> None:
    result = assess_text_quality(
        "Aufgaben: Datenmodelle entwickeln. "
        "Anforderungen: Python und Statistik. "
        "Sign in to continue. "
        + ("Ausführliche Stellenbeschreibung. " * 30),
        title="Data Scientist (m/w/d)",
        minimum_length=500,
    )

    assert result.sufficient is True
    assert result.warnings == ["possible_login_or_bot_protection"]


def test_rejects_long_bot_page_without_job_structure() -> None:
    result = assess_text_quality(
        "Verify you are human. " + ("Security validation in progress. " * 30),
        title="Just a moment",
        minimum_length=500,
    )

    assert result.sufficient is False
    assert result.warnings == ["possible_login_or_bot_protection"]
