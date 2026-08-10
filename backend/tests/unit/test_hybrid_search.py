from uuid import uuid4

from app.services.hybrid_search import RetrievalCandidate, merge_candidates


def test_merge_candidates_deduplicates_and_keeps_both_sources() -> None:
    evidence_id = uuid4()
    result = merge_candidates(
        [RetrievalCandidate(evidence_id, lexical_score=0.8)],
        [RetrievalCandidate(evidence_id, semantic_score=0.9)],
    )
    assert len(result) == 1
    assert result[0].retrieval_sources == {"lexical", "semantic"}
    assert result[0].lexical_score == 0.8
    assert result[0].semantic_score == 0.9


def test_merge_candidates_keeps_lexical_only_and_semantic_only() -> None:
    lexical_id, semantic_id = uuid4(), uuid4()
    result = merge_candidates(
        [RetrievalCandidate(lexical_id, lexical_score=1.0)],
        [RetrievalCandidate(semantic_id, semantic_score=0.7)],
    )
    assert {item.evidence_id for item in result} == {lexical_id, semantic_id}
