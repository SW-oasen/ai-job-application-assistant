from app.parsers.job_structure import extract_job_structure


def test_extracts_generic_you_will_activity_heading() -> None:
    result = extract_job_structure("""
**As part of the Data Platform organization, you will:**
- Design and maintain data pipelines
- Improve data reliability
""")
    assert len(result.activities) == 2


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
        "must",
        "nice_to_have",
    ]
    assert result.requirements[0]["normalized_value"] == "min_years:3"
    assert "Python" in result.requirements[1]["keywords"]
    assert all("Flexible Arbeitszeiten" not in str(item) for item in result.requirements)


def test_extracts_benefits_separately() -> None:
    result = extract_job_structure(
        """
## Benefits
- Firmenwagen
- Getränke
"""
    )

    assert result.activities == []
    assert result.requirements == []
    assert [item["benefit"] for item in result.benefits] == ["Firmenwagen", "Getränke"]


def test_keeps_benefits_out_of_activities_for_combined_heading() -> None:
    result = extract_job_structure(
        "## Aufgaben und Benefits\n- Anforderungen an Kompetenz\n- Flexikompass"
    )
    assert result.activities == []
    assert result.requirements == []
    assert [item["benefit"] for item in result.benefits] == [
        "Anforderungen an Kompetenz", "Flexikompass"
    ]


def test_maps_my_competencies_to_requirements() -> None:
    result = extract_job_structure(
        "## Meine Kompetenzen\n- Python und SQL beherrschen"
    )
    assert result.activities == []
    assert result.requirements[0]["requirement"] == "Python und SQL beherrschen"


def test_maps_generic_competency_headings_to_requirements() -> None:
    result = extract_job_structure(
        "## Kompetenzprofil\n- Erfahrung mit Datenbanken"
    )
    assert result.activities == []
    assert result.requirements[0]["requirement"] == "Erfahrung mit Datenbanken"


def test_extracts_seniority_as_separate_requirement() -> None:
    result = extract_job_structure(
        """
## Das bringst du mit
- Mindestens drei Jahre Erfahrung mit Python
"""
    )

    assert result.requirements[0]["requirement"] == "Mindestens 3 Jahre Berufserfahrung"
    assert result.requirements[0]["category"] == "experience"
    assert result.requirements[0]["normalized_value"] == "min_years:3"
    assert result.requirements[1]["requirement"] == "Python"


def test_keeps_seniority_range_complete() -> None:
    result = extract_job_structure(
        "## Anforderungen\n- Mindestens 2 bis 3 Jahre Berufserfahrung"
    )
    assert result.requirements[0]["requirement"] == "Mindestens 2 Jahre Berufserfahrung"
    assert result.requirements[0]["normalized_value"] == "min_years:2"
    assert len(result.requirements) == 1


def test_extracts_activities_and_requirements_from_indeed_style_headings() -> None:
    content = """
## **In this position, you'll**

- **Design and build** scalable marketing data models
- **Own production reliability** by investigating incidents end-to-end

## **About you**

- **Hands-on experience in Analytics Engineering** (typically around 3 years)
- **Strong SQL skills**, including writing readable queries
"""

    result = extract_job_structure(content)

    assert [item["activity"] for item in result.activities] == [
        "**Design and build** scalable marketing data models",
        "**Own production reliability** by investigating incidents end-to-end",
    ]
    assert len(result.requirements) == 2


def test_extracts_requirements_from_what_you_need_to_be_successful_heading() -> None:
    result = extract_job_structure(
        "## What you need to be successful\n"
        "- Experience building data products\n"
        "- Strong communication skills\n"
    )

    assert [item["requirement"] for item in result.requirements] == [
        "Experience building data products",
        "Strong communication skills",
    ]


