from typing import Literal

SkillCategory = Literal[
    "programming_languages",
    "frameworks_libraries",
    "data_ai_ml",
    "databases",
    "cloud_devops",
    "tools_platforms",
    "methods",
    "soft_skills",
    "domain_knowledge",
    "natural_languages",
    "other",
]
SkillLevel = Literal["basic", "intermediate", "advanced", "expert"]

SKILL_CATEGORIES = [
    {"value": "programming_languages", "label_de": "Programmiersprachen", "label_en": "Programming languages"},
    {"value": "frameworks_libraries", "label_de": "Frameworks & Bibliotheken", "label_en": "Frameworks & libraries"},
    {"value": "data_ai_ml", "label_de": "Daten, KI & Machine Learning", "label_en": "Data, AI & machine learning"},
    {"value": "databases", "label_de": "Datenbanken", "label_en": "Databases"},
    {"value": "cloud_devops", "label_de": "Cloud & DevOps", "label_en": "Cloud & DevOps"},
    {"value": "tools_platforms", "label_de": "Tools & Plattformen", "label_en": "Tools & platforms"},
    {"value": "methods", "label_de": "Methoden & Prozesse", "label_en": "Methods & processes"},
    {"value": "soft_skills", "label_de": "Soziale Kompetenzen", "label_en": "Soft skills"},
    {"value": "domain_knowledge", "label_de": "Fach- & Branchenwissen", "label_en": "Domain knowledge"},
    {"value": "natural_languages", "label_de": "Sprachen", "label_en": "Languages"},
    {"value": "other", "label_de": "Sonstiges", "label_en": "Other"},
]

SKILL_LEVELS = [
    {"value": "basic", "label_de": "Grundkenntnisse", "label_en": "Basic"},
    {"value": "intermediate", "label_de": "Gute Kenntnisse", "label_en": "Intermediate"},
    {"value": "advanced", "label_de": "Fortgeschritten", "label_en": "Advanced"},
    {"value": "expert", "label_de": "Experte / Expertin", "label_en": "Expert"},
]


def normalize_skill_category(source: str | None) -> SkillCategory:
    value = (source or "").casefold()
    if any(term in value for term in ("program", "language", "sprache")):
        return "programming_languages"
    if any(term in value for term in ("framework", "library", "bibliothek")):
        return "frameworks_libraries"
    if any(term in value for term in ("data", "daten", "machine", " ai", "ki", "ml")):
        return "data_ai_ml"
    if any(term in value for term in ("database", "datenbank", "sql")):
        return "databases"
    if any(term in value for term in ("cloud", "devops", "deployment", "infra")):
        return "cloud_devops"
    if any(term in value for term in ("tool", "platform", "werkzeug")):
        return "tools_platforms"
    if any(term in value for term in ("method", "prozess", "agile", "scrum")):
        return "methods"
    if any(term in value for term in ("soft", "social", "kommunikation", "leadership")):
        return "soft_skills"
    if any(term in value for term in ("domain", "industry", "fach", "branche")):
        return "domain_knowledge"
    return "other"


def normalize_skill_level(source: str | None) -> SkillLevel | None:
    value = (source or "").casefold()
    if not value:
        return None
    if any(term in value for term in ("native", "mother", "mutter", "c2", "expert")):
        return "expert"
    if any(term in value for term in ("advanced", "fortgeschritten", "fluent", "c1")):
        return "advanced"
    if any(term in value for term in ("intermediate", "mittel", "good", "gut", "b1", "b2")):
        return "intermediate"
    return "basic"
