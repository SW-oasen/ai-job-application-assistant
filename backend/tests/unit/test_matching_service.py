from types import SimpleNamespace

from app.schemas.matching import EvidenceInput
from app.services.matching_service import (
    COMPANY_PATTERNS,
    StoredEvidence,
    _evaluate,
    _evaluate_target_fit,
    _first_metadata_match,
    _matching_recommendation,
    _nationality_evidence_input,
    _qualification_fit,
    _terms,
)


def test_target_fit_is_separate_and_uses_structured_preferences() -> None:
    job = SimpleNamespace(
        title="Machine Learning Engineer",
        location="Berlin",
        work_model="Hybrid",
        employment_type="Unbefristete Vollzeitstelle",
        normalized_content="Entwicklung von Machine-Learning-Anwendungen.",
    )
    company = SimpleNamespace(industry=None)
    profile = SimpleNamespace(
        career_goal="Machine Learning, Entwicklung von KI-Anwendungen",
        target_roles=["Data Scientist", "Machine Learning Engineer"],
        target_industries=[],
        target_locations=["Berlin"],
        preferred_work_models=["remote", "hybrid"],
        preferred_employment_types=["permanent"],
        deal_breakers=["Freiberuflich"],
    )

    activities = [
        SimpleNamespace(activity_text="Entwicklung von Machine-Learning-Anwendungen")
    ]
    result = _evaluate_target_fit(job, company, profile, activities)

    assert result["level"] == "strong"
    assert result["score"] == 100
    assert result["exclusions"][0]["status"] == "clear"


def test_target_fit_detects_structured_freelance_conflict() -> None:
    job = SimpleNamespace(
        title="AI Engineer",
        location="Berlin",
        work_model="Remote",
        employment_type="Freelance",
        normalized_content="Freelance AI project",
    )
    profile = SimpleNamespace(
        career_goal="KI-Anwendungsentwicklung",
        target_roles=["AI Engineer"],
        target_industries=[],
        target_locations=["Berlin"],
        preferred_work_models=["remote"],
        preferred_employment_types=["permanent"],
        deal_breakers=["Freiberuflich"],
    )

    result = _evaluate_target_fit(job, None, profile)

    assert result["level"] == "conflict"
    assert result["exclusions"][0]["status"] == "conflict"


def test_target_fit_matches_temporary_contract_with_minimum_duration() -> None:
    job = SimpleNamespace(
        title="Data Engineer",
        location="Berlin",
        work_model="Hybrid",
        employment_type="Vollzeit",
        contract_term="Temporary (2 Years)",
        normalized_content="",
    )
    profile = SimpleNamespace(
        career_goal="Data Engineering",
        target_roles=[], target_industries=[], target_locations=[],
        preferred_work_models=[], preferred_employment_types=["temporary"], deal_breakers=[],
        minimum_contract_duration_months=24,
    )

    result = _evaluate_target_fit(job, None, profile)

    employment = next(item for item in result["criteria"] if item["key"] == "employment_type")
    assert employment["status"] == "match"
    assert employment["actual"] == "Temporary (2 Years)"


def test_target_fit_rejects_temporary_contract_shorter_than_minimum() -> None:
    job = SimpleNamespace(
        title="Data Engineer",
        location="Berlin",
        work_model="Hybrid",
        employment_type="Vollzeit",
        contract_term="Temporary (1 Year)",
        normalized_content="",
    )
    profile = SimpleNamespace(
        career_goal="Data Engineering",
        target_roles=[], target_industries=[], target_locations=[],
        preferred_work_models=[], preferred_employment_types=["temporary"], deal_breakers=[],
        minimum_contract_duration_months=24,
    )

    result = _evaluate_target_fit(job, None, profile)

    employment = next(item for item in result["criteria"] if item["key"] == "employment_type")
    assert employment["status"] == "mismatch"
    assert employment["score"] == 0.0


def test_target_fit_accepts_permanent_when_both_contract_preferences_are_selected() -> None:
    job = SimpleNamespace(
        title="Data Engineer", location="Berlin", work_model="Hybrid",
        employment_type="Vollzeit", contract_term="unbefristet", normalized_content="",
    )
    profile = SimpleNamespace(
        career_goal="Data Engineering", target_roles=[], target_industries=[],
        target_locations=[], preferred_work_models=[],
        deal_breakers=[], preferred_employment_types=["permanent", "temporary"],
        minimum_contract_duration_months=24,
    )

    result = _evaluate_target_fit(job, None, profile)

    employment = next(item for item in result["criteria"] if item["key"] == "employment_type")
    assert employment["status"] == "match"


