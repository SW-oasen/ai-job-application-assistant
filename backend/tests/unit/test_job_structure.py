from app.parsers.job_structure import extract_job_structure


def test_extracts_activities_and_requirements_from_markdown_sections() -> None:
    content = """
# Machine Learning Engineer

## Deine Aufgaben

- Entwicklung von KI-Anwendungen für interne Prozesse
- Automatisierung datengetriebener Arbeitsabläufe

## Das bringst du mit

- Mindestens drei Jahre Erfahrung mit Python
- Idealerweise Kenntnisse in Azure

## Wir bieten

- Flexible Arbeitszeiten
"""

    result = extract_job_structure(content)

    assert [item["activity"] for item in result.activities] == [
        "Entwicklung von KI-Anwendungen für interne Prozesse",
        "Automatisierung datengetriebener Arbeitsabläufe",
    ]
    assert [item["priority"] for item in result.requirements] == [
        "must",
        "nice_to_have",
    ]
    assert "Python" in result.requirements[0]["keywords"]
    assert all("Flexible Arbeitszeiten" not in str(item) for item in result.requirements)


def test_ignores_lists_outside_recognized_sections() -> None:
    result = extract_job_structure(
        """
## Benefits
- Firmenwagen
- Getränke
"""
    )

    assert result.activities == []
    assert result.requirements == []
