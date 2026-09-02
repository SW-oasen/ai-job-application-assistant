"""Create repeatable, clearly fictional data for the isolated demo database."""

import asyncio
import hashlib
import os
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.core.config import get_settings
from app.core.demo_mode import validate_demo_database
from app.database.models import (
    Application,
    ApplicationEvent,
    Company,
    Job,
    JobActivity,
    JobRequirement,
    Profile,
    Skill,
)
from app.database.session import get_session_factory

PROFILE_NAME = os.getenv("DEMO_PROFILE_NAME", "Demo Testerprofil")
DEMO_SOURCE = "demo_seed"

DEMO_JOBS = (
    {
        "slug": "nordlicht-data",
        "company": "Nordlicht Datenwerke GmbH",
        "industry": "Datenplattformen",
        "title": "Data Analyst (m/w/d) – Nachhaltigkeitsdaten",
        "location": "Hamburg",
        "work_model": "hybrid",
        "requirements": [
            (
                "Fachkenntnisse",
                "Sichere Anwendung von SQL und Python für Datenanalysen.",
                "must_have",
                ["SQL", "Python"],
            ),
            (
                "Methodik",
                "Erfahrung mit Dashboarding und verständlicher Datenkommunikation.",
                "must_have",
                ["Power BI", "Storytelling"],
            ),
            (
                "Sprache",
                "Sehr gute Deutschkenntnisse in Wort und Schrift.",
                "nice_to_have",
                ["Deutsch"],
            ),
        ],
        "activities": [
            "ESG- und Produktdaten analysieren und plausibilisieren.",
            "Kennzahlen-Dashboards für Fachbereiche entwickeln.",
            "Ergebnisse für Management und Kund:innen aufbereiten.",
        ],
        "application_status": "applied",
    },
    {
        "slug": "kiesel-product",
        "company": "Kiesel Produktstudio AG",
        "industry": "Digitale Produkte",
        "title": "Product Operations Manager (m/w/d)",
        "location": "Berlin",
        "work_model": "remote",
        "requirements": [
            (
                "Erfahrung",
                "Mehrjährige Erfahrung in Produktorganisation oder Projektmanagement.",
                "must_have",
                ["Produktmanagement", "Projektmanagement"],
            ),
            (
                "Fachkenntnisse",
                "Routine mit Jira, Confluence und agilen Arbeitsweisen.",
                "must_have",
                ["Jira", "Confluence", "Agile"],
            ),
            (
                "Arbeitsweise",
                "Strukturierte, eigenverantwortliche Zusammenarbeit mit mehreren Teams.",
                "nice_to_have",
                ["Kommunikation"],
            ),
        ],
        "activities": [
            "Produktprozesse und Team-Routinen weiterentwickeln.",
            "Roadmap- und Release-Planung koordinieren.",
            "Kennzahlen für Durchlaufzeiten und Qualität etablieren.",
        ],
        "application_status": "interview",
    },
    {
        "slug": "voltwerk-cloud",
        "company": "Voltwerk Cloud Services SE",
        "industry": "Energie-Software",
        "title": "Business Intelligence Consultant (m/w/d)",
        "location": "Köln",
        "work_model": "hybrid",
        "requirements": [
            (
                "Fachkenntnisse",
                "Erfahrung mit Datenmodellierung, SQL und ETL-Prozessen.",
                "must_have",
                ["SQL", "Datenmodellierung", "ETL"],
            ),
            (
                "Fachkenntnisse",
                "Kenntnisse in Power BI oder Tableau.",
                "must_have",
                ["Power BI", "Tableau"],
            ),
            (
                "Beratung",
                "Freude an Workshops mit Fachbereichen.",
                "nice_to_have",
                ["Workshop", "Beratung"],
            ),
        ],
        "activities": [
            "BI-Lösungen von der Anforderung bis zum Rollout begleiten.",
            "Datenmodelle für Energie- und Verbrauchsdaten entwerfen.",
            "Fachbereiche in Datenfragen beraten.",
        ],
        "application_status": "draft",
    },
    {
        "slug": "stadtfaden",
        "company": "Stadtfaden Mobilität eG",
        "industry": "Urbane Mobilität",
        "title": "Projektmanager:in Digitale Mobilität",
        "location": "Leipzig",
        "work_model": "onsite",
        "requirements": [
            (
                "Erfahrung",
                "Erfahrung in der Steuerung digitaler Projekte mit öffentlichen oder "
                "privaten Partnern.",
                "must_have",
                ["Projektmanagement", "Stakeholdermanagement"],
            ),
            (
                "Methodik",
                "Kenntnisse agiler und klassischer Projektmethoden.",
                "must_have",
                ["Scrum", "Kanban"],
            ),
            ("Sprache", "Verhandlungssicheres Deutsch.", "must_have", ["Deutsch"]),
        ],
        "activities": [
            "Digitale Mobilitätsprojekte planen und steuern.",
            "Stakeholder-Workshops moderieren.",
            "Fortschritt, Risiken und Budget transparent berichten.",
        ],
        "application_status": None,
    },
    {
        "slug": "klartext-ai",
        "company": "Klartext KI Lab GmbH",
        "industry": "Künstliche Intelligenz",
        "title": "Junior AI Operations Specialist (m/w/d)",
        "location": "München",
        "work_model": "hybrid",
        "requirements": [
            (
                "Fachkenntnisse",
                "Grundkenntnisse in Python, APIs und Datenaufbereitung.",
                "must_have",
                ["Python", "APIs", "Datenaufbereitung"],
            ),
            (
                "Arbeitsweise",
                "Sorgfalt bei Qualitätskontrollen und Dokumentation.",
                "must_have",
                ["Qualitätssicherung", "Dokumentation"],
            ),
            (
                "Fachkenntnisse",
                "Interesse an LLMs und Prompting.",
                "nice_to_have",
                ["LLM", "Prompting"],
            ),
        ],
        "activities": [
            "KI-gestützte Prozesse testen und überwachen.",
            "Trainings- und Auswertungsdaten dokumentieren.",
            "Fehlerbilder strukturieren und Verbesserungen nachverfolgen.",
        ],
        "application_status": "followed_up",
    },
    {
        "slug": "horizon-education",
        "company": "Horizon Lernsysteme GmbH",
        "industry": "Bildungstechnologie",
        "title": "Customer Insights Analyst (m/w/d)",
        "location": "Frankfurt am Main",
        "work_model": "remote",
        "requirements": [
            (
                "Fachkenntnisse",
                "Erfahrung mit Nutzerforschung, Umfragen und Datenanalyse.",
                "must_have",
                ["User Research", "SQL", "Umfragen"],
            ),
            (
                "Methodik",
                "Fähigkeit, qualitative und quantitative Erkenntnisse zu verbinden.",
                "must_have",
                ["Mixed Methods", "Analyse"],
            ),
            (
                "Kommunikation",
                "Präsentationsstärke für Produkt- und Vertriebsteams.",
                "nice_to_have",
                ["Präsentation", "Storytelling"],
            ),
        ],
        "activities": [
            "Kundenfeedback aus verschiedenen Quellen auswerten.",
            "Insights für Produktentscheidungen ableiten.",
            "Research-Ergebnisse in verständliche Handlungsempfehlungen übersetzen.",
        ],
        "application_status": "rejected",
    },
)