def test_target_fit_uses_activity_concepts_and_seniority() -> None:
    job = SimpleNamespace(
        title="Data Science & Machine Learning Engineer",
        location="Berlin",
        work_model=None,
        employment_type="Angestellte/r",
        normalized_content="Machine Learning und Datenanalyse",
        extracted_json={
            "seniority": {
                "level": "junior",
                "confidence": 0.95,
                "years_required": None,
                "signals": ["erste Berufserfahrung"],
            }
        },
    )
    profile = SimpleNamespace(
        career_goal="Machine Learning, Datenanalyse, Prozessautomatisierung und KI-Anwendungsentwicklung",
        target_roles=["Data Scientist", "Machine Learning Engineer"],
        target_industries=[],
        target_locations=["Berlin"],
        preferred_work_models=[],
        preferred_employment_types=["permanent"],
        deal_breakers=[],
    )
    activities = [
        SimpleNamespace(activity_text="Data Science, Machine Learning und Softwareentwicklung von Prototypen")
    ]

    result = _evaluate_target_fit(job, None, profile, activities, profile_seniority_years=4)

    assert result["level"] == "strong"
    assert next(item for item in result["criteria"] if item["key"] == "seniority")["status"] == "unknown"
    assert next(item for item in result["criteria"] if item["key"] == "employment_type")["status"] == "unknown"


def test_target_fit_uses_role_context_for_short_activity_headings() -> None:
    job = SimpleNamespace(
        title="Junior AI/ML Engineer, Data and Evaluation",
        location="Berlin",
        work_model="Hybrid",
        employment_type=None,
        normalized_content="",
        extracted_json={"seniority": {"level": "junior"}},
    )
    profile = SimpleNamespace(
        career_goal="Machine Learning, Datenanalyse, Prozessautomatisierung und KI-Anwendungsentwicklung",
        target_roles=["Machine Learning Engineer", "AI Engineer"],
        target_role_preferences=[
            {"role": "Machine Learning Engineer", "level": "Mid", "priority": 1},
            {"role": "AI Engineer", "level": "Mid", "priority": 1},
        ],
        target_industries=[],
        target_locations=["Berlin"],
        preferred_work_models=["hybrid"],
        preferred_employment_types=[],
        deal_breakers=[],
    )
    activities = [
        SimpleNamespace(activity_text="Curate Security Datasets"),
        SimpleNamespace(activity_text="Automate Benchmarks"),
        SimpleNamespace(activity_text="Run Experiments and Error Analysis"),
    ]

    result = _evaluate_target_fit(job, None, profile, activities)

    assert next(item for item in result["criteria"] if item["key"] == "activities")["status"] == "match"
    seniority = next(item for item in result["criteria"] if item["key"] == "seniority")
    assert seniority["actual"] == "Junior"
    assert seniority["status"] == "partial"


def test_target_fit_uses_full_advert_when_extracted_activities_are_noisy() -> None:
    job = SimpleNamespace(
        title="Software Engineer, Foundation",
        location="Berlin",
        work_model=None,
        employment_type="Vollzeit",
        normalized_content=(
            "Build agentic and AI infrastructure, including MCP servers, "
            "agent platforms, automated workflows, evaluation feedback loops "
            "and developer tooling."
        ),
        extracted_json={},
    )
    profile = SimpleNamespace(
        career_goal="KI-Anwendungsentwicklung und Prozessautomatisierung",
        target_roles=["AI Engineer"],
        target_industries=[],
        target_locations=["Berlin"],
        preferred_work_models=[],
        preferred_employment_types=["permanent"],
        deal_breakers=[],
    )
    activities = [
        SimpleNamespace(activity_text="Learning architecture by doing it"),
    ]

    result = _evaluate_target_fit(job, None, profile, activities)

    assert next(item for item in result["criteria"] if item["key"] == "activities")["status"] == "match"


