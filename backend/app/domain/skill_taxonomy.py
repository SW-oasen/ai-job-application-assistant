from typing import Literal

SkillCategory = Literal[
    "programming_languages",
    "software_development_apis",
    "frontend_development",
    "data_engineering",
    "ai_agents",
    "machine_learning_predictive_analytics",
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
    {
        "value": "programming_languages",
        "label_de": "Programmiersprachen",
        "label_en": "Programming languages",
    },
    {
        "value": "software_development_apis",
        "label_de": "Softwareentwicklung & APIs",
        "label_en": "Software development & APIs",
    },
    {
        "value": "frontend_development",
        "label_de": "Frontend-Entwicklung",
        "label_en": "Frontend development",
    },
    {"value": "data_engineering", "label_de": "Data Engineering", "label_en": "Data engineering"},
    {"value": "ai_agents", "label_de": "KI & Agentensysteme", "label_en": "AI & agent systems"},
    {
        "value": "machine_learning_predictive_analytics",
        "label_de": "Machine Learning & Predictive Analytics",
        "label_en": "Machine learning & predictive analytics",
    },
    {"value": "databases", "label_de": "Datenbanken", "label_en": "Databases"},
    {"value": "cloud_devops", "label_de": "Cloud & DevOps", "label_en": "Cloud & DevOps"},
    {
        "value": "tools_platforms",
        "label_de": "Tools & Plattformen",
        "label_en": "Tools & platforms",
    },
    {"value": "methods", "label_de": "Methoden & Prozesse", "label_en": "Methods & processes"},
    {"value": "soft_skills", "label_de": "Soziale Kompetenzen", "label_en": "Soft skills"},
    {
        "value": "domain_knowledge",
        "label_de": "Fach- & Branchenwissen",
        "label_en": "Domain knowledge",
    },
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
    if any(term in value for term in ("react", "angular", "vue", "frontend")):
        return "frontend_development"
    if any(
        term in value
        for term in ("agent", "langchain", "llm", "openai", "generative", "prompt")
    ):
        return "ai_agents"
    if any(
        term in value
        for term in ("machine", "predict", "forecast", "scikit", "pytorch", "tensorflow")
    ):
        return "machine_learning_predictive_analytics"
    if any(term in value for term in ("data", "daten", "etl", "pipeline", "airflow", "dbt")):
        return "data_engineering"
    if any(term in value for term in ("framework", "library", "bibliothek", "api", "backend")):
        return "software_development_apis"
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