async def ensure_profile(session) -> Profile:
    profile = await session.scalar(select(Profile).where(Profile.display_name == PROFILE_NAME))
    if profile is None:
        profile = Profile(
            display_name=PROFILE_NAME,
            full_name="Alex Demo",
            email="alex.demo@example.invalid",
            career_goal="Daten und digitale Produkte wirksam verbinden.",
            target_roles=[
                "Data Analyst",
                "Business Intelligence Consultant",
                "Product Operations Manager",
            ],
            target_industries=["Datenplattformen", "Digitale Produkte", "Bildungstechnologie"],
            target_locations=["Hamburg", "Berlin", "Köln", "Remote"],
            preferred_work_models=["hybrid", "remote"],
            preferred_employment_types=["Vollzeit"],
            default_language="de",
            status="active",
        )
        session.add(profile)
        await session.flush()

    existing_skills = set(
        (
            await session.scalars(
                select(Skill.canonical_name).where(Skill.profile_id == profile.id)
            )
        ).all()
    )
    for name, category, level, years in (
        ("Python", "Programmiersprache", "Fortgeschritten", 3),
        ("SQL", "Datenbanken", "Fortgeschritten", 4),
        ("Power BI", "Business Intelligence", "Fortgeschritten", 3),
        ("Projektmanagement", "Methodik", "Fortgeschritten", 4),
        ("Jira", "Tools", "Fortgeschritten", 3),
        ("Datenanalyse", "Methodik", "Fortgeschritten", 4),
    ):
        if name not in existing_skills:
            session.add(
                Skill(
                    profile_id=profile.id,
                    canonical_name=name,
                    category=category,
                    proficiency_level=level,
                    years_experience=years,
                    last_used_at=date.today(),
                    aliases=[],
                    active=True,
                    status="active",
                )
            )
    return profile


