from dataclasses import dataclass
from typing import Any

import httpx

from app.core.errors import ApplicationError


@dataclass(frozen=True)
class MinerUResult:
    markdown: str
    task_id: str | None


class MinerUClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        backend: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.backend = backend
        self.transport = transport

    async def parse_pdf(self, *, content: bytes, filename: str) -> MinerUResult:
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/file_parse",
                    files={"files": (filename, content, "application/pdf")},
                    data={
                        "backend": self.backend,
                        "parse_method": "ocr",
                        "return_md": "true",
                        "return_middle_json": "false",
                        "return_model_output": "false",
                        "return_content_list": "false",
                        "return_images": "false",
                    },
                )
        except (httpx.TimeoutException, httpx.NetworkError) as exception:
            raise ApplicationError(
                "MinerU is unavailable or exceeded its processing timeout.",
                code="mineru_unavailable",
                status_code=502,
            ) from exception

        if response.status_code >= 400:
            raise ApplicationError(
                f"MinerU returned HTTP {response.status_code}.",
                code="mineru_error",
                status_code=502,
                details={"source_status": response.status_code},
            )

        try:
            payload: dict[str, Any] = response.json()
        except ValueError as exception:
            raise ApplicationError(
                "MinerU returned an invalid response.",
                code="mineru_invalid_response",
                status_code=502,
            ) from exception

        results = payload.get("results")
        if not isinstance(results, dict) or not results:
            raise self._missing_markdown_error()
        first_result = next(iter(results.values()))
        markdown = first_result.get("md_content") if isinstance(first_result, dict) else None
        if not isinstance(markdown, str) or not markdown.strip():
            raise self._missing_markdown_error()
        return MinerUResult(markdown=markdown.strip(), task_id=payload.get("task_id"))

    @staticmethod
    def _missing_markdown_error() -> ApplicationError:
        return ApplicationError(
            "MinerU returned no Markdown content.",
            code="mineru_invalid_response",
            status_code=502,
        )

