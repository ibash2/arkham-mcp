"""
Provider registry — маппинг имён провайдеров на фабричные функции.

Чтобы добавить новый провайдер:
  1. Создай файл providers/<name>.py с функцией create_provider(settings)
  2. Добавь его в _REGISTRY ниже
  3. Установи ARKHAM_PROVIDER=<name> в .env

Пример нового провайдера (providers/mock.py):
    @asynccontextmanager
    async def create_provider(settings):
        yield MockProvider()
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

from .base import DataProvider
from . import arkham

if TYPE_CHECKING:
    from ..config import Settings


def _playwright_provider(settings: "Settings"):
    """Lazy wrapper — imports playwright only when actually selected."""
    from . import playwright  # noqa: PLC0415
    return playwright.create_provider(settings)


_REGISTRY: dict[str, object] = {
    "arkham": arkham.create_provider,
    "playwright": _playwright_provider,
}


@asynccontextmanager
async def get_provider(settings: Settings) -> AsyncIterator[DataProvider]:
    """
    Фабрика провайдеров. Выбирает реализацию по settings.provider.

    Использование в server.py:
        async with get_provider(settings) as provider:
            app.state["client"] = provider
    """
    factory = _REGISTRY.get(settings.provider)
    if factory is None:
        available = ", ".join(f'"{k}"' for k in _REGISTRY)
        raise ValueError(
            f'Unknown provider "{settings.provider}". Available: {available}'
        )
    async with factory(settings) as provider:
        yield provider
