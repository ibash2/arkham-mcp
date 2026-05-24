import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from patchright.async_api import PlaywrightContextManager  # type: ignore
from patchright.async_api import BrowserContext, Page, Route

logger = logging.getLogger("webdriver")


@dataclass
class Responce:
    status_code: int
    text: str
    data: dict

    def json(self) -> dict:
        return self.data


@dataclass
class BaseWebDriverHttp(ABC):
    cookie: dict = field(default_factory=dict, kw_only=True)
    headers: dict = field(default_factory=dict, kw_only=True)
    timeout: int = field(default_factory=lambda: 5000, kw_only=True)

    @abstractmethod
    async def get(self, url: str, params: dict = {}, json: dict = {}, headers: dict = {}, timeout: int = 0) -> Responce:
        pass

    @abstractmethod
    async def post(self, url: str, params: dict = {}, json: dict = {}, headers: dict = {}, timeout: int = 0) -> Responce:
        pass

    @abstractmethod
    async def request(self, method: str, url: str, params: dict = {}, json: dict = {}, headers: dict = {}) -> Responce:
        pass

    def _make_query_string(self, params: dict) -> str:
        return "&".join([f"{key}={value}" for key, value in params.items()])


@dataclass
class PlaywrightWebDriverHttp(BaseWebDriverHttp):
    _prepared_map: dict = field(default_factory=dict, kw_only=True)
    headless: bool = field(default=True, kw_only=True)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, kw_only=True)

    async def prepare_browser(self) -> BrowserContext:
        browser = self._prepared_map.get("browser", None)
        if not browser:
            context = await PlaywrightContextManager().start()
            browser = await context.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--lang=ru-RU,ru;q=0.9",
                    "--disable-sync",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-blink-features=AutomationControlled",
                    # Do not route through system proxy — direct connection gives a
                    # residential IP fingerprint which is required for Cloudflare bypass.
                    "--no-proxy-server",
                ],
            )
            browser = await browser.new_context(
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            )
            self._prepared_map["browser"] = browser
        return browser

    async def get_page(self, browser: BrowserContext) -> Page:
        page = self._prepared_map.get("page", None)
        if not page:
            page = await browser.new_page()
            self._prepared_map["page"] = page
        return page

    async def get(self, url, params={}, json={}, headers={}, timeout: int = 0) -> Responce:
        if timeout == 0:
            timeout = self.timeout
        return await self.request("GET", url, params, json, headers, timeout)

    async def post(self, url, params={}, json={}, headers={}, timeout: int = 0) -> Responce:
        if timeout == 0:
            timeout = self.timeout
        return await self.request("POST", url, params, json, headers, timeout)

    async def request(self, method, url, params={}, json={}, headers={}, timeout: int = 0) -> Responce:
        if timeout == 0:
            timeout = self.timeout
        async with self.lock:
            browser = await self.prepare_browser()
            page = await self.get_page(browser)

            prepared_url = url
            if params:
                prepared_url = f"{url}?{self._make_query_string(params)}"

            merged_headers = {**self.headers, **headers}

            await page.route(
                f"{url}**",
                self.edit_request_handler(method, json, merged_headers),
            )

            await page.goto(url, timeout=timeout, wait_until="commit")
            async with page.expect_response(f"{prepared_url}**", timeout=timeout) as response_info:
                request_js = f"""fetch('{prepared_url}', {{
                    method: '{method}',
                    headers: {merged_headers},
                    {f"body: JSON.stringify({json})," if json else ""}
                }}).then(response => response.json())"""

                await page.evaluate(request_js)
                responce_value = await response_info.value

                logger.info("WD Request: %s %s 'HTTP %s'", method, prepared_url, responce_value.status)
                responce = Responce(
                    status_code=responce_value.status,
                    text=responce_value.status_text,
                    data=await responce_value.json(),
                )

            return responce

    async def close(self) -> None:
        browser = self._prepared_map.get("browser")
        if browser:
            await browser.close()
        self._prepared_map.clear()

    def edit_request_handler(self, method, json, headers):
        async def handle_route(route: Route):
            request_headers = dict(route.request.headers)
            # Remove sec-ch-ua headers that reveal automation
            for k in list(request_headers):
                if "sec-ch-ua" in k:
                    del request_headers[k]
            request_headers.update(headers)
            await route.continue_(headers=request_headers)

        return handle_route
