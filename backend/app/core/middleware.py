import contextvars
import logging
import time
from urllib.parse import urlparse
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="-",
)
logger = logging.getLogger("app.requests")

_BROWSER_CAPTURE_PATH = "/imports/browser-capture"


def _browser_capture_cors_headers(origin: str | None) -> dict[str, str]:
    """Allow a bookmarklet on a public job portal to send its rendered page.

    Some portals use Cross-Origin-Opener-Policy, which deliberately removes a
    popup's ``window.opener``.  The bookmarklet therefore submits directly to
    the local API instead of relying on a receiver popup.
    """
    parsed = urlparse(origin or "")
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return {}
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, X-Browser-Capture",
        # Chromium sends this preflight requirement for a public page talking
        # to the loopback service.
        "Access-Control-Allow-Private-Network": "true",
        "Access-Control-Max-Age": "600",
        "Vary": "Origin",
    }


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        cors_headers = (
            _browser_capture_cors_headers(request.headers.get("Origin"))
            if request.url.path == _BROWSER_CAPTURE_PATH
            else {}
        )
        if request.method == "OPTIONS" and cors_headers:
            return Response(status_code=204, headers=cors_headers)

        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        token = request_id_context.set(request_id)
        started_at = time.perf_counter()

        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers.update(cors_headers)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "request_completed method=%s path=%s status_code=%s duration_ms=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
            )
            return response
        finally:
            request_id_context.reset(token)