def test_extracts_charite_style_inline_activity_and_requirement_sections() -> None:
    result = extract_job_structure(
        "Zu Ihren Aufgaben zählen die\n"
        "- Entwicklung von Data-Science-Modellen\n"
        "- Durchführung wissenschaftlicher Analysen\n"
        "Sie verfügen über\n"
        "- Sehr gute Kenntnisse in Python\n"
        "- Erfahrung mit Machine Learning\n"
    )

    assert [item["activity"] for item in result.activities] == [
        "Entwicklung von Data-Science-Modellen",
        "Durchführung wissenschaftlicher Analysen",
    ]
    assert [item["requirement"] for item in result.requirements] == [
        "Sehr gute Kenntnisse in Python",
        "Erfahrung mit Machine Learning",
    ]


def test_extracts_requirements_from_blockquoted_heading() -> None:
    result = extract_job_structure(
        "> ## **Qualifikation**\n"
        "> - Erfahrung mit Python\n"
        "> - Kenntnisse in Docker\n"
    )
    assert [item["requirement"] for item in result.requirements] == [
        "Erfahrung mit Python",
        "Kenntnisse in Docker",
    ]


def test_classifies_bold_markdown_headings() -> None:
    result = extract_job_structure(
        "## **Tätigkeiten**\n- Entwicklung von APIs\n"
        "## **Anforderungen**\n- Erfahrung mit Python\n"
        "## **Benefits**\n- Flexible Arbeitszeiten\n"
    )
    assert [item["activity"] for item in result.activities] == ["Entwicklung von APIs"]
    assert [item["requirement"] for item in result.requirements] == ["Erfahrung mit Python"]
    assert [item["benefit"] for item in result.benefits] == ["Flexible Arbeitszeiten"]


def test_extracts_activities_from_bold_inline_subheading() -> None:
    content = """
#### **Warum das zählt**

Ein Kontextabsatz ohne Bezug zu Aufgaben.

**Deine Aufgaben** Produkte entwickeln:

- Du begleitest neue Produkte von der Idee bis zum produktiven Einsatz.
- Du entwickelst APIs und Datenmodelle.

#### Das bringst du mit

- Mindestens 5 Jahre Erfahrung im Software Engineering.
"""

    result = extract_job_structure(content)

    assert [item["activity"] for item in result.activities] == [
        "Du begleitest neue Produkte von der Idee bis zum produktiven Einsatz",
        "Du entwickelst APIs und Datenmodelle",
    ]
    assert result.requirements[0]["requirement"] == "Mindestens 5 Jahre Berufserfahrung"


def test_maps_necessary_and_desirable_qualification_sections() -> None:
    result = extract_job_structure(
        """
## Qualifikation

**Folgende Qualifikationen sind notwendig:**

- Python-Kenntnisse
- Erfahrung mit Statistik

**Folgende Qualifikationen sind wünschenswert:**

- Erfahrungen im Gesundheitssektor
"""
    )

    assert [item["priority"] for item in result.requirements] == [
        "must",
        "must",
        "nice_to_have",
    ]


def test_keeps_indented_list_item_continuation() -> None:
    result = extract_job_structure(
        "## Qualifikation\n\n"
        "**Folgende Qualifikationen sind notwendig:**\n\n"
        "- Abgeschlossenes Studium in einem relevanten Fachbereich\n"
        "  *(z. B. Data Science, Informatik, Mathematik oder vergleichbar)* oder\n"
        "  vergleichbare praktische Erfahrung\n"
    )

    assert result.requirements[0]["requirement"] == (
        "Abgeschlossenes Studium in einem relevanten Fachbereich "
        "*(z. B. Data Science, Informatik, Mathematik oder vergleichbar)* oder "
        "vergleichbare praktische Erfahrung"
    )


def test_repairs_mojibake_in_german_requirement_heading() -> None:
    result = extract_job_structure(
        "## Das bringst du im Bereich Functional Test mit\n"
        "- Abgeschlossenes IT-Studium oder vergleichbare Qualifikation\n"
    )
    assert len(result.requirements) == 1


def test_extracts_activities_from_mission_heading() -> None:
    result = extract_job_structure(
        "### Deine Mission bei uns\n"
        "- Du konzipierst die Datenplattform\n"
    )
    assert result.activities[0]["activity"] == "Du konzipierst die Datenplattform"
