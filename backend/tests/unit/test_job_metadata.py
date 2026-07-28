from app.parsers.job_metadata import extract_job_metadata


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
    }


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
