from app.schemas.matching import EvidenceInput
from app.services.matching_service import StoredEvidence, _evaluate, _terms


def _evidence(text: str, *, context: str = "professional", keywords: list[str] | None = None) -> list[StoredEvidence]:
    item = EvidenceInput(
        source_name="Baseline CV",
        source_type="cv",
        source_content="baseline",
        label="Berufsstation",
        evidence_text=text,
        experience_context=context,
        keywords=keywords or [],
    )
    return [StoredEvidence(item=item, evidence_id="evidence-1")]


def test_baseline_exact_skill_match_is_strong() -> None:
    result = _evaluate(
        "r1", "PostgreSQL", _terms("PostgreSQL", []), _evidence("PostgreSQL"),
    )
    assert result.match_level == "strong_match"


def test_baseline_related_wording_is_found_when_keyword_is_present() -> None:
    result = _evaluate(
        "r1",
        "automatisierte Tests",
        _terms("automatisierte Tests", ["Testautomatisierung"]),
        _evidence("Entwicklung der Testautomatisierung der M2M-Kommunikationsschnittstellen"),
        keyword_terms=_terms("", ["Testautomatisierung"]),
    )
    assert result.match_level in {"strong_match", "partial_match"}
    assert result.evidence


def test_baseline_unrelated_technology_is_not_an_exact_match() -> None:
    result = _evaluate(
        "r1", "Angular", _terms("Angular", []), _evidence("React und TypeScript"),
    )
    assert result.match_level in {"gap", "transferable", "partial_match"}
    assert result.match_level != "strong_match"


def test_baseline_missing_evidence_is_gap() -> None:
    result = _evaluate("r1", "E2E-Testing", _terms("E2E-Testing", []), _evidence("Python"))
    assert result.match_level == "gap"


def test_semantic_only_candidate_is_not_direct_match() -> None:
    result = _evaluate(
        "r1",
        "Angular",
        _terms("Angular", []),
        _evidence("React and TypeScript"),
        semantic_candidate_ids={"evidence-1"},
    )
    assert result.match_level in {"partial_match", "transferable"}
    assert result.match_level != "strong_match"


def test_baseline_compound_requirement_can_be_partial() -> None:
    result = _evaluate(
        "r1",
        "Angular und TypeScript",
        _terms("Angular und TypeScript", []),
        _evidence("TypeScript in mehreren Projekten"),
    )
    assert result.match_level in {"partial_match", "transferable"}
