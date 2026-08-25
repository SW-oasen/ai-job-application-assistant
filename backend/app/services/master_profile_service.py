import hashlib
import re
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, select, update

from app.core.errors import ApplicationError
from app.database.models import MasterProfile, Profile
from app.database.session import get_session_factory
from app.services.profile_service import _serialize

REQUIRED_HEADINGS = (
    "profile_name",
    "profile_job_title",
    "profile_text",
    "skills",
    "working_experience",
    "education",
    "certificates",
    "references",
    "selected_projects",
)


def normalized_master_profile_content(content: str) -> str:
    """Ignore formatting-only whitespace while comparing profile versions."""
    return re.sub(r"\s+", "", content)


def _factory():
    factory = get_session_factory()
    if factory is None:
        raise ApplicationError(
            "Master-Profile benötigen eine konfigurierte Datenbank.",
            code="database_not_configured",
            status_code=503,
        )
    return factory


def validate_master_profile(filename: str, content: bytes) -> str:
    if not Path(filename).name.lower().endswith(".md"):
        raise ApplicationError(
            "Bitte eine Markdown-Datei (.md) auswählen.",
            code="master_profile_invalid_file",
            status_code=422,
        )
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ApplicationError(
            "Die Markdown-Datei muss UTF-8-kodiert sein.",
            code="master_profile_invalid_encoding",
            status_code=422,
        ) from error
    if not text.strip():
        raise ApplicationError(
            "Die Markdown-Datei ist leer.", code="master_profile_empty", status_code=422
        )
    headings = {item.casefold() for item in re.findall(r"(?m)^#{1,2}\s+([a-z_]+)\s*$", text)}
    missing = [item for item in REQUIRED_HEADINGS if item not in headings]
    if missing:
        raise ApplicationError(
            "Pflichtbereiche fehlen: " + ", ".join(missing),
            code="master_profile_invalid_structure",
            status_code=422,
            details={"missing_headings": missing},
        )
    return text


async def import_master_profile(
    *, profile_id: UUID, language: str, filename: str, content: bytes
) -> dict:
    if language not in {"de", "en"}:
        raise ApplicationError(
            "language must be de or en.", code="invalid_master_profile_language", status_code=422
        )
    text = validate_master_profile(filename, content)
    async with _factory()() as session:
        if await session.get(Profile, profile_id) is None:
            raise ApplicationError(
                "Profil wurde nicht gefunden.", code="profile_not_found", status_code=404
            )
        previous = await session.scalar(
            select(MasterProfile).where(
                MasterProfile.profile_id == profile_id,
                MasterProfile.language == language,
                MasterProfile.is_current.is_(True),
            )
        )
        if previous and (
            normalized_master_profile_content(previous.content)
            == normalized_master_profile_content(text)
        ):
            raise ApplicationError(
                "Die Datei entspricht der aktuellen Master-Profil-Version; "
                "es wurde keine neue Version angelegt.",
                code="master_profile_unchanged",
                status_code=409,
            )
        current = await session.scalar(
            select(func.max(MasterProfile.version)).where(
                MasterProfile.profile_id == profile_id, MasterProfile.language == language
            )
        )
        await session.execute(
            update(MasterProfile)
            .where(
                MasterProfile.profile_id == profile_id,
                MasterProfile.language == language,
                MasterProfile.is_current.is_(True),
            )
            .values(is_current=False)
        )
        row = MasterProfile(
            profile_id=profile_id,
            language=language,
            content=text,
            version=(current or 0) + 1,
            is_current=True,
            original_filename=Path(filename).name,
            content_hash=hashlib.sha256(content).hexdigest(),
            file_size=len(content),
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _serialize(row)


async def list_master_profiles(profile_id: UUID) -> list[dict]:
    async with _factory()() as session:
        rows = (
            await session.scalars(
                select(MasterProfile)
                .where(MasterProfile.profile_id == profile_id, MasterProfile.is_current.is_(True))
                .order_by(MasterProfile.language)
            )
        ).all()
        return [_serialize(row) for row in rows]


async def get_current_master_profile(profile_id: UUID, language: str) -> dict:
    async with _factory()() as session:
        row = await session.scalar(
            select(MasterProfile).where(
                MasterProfile.profile_id == profile_id,
                MasterProfile.language == language,
                MasterProfile.is_current.is_(True),
            )
        )
        if row is None:
            raise ApplicationError(
                "Für diese Sprache ist kein Master-Profil vorhanden.",
                code="master_profile_not_found",
                status_code=404,
            )
        return _serialize(row)


async def list_master_profile_versions(profile_id: UUID, language: str) -> list[dict]:
    async with _factory()() as session:
        rows = (
            await session.scalars(
                select(MasterProfile)
                .where(MasterProfile.profile_id == profile_id, MasterProfile.language == language)
                .order_by(MasterProfile.version.desc())
            )
        ).all()
        return [_serialize(row) for row in rows]
