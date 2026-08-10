import pytest
import httpx
import json

from app.services.embedding_service import OpenAICompatibleEmbeddingProvider, build_evidence_embedding_text, validate_batch, validate_embedding


def test_validate_embedding_accepts_configured_dimension() -> None:
    assert validate_embedding([1, 0.5, 0], dimension=3) == [1.0, 0.5, 0.0]


def test_build_evidence_embedding_text_includes_context() -> None:
    assert build_evidence_embedding_text(
        label="Senior Engineer", evidence_text="Built test automation", source_name="Acme"
    ) == "Evidence: Built test automation\nType: Senior Engineer\nSource: Acme"


def test_validate_embedding_rejects_wrong_dimension() -> None:
    with pytest.raises(ValueError, match="Expected embedding dimension 3"):
        validate_embedding([1, 0], dimension=3)


def test_validate_batch_rejects_wrong_count() -> None:
    with pytest.raises(ValueError, match="Expected 2 embeddings"):
        validate_batch([[1, 0]], expected_count=2, dimension=2)


def test_validate_batch_validates_each_vector() -> None:
    with pytest.raises(ValueError, match="Expected embedding dimension 2"):
        validate_batch([[1, 0], [1]], expected_count=2, dimension=2)


def test_openai_compatible_provider_sends_batch_and_sorts_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/embeddings"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert json.loads(request.content)["input"] == ["one", "two"]
        return httpx.Response(200, json={"data": [
            {"index": 1, "embedding": [0, 1]},
            {"index": 0, "embedding": [1, 0]},
        ]})

    provider = OpenAICompatibleEmbeddingProvider(
        base_url="https://embedding.test/v1", api_key="test-key", model="test", dimension=2,
        client=httpx.Client(transport=httpx.MockTransport(handler), base_url="https://embedding.test/v1"),
    )
    assert provider.embed_batch(["one", "two"]) == [[1.0, 0.0], [0.0, 1.0]]
