"""Versioned, round-tripable Markdown snapshots for personal profiles."""

import json
import re
from typing import Any

from pydantic import ValidationError

from app.schemas.profile import ProfileCreate

FORMAT = "application-assistant-profile"
VERSION = 1
MARKER = "<!-- profile-export: 1 -->"


def parse_profile_snapshot_with_resources(content: str) -> tuple[ProfileCreate, dict[str, list[dict[str, Any]]]]:
    profile = parse_profile_snapshot(content)
    match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    payload = json.loads(match.group(1)) if match else {}
    raw_resources = payload.get("profile", {}).get("resources", {})
    if not isinstance(raw_resources, dict) or any(not isinstance(value, list) for value in raw_resources.values()):
        raise ValueError("Die Profilressourcen sind ungültig.")
    return profile, raw_resources


def render_profile_snapshot(profile: dict[str, Any] | ProfileCreate) -> str:
    if isinstance(profile, ProfileCreate):
        profile = profile.model_dump(mode="json")
    fields = {
        key: profile.get(key)
        for key in ProfileCreate.model_fields
        if key != "change_reason"
    }
    fields["display_name"] = profile.get("display_name", "")
    if profile.get("resources"):
        fields["resources"] = profile["resources"]
    payload = {"format": FORMAT, "version": VERSION, "profile": fields}
    return "# Application Assistant Profile Export\n\n" + MARKER + "\n\n```json\n" + json.dumps(payload, ensure_ascii=False, indent=2) + "\n```\n"


def parse_profile_snapshot(content: str) -> ProfileCreate:
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Die Profilsicherung ist leer.")
    if MARKER not in content:
        raise ValueError("Profil-Sicherungsmarker fehlt oder ist unbekannt.")
    match = re.search(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
    if not match:
        raise ValueError("Kein gültiger JSON-Block in der Profilsicherung gefunden.")
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON der Profilsicherung ist ungültig: {exc.msg}.") from exc
    if payload.get("format") != FORMAT or payload.get("version") != VERSION:
        raise ValueError("Format oder Version der Profilsicherung wird nicht unterstützt.")
    profile = payload.get("profile")
    if not isinstance(profile, dict):
        raise ValueError("Der Profilblock fehlt oder ist kein Objekt.")
    try:
        return ProfileCreate.model_validate({key: value for key, value in profile.items() if key != "resources"})
    except ValidationError as exc:
        details = "; ".join(f"{'.'.join(str(x) for x in error['loc'])}: {error['msg']}" for error in exc.errors())
        raise ValueError(f"Profil-Sicherung enthält ungültige Felder: {details}") from exc
