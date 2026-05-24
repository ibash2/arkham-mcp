import asyncio
import logging
import os
from dataclasses import dataclass, field
from urllib.parse import urlencode

from patchright.async_api import PlaywrightContextManager  # type: ignore
from patchright.async_api import BrowserContext, Page, Route

logger = logging.getLogger("webdriver")


@dataclass
class Response:
    status_code: int
    text: str
    data: dict

    def json(self) -> dict:
        return self.data


@dataclass
class PlaywrightWebDriverHttp:
    cookie: dict = field(default_factory=dict, kw_only=True)
    headers: dict = field(default_factory=dict, kw_only=True)
    timeout: int = field(default_factory=lambda: 5000, kw_only=True)
    headless: bool = field(default=True, kw_only=True)
    proxy: str | None = field(default=None, kw_only=True)
    _prepared_map: dict = field(default_factory=dict, kw_only=True)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, kw_only=True)

    def _make_query_string(self, params: dict) -> str:
        return urlencode(params)

    def _resolve_proxy(self) -> str | None:
        if self.proxy:
            return self.proxy
        for var in ("ALL_PROXY", "all_proxy", "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy"):
            val = os.environ.get(var, "").strip()
            if val:
                return val
        return None

    async def prepare_browser(self) -> BrowserContext:
        browser = self._prepared_map.get("browser")
        if not browser:
            context = await PlaywrightContextManager().start()
            launch_args = [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--lang=ru-RU,ru;q=0.9",
                "--disable-sync",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-blink-features=AutomationControlled",
            ]
            resolved_proxy = self._resolve_proxy()
            if not resolved_proxy:
                launch_args.append("--no-proxy-server")

            proxy_config = {"server": resolved_proxy} if resolved_proxy else None
            browser = await context.chromium.launch(
                headless=self.headless,
                args=launch_args,
                proxy=proxy_config,
            )
            browser = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            self._prepared_map["browser"] = browser
        return browser

    async def get_page(self, browser: BrowserContext) -> Page:
        page = self._prepared_map.get("page")
        if not page:
            page = await browser.new_page()
            self._prepared_map["page"] = page
        return page

    async def get(self, url: str, params: dict = {}, json: dict = {}, headers: dict = {}, timeout: int = 0) -> Response:
        return await self.request("GET", url, params, json, headers, timeout or self.timeout)

    async def post(self, url: str, params: dict = {}, json: dict = {}, headers: dict = {}, timeout: int = 0) -> Response:
        return await self.request("POST", url, params, json, headers, timeout or self.timeout)

    async def request(self, method: str, url: str, params: dict = {}, json: dict = {}, headers: dict = {}, timeout: int = 0) -> Response:
        timeout = timeout or self.timeout
        async with self.lock:
            browser = await self.prepare_browser()
            page = await self.get_page(browser)

            prepared_url = f"{url}?{self._make_query_string(params)}" if params else url
            merged_headers = {**self.headers, **headers}

            await page.route(f"{url}**", self._edit_request_handler(method, json, merged_headers))
            await page.goto(url, timeout=timeout, wait_until="commit")

            async with page.expect_response(f"{prepared_url}**", timeout=timeout) as response_info:
                request_js = f"""fetch('{prepared_url}', {{
                    method: '{method}',
                    headers: {merged_headers},
                    {f"body: JSON.stringify({json})," if json else ""}
                }}).then(r => r.json())"""
                await page.evaluate(request_js)
                raw = await response_info.value

            logger.info("WD %s %s HTTP %s", method, prepared_url, raw.status)
            return Response(status_code=raw.status, text=raw.status_text, data=await raw.json())

    async def close(self) -> None:
        browser = self._prepared_map.get("browser")
        if browser:
            await browser.close()
        self._prepared_map.clear()

    def _edit_request_handler(self, method: str, json: dict, headers: dict):
        async def handle_route(route: Route):
            request_headers = dict(route.request.headers)
            for k in list(request_headers):
                if "sec-ch-ua" in k:
                    del request_headers[k]
            request_headers.update(headers)
            await route.continue_(headers=request_headers)
        return handle_route