def test_qualification_fit_weights_must_requirements_more_strongly() -> None:
    result = _qualification_fit(
        [
            {
                "requirement_id": "1",
                "requirement": "Python",
                "priority": "must",
                "match_level": "strong_match",
            },
            {
                "requirement_id": "2",
                "requirement": "Production ML",
                "priority": "must",
                "match_level": "gap",
            },
            {
                "requirement_id": "3",
                "requirement": "Cloud",
                "priority": "should",
                "match_level": "partial_match",
            },
            {
                "requirement_id": "4",
                "requirement": "Domain knowledge",
                "priority": "nice_to_have",
                "match_level": "transferable",
            },
        ]
    )

    assert result["score"] == 52
    assert result["level"] == "partial"
    assert result["achieved_points"] == 4.7
    assert result["possible_points"] == 9
    assert result["weighted_requirements"][0]["priority_weight"] == 3


def test_qualification_fit_without_requirements_is_unknown() -> None:
    result = _qualification_fit([])

    assert result["score"] is None
    assert result["level"] == "unknown"


def test_seniority_requirement_does_not_use_unlinked_skill_years() -> None:
    result = _evaluate(
        "seniority-1",
        "Mindestens 3 Jahre Berufserfahrung",
        set(),
        [
            StoredEvidence(
                evidence_id="skill-1",
                item=EvidenceInput(
                    source_name="profile:skill:1",
                    source_type="manual",
                    source_content='{"canonical_name":"Python","years_experience":4}',
                    label="Python",
                    evidence_text="Skill: Python; Jahre: 4",
                    experience_context="other",
                    keywords=["Python"],
                ),
            )
        ],
        category="experience",
        normalized_value="min_years:3",
    )

    assert result.match_level == "unknown"


def test_seniority_requirement_without_skill_scope_remains_unknown() -> None:
    result = _evaluate(
        "seniority-2",
        "Mindestens 5 Jahre Python Berufserfahrung",
        set(),
        [
            StoredEvidence(
                evidence_id="skill-2",
                item=EvidenceInput(
                    source_name="profile:skill-evidence:2",
                    source_type="manual",
                    source_content='{"canonical_name":"Python","years_experience":2}',
                    label="Python",
                    evidence_text="Skill: Python; Jahre: 2",
                    experience_context="professional",
                    keywords=["Python"],
                ),
            )
        ],
        category="experience",
        normalized_value="min_years:5",
    )

    assert result.match_level == "unknown"


def test_seniority_requirement_is_detected_in_english_legacy_text() -> None:
    result = _evaluate(
        "seniority-3",
        "5+ years of professional experience",
        set(),
        [],
        category="experience",
    )

    assert result.match_level == "unknown"
    assert "Erfahrungsjahre" in result.recommended_action


def test_matching_recommendation_encourages_two_strong_fits_without_must_gaps() -> None:
    recommendation = _matching_recommendation(
        {
            "score": 82,
            "weighted_requirements": [
                {"priority": "must", "match_level": "strong_match"}
            ],
        },
        {"score": 76, "level": "strong", "exclusions": []},
    )

    assert recommendation["verdict"] == "apply"
    assert recommendation["headline"] == "Bewerbung empfohlen"
    assert recommendation["requires_manual_review"] is False


def test_matching_recommendation_prioritizes_target_conflict() -> None:
    recommendation = _matching_recommendation(
        {"score": 95, "weighted_requirements": []},
        {
            "score": 90,
            "level": "conflict",
            "exclusions": [{"status": "conflict"}],
        },
    )

    assert recommendation["verdict"] == "deprioritize"
    assert recommendation["headline"] == "Nicht priorisieren"


def evidence(context: str, keywords: list[str]) -> StoredEvidence:
    return StoredEvidence(
        evidence_id="evidence-1",
        item=EvidenceInput(
            source_name="CV",
            source_type="cv",
            source_content="Profile content",
            label="AWS example",
            evidence_text="Built an AWS deployment",
            experience_context=context,
            keywords=keywords,
        ),
    )


def test_professional_evidence_can_produce_strong_match() -> None:
    result = _evaluate(
        "requirement-1",
        "AWS deployment",
        {"aws", "deployment"},
        [evidence("professional", ["aws", "deployment"])],
    )

    assert result.match_level == "strong_match"
    assert result.evidence[0].experience_context == "professional"


