"""
PlaywrightArkhamClient — Arkham API client using a real browser (patchright).

Inherits ALL 50+ API methods from ArkhamClient.
Only the transport layer (_request, __aenter__, __aexit__) is overridden.

Key differences from AiohttpClient:
  - Cookies are set on the browser context (browser sends them automatically).
    Setting Cookie in fetch() headers is blocked by browsers.
  - page.goto() is called ONCE on intel.arkm.com — patchright solves the
    Cloudflare challenge there; cf_clearance is set on .arkm.com domain and
    is therefore valid for api.arkm.com too.
  - Subsequent requests use page.evaluate(fetch(..., credentials:'include'))
    so cf_clearance and session cookies are sent on cross-origin calls to
    api.arkm.com.
  - JSON is parsed on the Python side for reliable error handling.
"""

import json as _json
import logging
import time
from typing import Any, Optional
from urllib.parse import urlencode

from ..client import ArkhamAPIError, ArkhamClient
from .playwright_driver import PlaywrightWebDriverHttp

BROWSER_TIMEOUT_MS = 60_000

logger = logging.getLogger(__name__)


async def _solve_cloudflare_challenge(page, *, timeout: int) -> None:
    """
    Attempt to automatically pass a Cloudflare Turnstile challenge.

    Cloudflare shows two types of challenges:
      1. Pure JS challenge — resolves on its own, no click needed.
      2. Turnstile — shows an iframe with a "Verify you are human" checkbox.

    We try to click the checkbox inside the Turnstile iframe.
    If not found, we fall back to waiting for the title to change.
    """
    import asyncio as _asyncio

    # Give the pure JS challenge a chance to resolve on its own first.
    try:
        await page.wait_for_function(
            "() => !document.title.includes('Just a moment')",
            timeout=5_000,
        )
        await page.wait_for_load_state("load", timeout=timeout)
        return
    except Exception:
        pass  # Didn't auto-resolve — try clicking the Turnstile checkbox.

    logger.info("Cloudflare challenge detected, attempting auto-click...")

    # Cloudflare Turnstile renders inside an iframe whose src contains
    # "challenges.cloudflare.com". Inside that iframe there is a checkbox.
    try:
        cf_frame_handle = await page.wait_for_selector(
            "iframe[src*='challenges.cloudflare.com']",
            timeout=10_000,
        )
        if cf_frame_handle:
            cf_frame = await cf_frame_handle.content_frame()
            if cf_frame:
                checkbox = await cf_frame.wait_for_selector(
                    "input[type='checkbox']",
                    timeout=8_000,
                )
                if checkbox:
                    # Human-like: small random delay before clicking.
                    await _asyncio.sleep(0.5)
                    await checkbox.click()
                    logger.info("Clicked Cloudflare Turnstile checkbox.")
    except Exception as exc:
        logger.warning("Could not auto-click Cloudflare checkbox: %s", exc)

    # Wait for challenge to clear regardless of whether click succeeded.
    await page.wait_for_function(
        "() => !document.title.includes('Just a moment')",
        timeout=timeout,
    )
    await page.wait_for_load_state("load", timeout=timeout)


def _parse_cookie_header(cookie_str: str, domain: str = ".arkm.com") -> list[dict]:
    """Convert 'name=value; name2=value2' string into Playwright cookie dicts."""
    cookies = []
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" not in part:
            continue
        name, _, value = part.partition("=")
        cookies.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": domain,
            "path": "/",
        })
    return cookies


class PlaywrightArkhamClient(ArkhamClient):
    """
    Drop-in replacement for ArkhamClient that routes all HTTP calls
    through a real Chromium browser (via patchright/Playwright).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cookie: Optional[str] = None,
        base_url: str = "https://api.arkm.com",
        headless: bool = True,
        timeout_ms: int = BROWSER_TIMEOUT_MS,
    ):
        super().__init__(api_key=api_key, cookie=cookie, base_url=base_url)
        self._driver = PlaywrightWebDriverHttp(
            timeout=timeout_ms,
            headless=headless,
        )

    async def __aenter__(self) -> "PlaywrightArkhamClient":
        # Browser starts lazily on first request — keeps MCP handshake fast.
        return self

    async def __aexit__(self, *_) -> None:
        await self._driver.close()

    async def _init_browser(self) -> None:
        """Launch browser and solve Cloudflare on first use."""
        if self._driver._prepared_map.get("browser"):
            return
        browser_ctx = await self._driver.prepare_browser()
        if self.cookie:
            await browser_ctx.add_cookies(
                _parse_cookie_header(self.cookie, domain=".arkm.com")
            )
        page = await self._driver.get_page(browser_ctx)
        await page.goto(
            "https://intel.arkm.com",
            wait_until="load",
            timeout=self._driver.timeout,
        )
        title = await page.title()
        if "Just a moment" in title:
            await _solve_cloudflare_challenge(page, timeout=self._driver.timeout)

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
        rate_limited: bool = False,
    ) -> Any:
        """Override transport: cross-origin fetch with credentials from intel.arkm.com."""
        if rate_limited:
            await self._slow_limiter.acquire()

        await self._init_browser()

        url = self._url(path)
        full_url = f"{url}?{urlencode(params)}" if params else url

        request_headers: dict[str, str] = {
            "X-Payload": self.generate_hash(url),
            "X-Timestamp": str(int(time.time())),
        }
        if self.api_key:
            request_headers["API-Key"] = self.api_key

        browser_ctx = await self._driver.prepare_browser()
        page = await self._driver.get_page(browser_ctx)

        # credentials:'include' sends cf_clearance (set on .arkm.com) along with
        # the cross-origin request from intel.arkm.com to api.arkm.com.
        body_js = f"body: JSON.stringify({_json.dumps(json)})," if json else ""
        js = f"""async () => {{
            const resp = await fetch({_json.dumps(full_url)}, {{
                method: {_json.dumps(method)},
                headers: {_json.dumps(request_headers)},
                credentials: 'include',
                {body_js}
            }});
            const text = await resp.text();
            return {{ status: resp.status, text }};
        }}"""

        result = await page.evaluate(js)
        status: int = result["status"]
        raw: str = result["text"]

        try:
            data = _json.loads(raw)
        except _json.JSONDecodeError:
            raise ArkhamAPIError(status, raw[:300])

        if status >= 400:
            msg = data.get("message") or data.get("error") or str(data)
            raise ArkhamAPIError(status, msg)

        return data
