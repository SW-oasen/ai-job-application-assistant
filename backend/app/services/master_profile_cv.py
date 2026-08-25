"""Parse the constrained Markdown master-profile format and render CVs deterministically."""

import re
from dataclasses import dataclass
from typing import Any

from app.core.errors import ApplicationError


def _text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _section(content: str, name: str) -> str:
    match = re.search(
        rf"(?ms)^#{{1,2}}\s+{re.escape(name)}\s*$\n(?P<value>.*?)(?=^#{{1,2}}\s+|\Z)", content
    )
    return match.group("value") if match else ""


def _field(content: str, name: str) -> str:
    return _text(_section(content, name))


def _subfields(block: str) -> dict[str, str]:
    values: dict[str, str] = {}
    matches = list(re.finditer(r"(?m)^####\s+([a-z_]+)\s*$", block))
    for index, match in enumerate(matches):
        values[match.group(1)] = _text(block[match.end(): matches[index + 1].start() if index + 1 < len(matches) else len(block)])
    return values


def parse_master_profile(content: str) -> dict[str, Any]:
    """Expose only source-backed selectable items with stable IDs."""
    skills: list[dict] = []
    for category_match in re.finditer(r"(?m)^###\s+([^\n]+)\s*$", _section(content, "skills")):
        category = _text(category_match.group(1))
        start = category_match.end()
        next_match = re.search(r"(?m)^###\s+", _section(content, "skills")[start:])
        block = _section(content, "skills")[start: start + next_match.start() if next_match else None]
        for position, raw in enumerate(re.findall(r"(?m)^\s*[-*]\s+(.+?)\s*$", block)):
            name = _text(raw)
            if name:
                skills.append({"id": f"skill:{category}:{position}", "category": category, "name": name})

    def entries(section: str, prefix: str, fields: tuple[str, ...]) -> list[dict]:
        rows: list[dict] = []
        for index, match in enumerate(re.finditer(r"(?m)^###\s+(.+?)\s*$", _section(content, section))):
            body = _section(content, section)[match.end():]
            next_match = re.search(r"(?m)^###\s+", body)
            body = body[:next_match.start()] if next_match else body
            values = _subfields(body)
            row = {"id": f"{prefix}:{index}", "label": _text(match.group(1)), **{key: values.get(key, "") for key in fields}}
            if prefix == "experience":
                row["bullets"] = [_text(item) for item in re.findall(r"(?m)^\s*[-*]\s+(.+?)\s*$", values.get("activities_achievements", "")) if _text(item)]
                row["job_title"] = values.get("job_title", "")
                row["company"] = values.get("company", "")
                row["name"] = " · ".join(part for part in (row["job_title"], row["company"], row["label"]) if part)
            elif prefix == "education":
                row["name"] = " · ".join(part for part in (values.get("diploma", ""), values.get("institution", ""), row["label"]) if part)
            elif prefix == "certificate":
                row["name"] = " · ".join(part for part in (values.get("certificate", ""), values.get("institution", ""), row["label"]) if part)
            rows.append(row)
        return rows

    return {
        "profile_name": _field(content, "profile_name"),
        "contact": {key.removeprefix("profile_"): _field(content, key) for key in ("profile_phone", "profile_email", "profile_linkedin", "profile_project_portfolio", "profile_github")},
        "profile_job_title": _field(content, "profile_job_title"),
        "profile_text": _field(content, "profile_text"),
        "skills": skills,
        "experience": entries("working_experience", "experience", ("company", "job_title", "activities_achievements")),
        "projects": entries("selected_projects", "project", ("description", "technologies", "url")),
        "education": entries("education", "education", ("diploma", "institution", "major")),
        "certificates": entries("certificates", "certificate", ("institution", "certificate")),
        "references": entries("references", "reference", ("reference_job_title", "reference_company", "reference_linkedin")),
    }


