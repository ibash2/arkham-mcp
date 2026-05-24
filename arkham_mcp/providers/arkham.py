"""
ArkhamProvider — реализация DataProvider через Arkham Intelligence API.

Тонкая обёртка над ArkhamClient: добавляет явное объявление
что клиент реализует DataProvider, и предоставляет фабричную функцию.
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from ..client import ArkhamClient
from ..config import Settings
from .base import DataProvider


@asynccontextmanager
async def create_provider(settings: Settings) -> AsyncIterator[DataProvider]:
    """
    Async context manager, возвращающий готовый к работе ArkhamClient.

    Использование:
        async with create_provider(settings) as provider:
            data = await provider.get_address("0x...")
    """
    async with ArkhamClient(
        api_key=settings.api_key,
        cookie=settings.cookie,
        base_url=settings.base_url,
    ) as client:
        # Статическая проверка: убедимся что ArkhamClient удовлетворяет Protocol.
        # Если нет — ошибка возникнет здесь при старте, а не во время запроса.
        assert isinstance(client, DataProvider), (
            "ArkhamClient does not fully implement DataProvider. "
            "Add missing methods to client.py."
        )
        yield client
