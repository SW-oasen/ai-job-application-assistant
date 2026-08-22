from app.parsers.job_metadata import extract_job_metadata


def test_extracts_contract_term_from_english_role_scope() -> None:
    metadata = extract_job_metadata(
        """
**Scope of the role:**
**Temporary (1 Year),** focused on execution and delivery.
"""
    )

    assert metadata["contract_term"] == "Temporary (1 Year)"


def test_extracts_fixed_term_duration_from_english_prose() -> None:
    metadata = extract_job_metadata("This is a fixed-term for 12 months position.")

    assert metadata["contract_term"] == "fixed-term for 12 months"


def test_extracts_labeled_job_metadata_and_remote_option() -> None:
    content = """
> #### Arbeitsort
>
> Berlin
>
> #### Anstellungsart
>
> Vollzeit
>
> Veröffentlichungsdatum: Vor 30+ Tagen veröffentlicht

We offer employees the opportunity to work flexibly and remotely.
"""

    assert extract_job_metadata(content) == {
        "title": None,
        "company": None,
        "published_text": "Vor 30+ Tagen veröffentlicht",
        "location": "Berlin",
        "employment_type": "Vollzeit",
        "contract_term": None,
        "source_portal": None,
        "work_model": "Remote möglich",
        "language": "en",
    }


def test_extracts_location_from_google_maps_link() -> None:
    metadata = extract_job_metadata(
        "[Berlin, Deutschland](https://www.google.com/maps/search/?api=1&query=Berlin)"
    )

    assert metadata["location"] == "Berlin, Deutschland"


def test_splits_definition_list_employment_type_and_contract_term() -> None:
    metadata = extract_job_metadata(
        """
Beschäftigungsart
:   Vollzeit, unbefristet
"""
    )

    assert metadata["employment_type"] == "Vollzeit"
    assert metadata["contract_term"] == "unbefristet"


def test_detects_english_job_description_language() -> None:
    metadata = extract_job_metadata(
        """
# Data Engineer

We are looking for a data engineer to join our team. You will build reliable
data products and work with our analysts. Your application should include a CV.
"""
    )

    assert metadata["language"] == "en"


def test_detects_german_job_description_language() -> None:
    metadata = extract_job_metadata(
        """
# Data Engineer

Wir suchen einen Data Engineer für unser Team. Du wirst zuverlässige
Datenprodukte entwickeln und mit unseren Analysten arbeiten.
"""
    )

    assert metadata["language"] == "de"


def test_leaves_ambiguous_job_description_language_empty() -> None:
    assert extract_job_metadata("Data Engineer\nBerlin")["language"] is None


def test_extracts_company_below_title_before_information_short_name() -> None:
    content = """
# AI Engineer (m/w/d)

Gesellschaft für musikalische Aufführungs- und mechanische Vervielfältigungsrechte (GEMA)

Berlin

## **INFORMATIONEN**

GEMA
"""

    assert extract_job_metadata(content)["company"] == (
        "Gesellschaft für musikalische Aufführungs- und mechanische "
        "Vervielfältigungsrechte (GEMA)"
    )


def test_extracts_plain_pdf_header_metadata() -> None:
    content = """
Junior Machine
Learning Engineer
(m/w/d)
AMAI GmbH
CJ
Hi! Ich bin Christopher Jungmann von AMAI GmbH.
Remote in DE
Du kannst aus Deutschland arbeiten.
Karlsruhe
Bürostandorte
50.000 - 70.000 €
Jahresgehalt
Vollzeit
Jobdetails
"""

    metadata = extract_job_metadata(content)

    assert metadata["title"] == "Junior Machine Learning Engineer (m/w/d)"
    assert metadata["company"] == "AMAI GmbH"
    assert metadata["location"] == "Karlsruhe"
    assert metadata["employment_type"] == "Vollzeit"
    assert metadata["work_model"] == "Remote"


def test_extracts_compact_screenshot_header_metadata() -> None:
    content = """
AI Engineer (m/w/d)
Amoria Bond · Berlin Metropolitan Area (Hybrid)

About the job

Unser Kunde ist ein innovatives Unternehmen aus dem Hightech-Umfeld.
"""

    metadata = extract_job_metadata(content)

    assert metadata["title"] == "AI Engineer (m/w/d)"
    assert metadata["company"] == "Amoria Bond"
    assert metadata["location"] == "Berlin Metropolitan Area"
    assert metadata["work_model"] == "Hybrid"


def test_extracts_ba_pdf_header_with_icons_and_ignores_portal_label() -> None:
    content = """
\uf5af Arbeit
AI Engineer – Research Algorithm/Model Expert (Scientific
Brain Domain)
CHN Energy Europe Research GmbH
\uf1aa Arbeitsort
Berlin
Anstellungsart
Vollzeit

Arbeitsorte
• Competitive compensation and benefits
"""

    metadata = extract_job_metadata(content)

    assert metadata["title"] == (
        "AI Engineer – Research Algorithm/Model Expert (Scientific Brain Domain)"
    )
    assert metadata["company"] == "CHN Energy Europe Research GmbH"
    assert metadata["location"] == "Berlin"
    assert metadata["employment_type"] == "Vollzeit"