def test_documented_daily_agentic_coding_use_is_a_strong_match() -> None:
    result = _evaluate(
        "requirement-1",
        "Daily use of agentic coding tools (Claude Code, Codex, or similar)",
        {"daily", "agentic", "coding", "tools", "claude", "code", "codex"},
        [
            StoredEvidence(
                evidence_id="evidence-1",
                item=EvidenceInput(
                    source_name="profile:project:1",
                    source_type="manual",
                    source_content="Project evidence",
                    label="AI Job Application Assistant",
                    evidence_text="Daily use of Codex and Claude Code for implementation and review.",
                    experience_context="project",
                    keywords=["Codex", "Claude Code", "agentic coding"],
                ),
            )
        ],
    )

    assert result.match_level == "strong_match"


def test_extracts_company_from_indeed_company_link() -> None:
    content = (
        "# Data Analyst\n\n"
        "[DataSmart Point GmbH](https://de.indeed.com/cmp/Datasmart-Point-Gmbh)\n"
    )

    assert _first_metadata_match(content, COMPANY_PATTERNS) == "DataSmart Point GmbH"


def test_project_evidence_is_not_presented_as_professional() -> None:
    result = _evaluate(
        "requirement-1",
        "Production experience with AWS",
        {"production", "aws"},
        [evidence("project", ["aws"])],
    )

    assert result.match_level == "transferable"
    assert "not production experience" in result.recommended_action


def test_missing_evidence_produces_gap_without_citation() -> None:
    result = _evaluate(
        "requirement-1",
        "Kubernetes",
        {"kubernetes"},
        [],
    )

    assert result.match_level == "gap"
    assert result.evidence == []


def test_german_nationality_supports_nato_citizenship_requirement() -> None:
    nationality = _nationality_evidence_input("profile-1", "deutsch")
    result = _evaluate(
        "requirement-1",
        "NATO-Staatsangehörigkeit",
        {"nato", "staatsangehörigkeit"},
        [StoredEvidence(evidence_id="nationality-1", item=nationality)],
        category="other",
        keyword_terms={"nato", "staatsangehörigkeit"},
    )

    assert result.match_level == "strong_match"
    assert result.evidence[0].label == "Staatsangehörigkeit"
    assert "Deutschland ist NATO-Mitglied" in result.evidence[0].evidence_text


def test_nationality_evidence_excludes_contact_data() -> None:
    nationality = _nationality_evidence_input("profile-1", "deutsch")

    assert nationality.source_name == "profile:profile-1:nationality"
    assert "nationality" in nationality.source_content
    assert "email" not in nationality.source_content
    assert "phone" not in nationality.source_content


def test_german_nationality_supports_work_authorization_in_germany() -> None:
    nationality = _nationality_evidence_input("profile-1", "Deutsch")
    result = _evaluate(
        "requirement-1",
        "Uneingeschränkte Arbeitserlaubnis in Deutschland",
        {"arbeitserlaubnis", "deutschland"},
        [StoredEvidence(evidence_id="nationality-1", item=nationality)],
        category="other",
        keyword_terms={"arbeitserlaubnis", "deutschland"},
    )

    assert result.match_level == "strong_match"
    assert "keine Arbeitserlaubnis erforderlich" in result.evidence[0].evidence_text


def test_german_nationality_supports_residence_authorization_in_germany() -> None:
    nationality = _nationality_evidence_input("profile-1", "Deutsch")
    result = _evaluate(
        "requirement-1",
        "Aufenthaltserlaubnis in Deutschland",
        {"aufenthaltserlaubnis", "deutschland"},
        [StoredEvidence(evidence_id="nationality-1", item=nationality)],
        category="other",
        keyword_terms={"aufenthaltserlaubnis", "deutschland"},
    )

    assert result.match_level == "strong_match"
    assert "kein Aufenthaltstitel" in result.evidence[0].evidence_text


def test_missing_soft_skill_is_unknown_instead_of_gap() -> None:
    result = _evaluate(
        "requirement-1",
        "Self-motivated and able to work independently",
        {"self", "motivated", "work", "independently"},
        [],
        category="Soft skills",
    )

    assert result.match_level == "unknown"
    assert result.evidence == []
    assert "manually" in result.recommended_action


def test_explicit_alternative_keyword_matches_canonical_skill() -> None:
    result = _evaluate(
        "requirement-1",
        "Proficient in Python or Go",
        {"proficient", "python", "go"},
        [evidence("other", ["python"])],
        category="Programming Languages",
        keyword_terms={"python", "go"},
    )

    assert result.match_level == "partial_match"
    assert result.evidence[0].source_name == "CV"


