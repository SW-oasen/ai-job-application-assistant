from app.schemas.matching import EvidenceInput
from app.services.matching_service import StoredEvidence, _has_cloud_platform_evidence


def _evidence(text: str) -> StoredEvidence:
    return StoredEvidence(EvidenceInput(source_name="project", source_type="portfolio", source_content="{}", label="Test", evidence_text=text, experience_context="project", keywords=[]), "evidence-1")


def test_local_only_cloud_wording_is_not_cloud_provider_evidence() -> None:
    assert not _has_cloud_platform_evidence([_evidence("Runs fully locally without a cloud API.")])


def test_named_cloud_provider_is_cloud_provider_evidence() -> None:
    assert _has_cloud_platform_evidence([_evidence("Deployed workloads on AWS using S3 and Lambda.")])