def validate_recommendation(recommendation: dict[str, Any], inventory: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Remove IDs not present in the master profile; never accept free candidate facts."""
    warnings: list[str] = []
    allowed = {kind: {row["id"] for row in inventory[kind]} for kind in ("skills", "experience", "projects", "education", "certificates", "references")}
    result = dict(recommendation)
    for field, kind in (("selected_skills", "skills"), ("selected_experience_entries", "experience"), ("selected_projects", "projects"), ("selected_education", "education"), ("selected_certificates", "certificates"), ("selected_references", "references")):
        selected = [str(value) for value in result.get(field, [])]
        invalid = [value for value in selected if value not in allowed[kind]]
        if invalid:
            warnings.append(f"Ungültige Auswahl in {field}: {', '.join(invalid)}")
        result[field] = [value for value in selected if value in allowed[kind]]
    selected_categories = {item["category"] for item in inventory["skills"] if item["id"] in result["selected_skills"]}
    result["selected_skill_categories"] = [str(value) for value in result.get("selected_skill_categories", []) if str(value) in selected_categories]
    bullets = result.get("selected_experience_bullets", {})
    # Dify Studio supports arrays of fixed objects reliably, while a JSON map
    # with arbitrary property names can break its schema editor. Accept that
    # transport form and normalize it before applying the evidence check.
    if isinstance(bullets, list):
        bullets = {
            str(item.get("experience_id")): item.get("bullets") or []
            for item in bullets
            if isinstance(item, dict) and item.get("experience_id")
        }
    if not isinstance(bullets, dict):
        bullets = {}
    valid_bullets: dict[str, list[str]] = {}
    for entry in inventory["experience"]:
        entry_id = entry["id"]
        if entry_id not in result["selected_experience_entries"]:
            continue
        requested = [str(item) for item in bullets.get(entry_id, [])]
        valid_bullets[entry_id] = [item for item in requested if item in entry["bullets"]]
        if len(valid_bullets[entry_id]) != len(requested):
            warnings.append(f"Nicht belegte Bullet-Auswahl in {entry_id} wurde verworfen.")
    result["selected_experience_bullets"] = valid_bullets
    text = _text(str(result.get("recommended_profile_text") or ""))
    if not (40 <= len(text) <= 5_000):
        raise ApplicationError("Der Profiltext muss zwischen 40 und 5.000 Zeichen lang sein.", code="cv_recommendation_invalid", status_code=422)
    result["recommended_profile_text"] = text
    result["recommended_job_title"] = _text(str(result.get("recommended_job_title") or ""))[:500]
    if not result["recommended_job_title"]:
        raise ApplicationError("Der empfohlene Jobtitel fehlt.", code="cv_recommendation_invalid", status_code=422)
    result["include_references"] = bool(result.get("include_references"))
    return result, warnings


def render_cv_markdown(inventory: dict[str, Any], recommendation: dict[str, Any], language: str) -> str:
    labels = {"de": {"profile": "Profil", "skills": "Kompetenzen", "experience": "Berufserfahrung", "projects": "Ausgewählte Projekte", "education": "Ausbildung", "certificates": "Zertifikate", "references": "Referenzen"}, "en": {"profile": "Profile", "skills": "Skills", "experience": "Professional Experience", "projects": "Selected Projects", "education": "Education", "certificates": "Certifications", "references": "References"}}[language]
    selected = lambda kind, key: [item for item in inventory[kind] if item["id"] in recommendation.get(key, [])]
    lines = [f"# {inventory['profile_name']}", "", f"## {recommendation['recommended_job_title']}", ""]
    contact = [value for value in inventory["contact"].values() if value]
    if contact:
        lines += [" · ".join(contact), ""]
    lines += [f"## {labels['profile']}", "", recommendation["recommended_profile_text"], ""]
    skills = selected("skills", "selected_skills")
    if skills:
        lines += [f"## {labels['skills']}", ""]
        for category in recommendation.get("selected_skill_categories", []):
            names = [item["name"] for item in skills if item["category"] == category]
            if names:
                lines += [f"**{category.replace('_', ' ').title()}:** {', '.join(names)}", ""]
    experience = selected("experience", "selected_experience_entries")
    if experience:
        lines += [f"## {labels['experience']}", ""]
        for item in experience:
            lines += [f"### {item['job_title']}", f"**{item['label']} · {item['company']}**", ""]
            lines += [f"- {bullet}" for bullet in recommendation["selected_experience_bullets"].get(item["id"], [])] + [""]
    for kind, key, label, fields in (("projects", "selected_projects", labels["projects"], ("label", "description", "technologies", "url")), ("education", "selected_education", labels["education"], ("diploma", "institution", "major", "label")), ("certificates", "selected_certificates", labels["certificates"], ("certificate", "institution", "label"))):
        rows = selected(kind, key)
        if rows:
            lines += [f"## {label}", ""]
            for row in rows:
                lines += [f"### {row[fields[0]] or row['label']}"]
                if kind in {"education", "certificates"}:
                    lines += [f"**{' · '.join(part for part in (row['label'], row.get('institution', '')) if part)}**"]
                    lines += [row["major"]] if kind == "education" and row.get("major") else []
                    lines += [""]
                else:
                    lines += [row[field] for field in fields[1:] if row.get(field)] + [""]
    if recommendation.get("include_references"):
        rows = selected("references", "selected_references")
        if rows:
            lines += [f"## {labels['references']}", ""]
            for row in rows:
                lines += [f"### {row['label']}", *[row[field] for field in ("reference_job_title", "reference_company", "reference_linkedin") if row.get(field)], ""]
    return "\n".join(lines).strip() + "\n"