def test_incidental_single_word_overlap_is_not_a_match() -> None:
    result = _evaluate(
        "requirement-1",
        "Supply chain logistics demand planning industry environment",
        {"supply", "chain", "logistics", "demand", "planning", "industry"},
        [evidence("professional", ["planning"])],
    )

    assert result.match_level == "gap"
    assert result.evidence == []
    assert result.confidence == 0.85


def test_multiple_skill_evidence_items_can_form_a_partial_match() -> None:
    result = _evaluate(
        "requirement-1",
        "Strong skills in Python, R, SQL and Power BI",
        {"python", "sql", "power", "bi"},
        [
            evidence("other", ["python"]),
            evidence("other", ["sql"]),
            evidence("other", ["power", "bi"]),
        ],
    )

    assert result.match_level == "partial_match"
    assert len(result.evidence) == 3


def test_multiple_components_without_professional_context_are_partial() -> None:
    result = _evaluate(
        "requirement-1",
        "Degree in data science with Python, SQL and professional project experience",
        {"degree", "data", "science", "python", "sql", "project", "experience"},
        [
            evidence("education", ["degree", "data", "science"]),
            evidence("other", ["python"]),
            evidence("other", ["sql"]),
        ],
    )

    assert result.match_level == "partial_match"
    assert "professional context is not fully documented" in result.explanation


def test_general_professional_experience_does_not_satisfy_required_role() -> None:
    result = _evaluate(
        "requirement-1",
        "Mehrere Jahre praktische Erfahrung als Data Engineer",
        {"mehrere", "jahre", "praktische", "data", "engineer"},
        [evidence("professional", ["Mehrere Jahre Berufserfahrung als Projektmanager"])],
    )
    assert result.match_level == "partial_match"
    assert "role or domain context" in result.explanation


def test_missing_cloud_evidence_is_a_gap_even_with_related_technical_evidence() -> None:
    result = _evaluate(
        "requirement-1",
        "Experience working with cloud platforms such as AWS",
        {"working", "cloud", "platforms", "aws"},
        [evidence("professional", ["Python backend services and SQL databases"])],
    )
    assert result.match_level == "gap"


def test_missing_financial_services_context_is_only_partial() -> None:
    result = _evaluate(
        "requirement-1",
        "Professional experience developing applications using Python in the financial services industry",
        {"professional", "developing", "applications", "python", "financial", "services", "industry"},
        [evidence("professional", ["Python backend applications in retail"])],
    )
    assert result.match_level == "partial_match"
    assert "industry or domain context" in result.explanation


def test_professional_evidence_for_one_explicit_alternative_is_strong() -> None:
    result = _evaluate(
        "requirement-1",
        "Experience in supply chain, logistics, or demand planning",
        {"supply", "chain", "logistics", "demand", "planning"},
        [evidence("professional", ["supply", "logistics", "orders"])],
    )

    assert result.match_level == "strong_match"
    assert result.evidence[0].experience_context == "professional"


def test_german_prediction_requirement_matches_english_forecasting_skill() -> None:
    requirement = "Entwurf genauer und skalierbarer Vorhersagealgorithmen"
    keywords = ["Entwurf genauer Vorhersagealgorithmen", "skalierbar"]
    result = _evaluate(
        "requirement-1",
        requirement,
        _terms(requirement, keywords),
        [evidence("other", ["Forecasting", "Vorhersagemodelle"])],
        category="technical_skill",
        keyword_terms=_terms("", keywords),
    )

    assert result.match_level == "partial_match"
    assert result.evidence[0].label == "AWS example"


def test_german_raw_data_requirement_matches_data_cleaning_and_eda() -> None:
    requirement = (
        "Analyse von Rohdaten und Bewertung der Qualit\u00e4t sowie Bereinigung "
        "und Strukturierung f\u00fcr die nachgeschaltete Verarbeitung"
    )
    keywords = [
        "Analyse von Rohdaten",
        "Bewertung der Qualit\u00e4t, Bereinigung und Strukturierung",
    ]
    result = _evaluate(
        "requirement-1",
        requirement,
        _terms(requirement, keywords),
        [
            evidence(
                "other",
                ["Data Cleaning", "Datenbereinigung", "Datenqualit\u00e4t"],
            ),
            evidence(
                "other",
                ["Exploratory Data Analysis", "Rohdatenanalyse"],
            ),
        ],
        category="technical_skill",
        keyword_terms=_terms("", keywords),
    )

    assert result.match_level == "partial_match"
    assert len(result.evidence) == 2
