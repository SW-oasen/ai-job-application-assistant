import pytest

from app.parsers.job_metadata import extract_job_metadata
from app.parsers.job_portals import normalize_job_document
from app.parsers.job_structure import extract_job_structure

LINKEDIN_CAPTURE = """[![Unternehmenslogo für ActAI](https://example.test/logo)](https://www.linkedin.com/company/actai/life/)

[ActAI](https://www.linkedin.com/company/actai/life/)

Applied AI Engineer

Deutschland · **Vor 10 Stunden**

[Remote](https://www.linkedin.com/jobs/view/4461352899/)

[Vollzeit](https://www.linkedin.com/jobs/view/4461352899/)

## Details zum Jobangebot

**About the Role**

Build reliable AI products.

**Focus**

- Build and ship AI features end-to-end
- Design and iterate on prompts and agent workflows

**Tech Stack**

- Python
- PyTorch / JAX

**Ideal Experience**

- Strong foundation in machine learning
- Hands-on experience deploying ML models

## Benachrichtigung für ähnliche Jobangebote einrichten

Premium promotion and unrelated content.

## Weitere Jobs

Unrelated Data Engineer role.
"""


def test_linkedin_profile_normalizes_header_sections_and_noise() -> None:
    document = normalize_job_document(
        LINKEDIN_CAPTURE,
        title="Applied AI Engineer | ActAI | LinkedIn",
        source_url="https://www.linkedin.com/jobs/view/4461352899/",
    )

    assert document.profile_name == "linkedin"
    assert document.title == "Applied AI Engineer"
    assert "# Applied AI Engineer" in document.markdown
    assert "Company: ActAI" in document.markdown
    assert "Location: Deutschland" in document.markdown
    assert "Work model: Remote" in document.markdown
    assert "Employment type: Vollzeit" in document.markdown
    assert "## Activities" in document.markdown
    assert document.markdown.count("## Requirements") == 2
    assert "Premium promotion" not in document.markdown
    assert "Unrelated Data Engineer" not in document.markdown

    metadata = extract_job_metadata(
        document.markdown, source_url="https://www.linkedin.com/jobs/view/4461352899/"
    )
    structure = extract_job_structure(document.markdown)
    assert metadata["title"] == "Applied AI Engineer"
    assert metadata["company"] == "ActAI"
    assert metadata["location"] == "Deutschland"
    assert metadata["work_model"] == "Remote"
    assert metadata["employment_type"] == "Vollzeit"
    assert [item["activity"] for item in structure.activities] == [
        "Build and ship AI features end-to-end",
        "Design and iterate on prompts and agent workflows",
    ]
    assert [item["requirement"] for item in structure.requirements] == [
        "Python",
        "PyTorch / JAX",
        "Strong foundation in machine learning",
        "Hands-on experience deploying ML models",
    ]


def test_linkedin_profile_supports_english_about_the_job_layout() -> None:
    document = normalize_job_document(
        """[inovex](https://www.linkedin.com/company/inovex/life/)

Data Engineer\\* / Machine Learning Engineer\\*

Germany Â· Reposted 1 day ago

[Remote](https://www.linkedin.com/jobs/view/4435676846/)

[Full-time](https://www.linkedin.com/jobs/view/4435676846/)

## About the job

**Was du bei uns bewegen kannst**

- Du entwickelst skalierbare Datenplattformen.

In unseren Projekten verwenden wir hÃ¤ufig folgende Technologien:

- Python, SQL, Java
- Databricks, Spark, Kafka

**Wer gut zu uns passen wÃ¼rde**

- Du hast ein abgeschlossenes Studium und mindestens zwei Jahre Berufserfahrung.

**Was wir dir bieten**

- Flexibles und mobiles Arbeiten

## About the company

inovex is an IT project house.
""",
        title="Data Engineer | inovex | LinkedIn",
        source_url="https://www.linkedin.com/jobs/view/4435676846/",
    )

    metadata = extract_job_metadata(
        document.markdown, source_url="https://www.linkedin.com/jobs/view/4435676846/"
    )
    structure = extract_job_structure(document.markdown)
    assert metadata["title"] == "Data Engineer* / Machine Learning Engineer*"
    assert metadata["company"] == "inovex"
    assert metadata["location"] == "Germany"
    assert metadata["work_model"] == "Remote"
    assert metadata["employment_type"] == "Full-time"
    assert [item["activity"] for item in structure.activities] == [
        "Du entwickelst skalierbare Datenplattformen"
    ]
    assert [item["requirement"] for item in structure.requirements] == [
        "Python, SQL, Java",
        "Databricks, Spark, Kafka",
        "Du hast ein abgeschlossenes Studium und mindestens zwei Jahre Berufserfahrung",
    ]
    assert [item["benefit"] for item in structure.benefits] == ["Flexibles und mobiles Arbeiten"]
    assert "inovex is an IT project house" not in document.markdown


def test_deloitte_profile_maps_impact_and_skillset_to_job_sections() -> None:
    document = normalize_job_document(
        """# Consultant AI Engineering (m/w/d)

## Dein Impact:

- Du entwickelst und implementierst AI- und GenAI-Lösungen.
- Du unterstützt bei Testing und Produktivsetzung von AI-Anwendungen.

## Dein Skillset:

- Programmierkenntnisse in Python sowie Erfahrung mit Azure AI Foundry und LangChain.
- Grundkenntnisse in Software Engineering, API-Integration und MLOps.

## Deine Chance:

- Mobile Working und Weiterbildung.
""",
        title="Consultant AI Engineering (m/w/d)",
        source_url="https://job.deloitte.com/job-consultant-ai-engineering-mwd-_50427",
    )

    structure = extract_job_structure(document.markdown)

    assert document.profile_name == "deloitte"
    assert [item["activity"] for item in structure.activities] == [
        "Du entwickelst und implementierst AI- und GenAI-Lösungen",
        "Du unterstützt bei Testing und Produktivsetzung von AI-Anwendungen",
    ]
    assert [item["requirement"] for item in structure.requirements] == [
        "Programmierkenntnisse in Python sowie Erfahrung mit Azure AI Foundry und LangChain",
        "Grundkenntnisse in Software Engineering, API-Integration und MLOps",
    ]
    assert [item["benefit"] for item in structure.benefits] == [
        "Mobile Working und Weiterbildung"
    ]


@pytest.mark.parametrize(
    ("url", "profile"),
    [
        ("https://de.indeed.com/viewjob?jk=123", "indeed"),
        ("https://instaffo.com/job/123", "instaffo"),
        ("https://www.stepstone.de/stellenangebote/123", "stepstone"),
        ("https://www.xing.com/jobs/berlin-data-engineer-123", "xing"),
        ("https://job.deloitte.com/job-consultant-ai-engineering-mwd-_50427", "deloitte"),
        ("https://careers.example.test/jobs/123", None),
    ],
)
def test_selects_profile_by_url_with_generic_fallback(url: str, profile: str | None) -> None:
    document = normalize_job_document("# Data Engineer", title="Data Engineer", source_url=url)

    assert document.profile_name == profile
    assert document.markdown == "# Data Engineer"
