import httpx
import pytest

from app.core.errors import ApplicationError
from app.importers.mineru_client import MinerUClient


@pytest.mark.asyncio
async def test_parses_current_mineru_response_shape() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={
                "task_id": "task-123",
                "results": {"job": {"md_content": "# Data Engineer\n\nJob text"}},
            },
        )
    )
    client = MinerUClient(
        base_url="http://mineru-api:8000",
        timeout_seconds=10,
        backend="pipeline",
        transport=transport,
    )

    result = await client.parse_pdf(content=b"%PDF-test", filename="job.pdf")

    assert result.markdown == "# Data Engineer\n\nJob text"
    assert result.task_id == "task-123"


@pytest.mark.asyncio
async def test_rejects_response_without_markdown() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"results": {"job": {}}})
    )
    client = MinerUClient(
        base_url="http://mineru-api:8000",
        timeout_seconds=10,
        backend="pipeline",
        transport=transport,
    )

    with pytest.raises(ApplicationError) as error:
        await client.parse_pdf(content=b"%PDF-test", filename="job.pdf")

    assert error.value.code == "mineru_invalid_response"

