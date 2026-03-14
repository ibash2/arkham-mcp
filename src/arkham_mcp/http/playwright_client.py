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
import time
from typing import Any, Optional
from urllib.parse import urlencode

from ..client import ArkhamAPIError, ArkhamClient
from .playwright_driver import PlaywrightWebDriverHttp

BROWSER_TIMEOUT_MS = 60_000


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
        headless: bool = False,
        timeout_ms: int = BROWSER_TIMEOUT_MS,
    ):
        super().__init__(api_key=api_key, cookie=cookie, base_url=base_url)
        self._driver = PlaywrightWebDriverHttp(
            timeout=timeout_ms,
            headless=headless,
        )

    async def __aenter__(self) -> "PlaywrightArkhamClient":
        browser_ctx = await self._driver.prepare_browser()

        # Set cookies on the browser context — browser sends them automatically.
        # We CANNOT set Cookie in fetch() headers (blocked by browser security).
        if self.cookie:
            await browser_ctx.add_cookies(
                _parse_cookie_header(self.cookie, domain=".arkm.com")
            )

        # Navigate to intel.arkm.com (the UI) — patchright handles the Cloudflare
        # challenge there. Cloudflare sets cf_clearance on domain=.arkm.com, so it
        # is valid for api.arkm.com requests made later with credentials:'include'.
        page = await self._driver.get_page(browser_ctx)
        await page.goto(
            "https://intel.arkm.com",
            wait_until="load",
            timeout=self._driver.timeout,
        )

        # If Cloudflare shows a JS challenge, wait for it to be resolved.
        title = await page.title()
        if "Just a moment" in title:
            await page.wait_for_function(
                "() => !document.title.includes('Just a moment')",
                timeout=self._driver.timeout,
            )
            await page.wait_for_load_state("load", timeout=self._driver.timeout)

        return self

    async def __aexit__(self, *_) -> None:
        await self._driver.close()

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

        url = self._url(path)
        full_url = f"{url}?{urlencode(params)}" if params else url

        # Payload hash headers (same as aiohttp client).
        # Cookie is NOT set here — browser sends cf_clearance automatically
        # because credentials:'include' is set on the fetch call.
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
