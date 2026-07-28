from dataclasses import dataclass
from urllib.parse import urljoin

import httpx

from app.core.errors import ApplicationError
from app.importers.url_security import validate_public_url

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
ALLOWED_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}


@dataclass(frozen=True)
class HttpImportResult:
    final_url: str
    content: str
    content_type: str


class HttpImporter:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_bytes: int,
        max_redirects: int,
        user_agent: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects
        self.user_agent = user_agent
        self.transport = transport

    async def fetch(self, url: str) -> HttpImportResult:
        current_url = await validate_public_url(url)
        timeout = httpx.Timeout(self.timeout_seconds)

        try:
            async with httpx.AsyncClient(
                follow_redirects=False,
                timeout=timeout,
                transport=self.transport,
                headers={"User-Agent": self.user_agent, "Accept": "text/html,text/plain"},
            ) as client:
                for redirect_count in range(self.max_redirects + 1):
                    async with client.stream("GET", current_url) as response:
                        if response.status_code in REDIRECT_STATUSES:
                            location = response.headers.get("location")
                            if not location:
                                raise ApplicationError(
                                    "The server returned a redirect without a destination.",
                                    code="invalid_redirect",
                                    status_code=502,
                                )
                            if redirect_count >= self.max_redirects:
                                raise ApplicationError(
                                    "The URL exceeded the redirect limit.",
                                    code="too_many_redirects",
                                    status_code=422,
                                )
                            current_url = await validate_public_url(
                                urljoin(str(response.url), location)
                            )
                            continue

                        if response.status_code >= 400:
                            raise ApplicationError(
                                f"The source returned HTTP {response.status_code}.",
                                code="source_http_error",
                                status_code=502,
                                details={"source_status": response.status_code},
                            )

                        content_type = (
                            response.headers.get("content-type", "").split(";")[0].lower()
                        )
                        if content_type not in ALLOWED_CONTENT_TYPES:
                            raise ApplicationError(
                                "The URL did not return supported HTML or text content.",
                                code="unsupported_content_type",
                                status_code=415,
                                details={"content_type": content_type or None},
                            )

                        declared_length = response.headers.get("content-length")
                        if declared_length:
                            try:
                                if int(declared_length) > self.max_bytes:
                                    raise self._too_large_error()
                            except ValueError:
                                pass

                        body = bytearray()
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > self.max_bytes:
                                raise self._too_large_error()

                        encoding = response.encoding or "utf-8"
                        return HttpImportResult(
                            final_url=current_url,
                            content=body.decode(encoding, errors="replace"),
                            content_type=content_type,
                        )
        except ApplicationError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exception:
            raise ApplicationError(
                "The source could not be downloaded within the configured limits.",
                code="source_unavailable",
                status_code=502,
            ) from exception

        raise ApplicationError(
            "The source could not be downloaded.",
            code="source_unavailable",
            status_code=502,
        )

    def _too_large_error(self) -> ApplicationError:
        return ApplicationError(
            "The source exceeds the maximum allowed download size.",
            code="source_too_large",
            status_code=413,
            details={"max_bytes": self.max_bytes},
        )
