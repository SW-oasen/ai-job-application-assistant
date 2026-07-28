from dataclasses import dataclass

from playwright.async_api import (
    async_playwright,
    Browser,
    Error as PlaywrightError,
    Route,
    TimeoutError as PlaywrightTimeoutError,
)

from app.core.errors import ApplicationError
from app.importers.url_security import validate_public_url


@dataclass(frozen=True)
class BrowserImportResult:
    final_url: str
    content: str


class PlaywrightImporter:
    def __init__(
        self,
        *,
        timeout_seconds: float,
        max_bytes: int,
        user_agent: str,
    ) -> None:
        self.timeout_ms = int(timeout_seconds * 1000)
        self.max_bytes = max_bytes
        self.user_agent = user_agent

    async def fetch(self, url: str) -> BrowserImportResult:
        target_url = await validate_public_url(url)

        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                try:
                    return await self._fetch_page(browser, target_url)
                finally:
                    await browser.close()
        except ApplicationError:
            raise
        except PlaywrightTimeoutError as exception:
            raise ApplicationError(
                "The browser import exceeded the configured timeout.",
                code="browser_timeout",
                status_code=504,
            ) from exception
        except PlaywrightError as exception:
            raise ApplicationError(
                "The page could not be loaded in the browser.",
                code="browser_import_failed",
                status_code=502,
            ) from exception

    async def _fetch_page(self, browser: Browser, url: str) -> BrowserImportResult:
        context = await browser.new_context(
            user_agent=self.user_agent,
            service_workers="block",
        )
        page = await context.new_page()
        page.set_default_timeout(self.timeout_ms)
        await page.route("**/*", self._validate_request)

        try:
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.timeout_ms,
            )
            if response is not None and response.status >= 400:
                raise ApplicationError(
                    f"The source returned HTTP {response.status} in the browser.",
                    code="source_http_error",
                    status_code=502,
                    details={"source_status": response.status},
                )

            await page.wait_for_load_state("networkidle", timeout=min(self.timeout_ms, 10_000))
        except PlaywrightTimeoutError:
            # DOM content can still be usable when analytics or streaming requests
            # prevent the network from becoming fully idle.
            pass

        final_url = await validate_public_url(page.url)
        content = await page.content()
        if len(content.encode("utf-8")) > self.max_bytes:
            raise ApplicationError(
                "The rendered page exceeds the maximum allowed size.",
                code="source_too_large",
                status_code=413,
                details={"max_bytes": self.max_bytes},
            )
        await context.close()
        return BrowserImportResult(final_url=final_url, content=content)

    async def _validate_request(self, route: Route) -> None:
        try:
            await validate_public_url(route.request.url)
        except ApplicationError:
            try:
                await route.abort("blockedbyclient")
            except PlaywrightError:
                # The page may already have been closed after the main request
                # failed. This is not a second import error.
                pass
            return
        try:
            await route.continue_()
        except PlaywrightError:
            # Ignore requests still in flight while a failed page is closing.
            pass
