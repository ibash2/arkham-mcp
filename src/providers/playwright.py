"""
PlaywrightProvider — реализация DataProvider через браузерный транспорт.

Использует PlaywrightArkhamClient вместо AiohttpClient.
Подходит когда обычные HTTP запросы блокируются Cloudflare / bot-detection.

Активация:
    ARKHAM_PROVIDER=playwright в .env или .mcp.json
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from ..config import Settings
from .base import DataProvider


@asynccontextmanager
async def create_provider(settings: Settings) -> AsyncIterator[DataProvider]:
    try:
        from ..http.playwright_client import PlaywrightArkhamClient
    except ImportError:
        raise ImportError(
            "patchright is required for the playwright provider. "
            "Install it with: poetry add patchright"
        )

    async with PlaywrightArkhamClient(
        api_key=settings.api_key,
        cookie=settings.cookie,
        base_url=settings.base_url,
    ) as client:
        assert isinstance(client, DataProvider), (
            "PlaywrightArkhamClient does not fully implement DataProvider."
        )
        yield client