async def seed_job(session, profile: Profile, data: dict, index: int) -> bool:
    source_filename = f"demo-{index:02d}-{data['slug']}.md"
    existing = await session.scalar(select(Job).where(Job.source_filename == source_filename))
    if existing is not None:
        return False
    company = await session.scalar(select(Company).where(Company.name == data["company"]))
    if company is None:
        company = Company(
            name=data["company"],
            industry=data["industry"],
            description="Fiktives Unternehmen für die Produktdemonstration.",
            location=data["location"],
        )
        session.add(company)
        await session.flush()
    content = f"{data['title']} bei {data['company']} in {data['location']}. " + " ".join(
        data["activities"]
    )
    job = Job(
        company_id=company.id,
        title=data["title"],
        source_type=DEMO_SOURCE,
        source_filename=source_filename,
        location=data["location"],
        work_model=data["work_model"],
        employment_type="Vollzeit",
        language="de",
        status="ready",
        published_at=date.today() - timedelta(days=index * 2),
        deadline=date.today() + timedelta(days=14 + index * 3),
        raw_content=content,
        normalized_content=content,
        extracted_json={"demo": True, "notice": "Fiktive Stellenanzeige für die Präsentation."},
        prompt_version="demo-seed-v1",
        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        retrieval_method="demo_seed",
        import_warnings=[],
    )
    session.add(job)
    await session.flush()
    for category, text, priority, keywords in data["requirements"]:
        session.add(
            JobRequirement(
                job_id=job.id,
                category=category,
                requirement_text=text,
                normalized_value=None,
                priority=priority,
                evidence="Fiktive Demoanzeige",
                confidence=1.0,
                keywords=keywords,
            )
        )
    for position, activity in enumerate(data["activities"], start=1):
        session.add(
            JobActivity(
                job_id=job.id,
                activity_text=activity,
                category="responsibility",
                evidence="Fiktive Demoanzeige",
                confidence=1.0,
                keywords=[],
                position=position,
            )
        )
    if data["application_status"]:
        occurred_at = datetime.now(UTC) - timedelta(days=index)
        application = Application(
            job_id=job.id,
            profile_id=profile.id,
            status=data["application_status"],
            status_changed_at=occurred_at,
            applied_at=occurred_at if data["application_status"] != "draft" else None,
            next_action="Demo: nächsten Schritt besprechen",
            next_action_at=occurred_at + timedelta(days=7),
        )
        session.add(application)
        await session.flush()
        session.add(
            ApplicationEvent(
                application_id=application.id,
                event_type="created",
                status=data["application_status"],
                occurred_at=occurred_at,
                channel="company_portal" if data["application_status"] == "applied" else None,
                portal_name=None,
                contact_person=None,
                note="Fiktiver Status für die Produktdemonstration.",
            )
        )
    return True


async def main() -> None:
    validate_demo_database(get_settings())
    factory = get_session_factory()
    if factory is None:
        raise RuntimeError(
            "DATABASE_URL fehlt. Das Demo-Seeding benötigt eine separate Demo-Datenbank."
        )
    async with factory() as session:
        profile = await ensure_profile(session)
        created = 0
        for index, data in enumerate(DEMO_JOBS, start=1):
            created += await seed_job(session, profile, data, index)
        await session.commit()
    print(
        f"Demo-Daten bereit: Profil '{PROFILE_NAME}', {created} neue von "
        f"{len(DEMO_JOBS)} fiktiven Stellenanzeigen."
    )


if __name__ == "__main__":
    asyncio.run(main())