def test_strips_leading_mineru_image_and_repairs_ai_title_ocr() -> None:
    content = """
![](images/header-decoration.jpg) Al Engineer – Research Algorithm/Model Expert
CHN Energy Europe Research GmbH
Arbeitsort
Berlin
"""

    metadata = extract_job_metadata(content)

    assert metadata["title"] == (
        "AI Engineer – Research Algorithm/Model Expert"
    )
    assert metadata["company"] == "CHN Energy Europe Research GmbH"


def test_extracts_inline_mineru_job_metadata() -> None:
    content = """
Arbeitsort Berlin
Anstellungsart Vollzeit
Befristung befristet für 24 Monate
"""

    metadata = extract_job_metadata(content)

    assert metadata["location"] == "Berlin"
    assert metadata["employment_type"] == "Vollzeit"
    assert metadata["contract_term"] == "befristet für 24 Monate"


def test_infers_source_portal_from_filename_without_changing_job_content() -> None:
    metadata = extract_job_metadata(
        "Machine Learning Engineer\nArbeitsort\nBerlin",
        source_filename="Machine_Learning_Engineer_-_Berlin_-_Indeed.com.pdf",
    )

    assert metadata["source_portal"] == "Indeed"


def test_indeed_job_address_wins_over_commute_distance() -> None:
    metadata = extract_job_metadata(
        """
Arbeitsort
45 Minuten ab Oldenburger Str. 31
Job address
Weidendamm 1, 15831 Mahlow
"""
    )

    assert metadata["location"] == "Weidendamm 1, 15831 Mahlow"


def test_extracts_standalone_legal_company_from_indeed_footer() -> None:
    metadata = extract_job_metadata(
        """
Vollständige Stellenbeschreibung
Als führender Getränkefacheinzelhändler begeistern wir unsere Kunden.
Wir freuen uns auf deine Online-Bewerbung über dieses Portal.
Getränke Hoffmann Gruppe KG
Am Weidendamm 1
15831 Blankenfelde-Mahlow
"""
    )

    assert metadata["company"] == "Getränke Hoffmann Gruppe KG"


def test_extracts_legal_company_from_indeed_description_prose() -> None:
    metadata = extract_job_metadata(
        """
Einleitung
Die Munich Innovation Labs GmbH – A Rohde & Schwarz
Company entwickelt innovative Software- und KI-Lösungen.
""",
        source_filename=(
            "Junior_Software_Engineer_m_f_d_AI_and_Data_Systems"
            "_-_Berlin_-_Indeed.com.pdf"
        ),
    )

    assert metadata["company"] == "Munich Innovation Labs GmbH"


def test_skips_apply_cta_and_extracts_company_from_career_page_prose() -> None:
    metadata = extract_job_metadata(
        """
# Junior Projektmanager (m/f/d) AI and Data Systems

[Jetzt bewerben](https://job.rohde-schwarz.com/apply)

Kontakt

### Einleitung

Die Munich Innovation Labs GmbH – A Rohde & Schwarz Company entwickelt
innovative Software- und KI-Lösungen.
""",
        source_url=(
            "https://www.rohde-schwarz.com/de/karriere/stellenangebote/"
            "junior-projektmanager.html"
        ),
    )

    assert metadata["company"] == "Munich Innovation Labs GmbH"


def test_uses_instaffo_main_heading_and_company_details() -> None:
    content = """
![](images/7a1084c5cdaa0b802d3da1738c9ae959b.jpg)

Junior Macnine Learning
Engineer (m/w/d) AMAI GmbH

## Data Engineer (all genders) in Berlin

# Junior Machine Learning Engineer (m/w/d)

Gespeichert!

AMAI AMAI GmbH AI EXPERTS

Remote in DE Du kannst aus Deutschland arbeiten.

Karlsruhe Bürostandorte

ÉVollzeit

## Firmendetails

## am.ai

AMAI ist der Spezialist für maßgeschneiderte KI-Beratung.
"""

    metadata = extract_job_metadata(
        content,
        source_filename="Junior_Machine_Learning_Engineer___Instaffo.pdf",
    )

    assert metadata["title"] == "Junior Machine Learning Engineer (m/w/d)"
    assert metadata["company"] == "am.ai"
    assert metadata["location"] == "Karlsruhe"
    assert metadata["employment_type"] == "Vollzeit"
    assert metadata["work_model"] == "Remote"


def test_extracts_join_company_link_before_job_heading() -> None:
    metadata = extract_job_metadata(
        """
[![Limebit GmbH](https://cdn.join.com/logo.jpg)

Limebit GmbH](https://join.com/companies/limebit)

# Data Science & Machine Learning for Life-Science (m/w/d)

[Berlin, Deutschland](https://maps.example/berlin)
""",
        source_url="https://join.com/companies/limebit/16533009-data-science",
    )

    assert metadata["title"] == "Data Science & Machine Learning for Life-Science (m/w/d)"
    assert metadata["company"] == "Limebit GmbH"


def test_extracts_brand_link_instead_of_location_below_greenhouse_title() -> None:
    content = """
[![GROPYUS Logo](https://example.com/logo.png)](https://www.gropyus.com)

# Data Engineer (all genders)

Berlin, Berlin, Germany

Apply Now
"""
    assert extract_job_metadata(content)["company"] == "GROPYUS"
