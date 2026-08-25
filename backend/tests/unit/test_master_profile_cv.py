from app.services.master_profile_cv import parse_master_profile, render_cv_markdown, validate_recommendation


MASTER = """# profile_name
Ada Example
## profile_job_title
Data Engineer
## profile_text
Experienced engineer with Python and data pipelines.
## skills
### data_engineering
- Python
- ETL Pipelines
## working_experience
### 2024-01 – 2025-01
#### company
Example GmbH
#### job_title
Data Engineer
#### activities_achievements
- Built Python data pipelines
## education
### 2020-01 – 2023-01
#### diploma
MSc Computer Science
#### institution
Example University
## certificates
### 2024
#### institution
Example Academy
#### certificate
Data Engineering
## references
### Jane Doe
#### reference_company
Example GmbH
## selected_projects
### Pipeline Project
#### description
Built an ETL pipeline.
#### technologies
- Python
"""


def test_recommendation_only_keeps_master_profile_selections() -> None:
    inventory = parse_master_profile(MASTER)
    recommendation, warnings = validate_recommendation(
        {
            "recommended_job_title": "Data Engineer",
            "recommended_profile_text": "Experienced engineer with Python and data pipelines for reliable data products.",
            "selected_skill_categories": ["data_engineering", "invented"],
            "selected_skills": ["skill:data_engineering:0", "skill:invented:0"],
            "selected_experience_entries": ["experience:0"],
            "selected_experience_bullets": {"experience:0": ["Built Python data pipelines", "Invented achievement"]},
            "selected_projects": ["project:0", "project:99"],
            "selected_education": ["education:0"],
            "selected_certificates": ["certificate:0"],
            "selected_references": ["reference:0"],
            "include_references": True,
        }, inventory
    )
    assert recommendation["selected_skills"] == ["skill:data_engineering:0"]
    assert recommendation["selected_experience_bullets"] == {"experience:0": ["Built Python data pipelines"]}
    assert recommendation["selected_projects"] == ["project:0"]
    assert warnings


def test_renderer_uses_source_bullets_and_localized_sections() -> None:
    inventory = parse_master_profile(MASTER)
    recommendation, _ = validate_recommendation(
        {
            "recommended_job_title": "Data Engineer",
            "recommended_profile_text": "Experienced engineer with Python and data pipelines for reliable data products.",
            "selected_skill_categories": ["data_engineering"],
            "selected_skills": ["skill:data_engineering:0"],
            "selected_experience_entries": ["experience:0"],
            "selected_experience_bullets": {"experience:0": ["Built Python data pipelines"]},
            "selected_projects": ["project:0"], "selected_education": ["education:0"],
            "selected_certificates": [], "selected_references": [], "include_references": False,
        }, inventory
    )
    rendered = render_cv_markdown(inventory, recommendation, "en")
    assert "## Professional Experience" in rendered
    assert "- Built Python data pipelines" in rendered
    assert "Invented" not in rendered
