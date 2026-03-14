"""
Tests for providers/base.py (DataProvider Protocol)
and providers/__init__.py (registry + get_provider factory).
"""

import inspect
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

from src.arkham_mcp.providers.base import DataProvider
from tests.conftest import make_client


# ── DataProvider Protocol ──────────────────────────────────────────────────────

class TestDataProviderProtocol:

    def test_mock_client_satisfies_protocol(self):
        """The mock we use in all tool tests must have all protocol methods."""
        client = make_client()
        proto_methods = [n for n, _ in inspect.getmembers(DataProvider) if not n.startswith('_')]
        for m in proto_methods:
            assert hasattr(client, m), f"Missing method: {m}"

    def test_incomplete_class_does_not_satisfy_protocol(self):
        """A class missing methods should not satisfy the Protocol."""
        class Incomplete:
            async def get_address(self, address: str) -> dict:
                return {}
            # missing all other methods

        assert not isinstance(Incomplete(), DataProvider)

    def test_full_implementation_satisfies_protocol(self):
        """A class implementing all methods satisfies the Protocol."""
        methods = [m for m in dir(DataProvider) if not m.startswith("_")]

        class FullStub:
            pass

        for m in methods:
            setattr(FullStub, m, AsyncMock())

        obj = FullStub()
        assert isinstance(obj, DataProvider)


# ── Provider registry ──────────────────────────────────────────────────────────

class TestProviderRegistry:

    @pytest.mark.asyncio
    async def test_get_provider_arkham_returns_provider(self):
        from src.arkham_mcp.providers import get_provider, _REGISTRY
        from src.arkham_mcp.config import Settings

        settings = Settings(api_key="test-key", provider="arkham")

        mock_client = make_client()

        @asynccontextmanager
        async def mock_create(s):
            yield mock_client

        with patch.dict(_REGISTRY, {"arkham": mock_create}):
            async with get_provider(settings) as provider:
                assert provider is mock_client

    @pytest.mark.asyncio
    async def test_unknown_provider_raises_value_error(self):
        from src.arkham_mcp.providers import get_provider
        from src.arkham_mcp.config import Settings

        settings = Settings(api_key="test-key", provider="nonexistent")

        with pytest.raises(ValueError, match='Unknown provider "nonexistent"'):
            async with get_provider(settings) as _:
                pass

    @pytest.mark.asyncio
    async def test_error_message_lists_available_providers(self):
        from src.arkham_mcp.providers import get_provider
        from src.arkham_mcp.config import Settings

        settings = Settings(api_key="key", provider="bad")

        try:
            async with get_provider(settings) as _:
                pass
        except ValueError as e:
            assert "arkham" in str(e)

    def test_custom_provider_can_be_registered(self):
        """Verify the registry is a plain dict that can be extended."""
        from src.arkham_mcp.providers import _REGISTRY

        original = dict(_REGISTRY)
        try:
            _REGISTRY["custom"] = AsyncMock()
            assert "custom" in _REGISTRY
        finally:
            _REGISTRY.clear()
            _REGISTRY.update(original)


# ── ArkhamProvider ─────────────────────────────────────────────────────────────

class TestArkhamProvider:

    @pytest.mark.asyncio
    async def test_create_provider_yields_data_provider(self):
        """ArkhamClient yielded by create_provider must satisfy DataProvider."""
        from src.arkham_mcp.providers.arkham import create_provider
        from src.arkham_mcp.config import Settings

        settings = Settings(api_key="test-key")

        with patch("src.arkham_mcp.client.aiohttp.ClientSession") as mock_session_cls:
            mock_session_cls.return_value.close = AsyncMock()

            async with create_provider(settings) as provider:
                assert isinstance(provider, DataProvider)
