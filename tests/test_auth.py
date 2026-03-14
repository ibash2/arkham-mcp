"""
Tests for ArkhamClient authentication modes:
  - API key only
  - Cookie only
  - Both combined
  - Neither (should raise)
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from src.arkham_mcp.client import ArkhamClient


class TestArkhamClientAuth:

    def test_raises_when_no_auth_provided(self):
        with pytest.raises(ValueError, match="Either api_key or cookie"):
            ArkhamClient()

    def test_api_key_only_accepted(self):
        client = ArkhamClient(api_key="test-key")
        assert client.api_key == "test-key"
        assert client.cookie is None

    def test_cookie_only_accepted(self):
        client = ArkhamClient(cookie="AMP_f072531383=JTdC...")
        assert client.api_key is None
        assert client.cookie == "AMP_f072531383=JTdC..."

    def test_both_accepted(self):
        client = ArkhamClient(api_key="key", cookie="AMP_f072531383=JTdC...")
        assert client.api_key == "key"
        assert client.cookie == "AMP_f072531383=JTdC..."

    def test_build_auth_headers_api_key_only(self):
        client = ArkhamClient(api_key="my-api-key")
        headers = client._build_auth_headers()
        assert headers == {"API-Key": "my-api-key"}
        assert "Cookie" not in headers

    def test_build_auth_headers_cookie_only(self):
        cookie = "AMP_f072531383=JTdCJTIy"
        client = ArkhamClient(cookie=cookie)
        headers = client._build_auth_headers()
        assert headers == {"Cookie": cookie}
        assert "API-Key" not in headers

    def test_build_auth_headers_both(self):
        client = ArkhamClient(api_key="key", cookie="cookie=val")
        headers = client._build_auth_headers()
        assert headers["API-Key"] == "key"
        assert headers["Cookie"] == "cookie=val"

    @pytest.mark.asyncio
    async def test_session_created_with_api_key_header(self):
        client = ArkhamClient(api_key="my-key")
        with patch("src.arkham_mcp.client.aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.__aenter__()
            mock_cls.assert_called_once_with(
                headers={"API-Key": "my-key"},
                raise_for_status=False,
            )

    @pytest.mark.asyncio
    async def test_session_created_with_cookie_header(self):
        cookie = "AMP_f072531383=JTdC"
        client = ArkhamClient(cookie=cookie)
        with patch("src.arkham_mcp.client.aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.__aenter__()
            mock_cls.assert_called_once_with(
                headers={"Cookie": cookie},
                raise_for_status=False,
            )

    @pytest.mark.asyncio
    async def test_session_created_with_both_headers(self):
        client = ArkhamClient(api_key="key", cookie="c=v")
        with patch("src.arkham_mcp.client.aiohttp.ClientSession") as mock_cls:
            mock_cls.return_value = AsyncMock()
            await client.__aenter__()
            mock_cls.assert_called_once_with(
                headers={"API-Key": "key", "Cookie": "c=v"},
                raise_for_status=False,
            )


class TestSettingsAuth:

    def test_raises_when_neither_set(self):
        from pydantic import ValidationError
        from src.arkham_mcp.config import Settings

        with pytest.raises(ValidationError, match="Authentication required"):
            Settings(api_key=None, cookie=None)

    def test_valid_with_api_key_only(self):
        from src.arkham_mcp.config import Settings

        s = Settings(api_key="key")
        assert s.api_key == "key"
        # assert s.cookie is None

    def test_valid_with_cookie_only(self):
        from src.arkham_mcp.config import Settings

        s = Settings(cookie="AMP_f072531383=JTdC")
        assert s.api_key is None
        assert s.cookie == "AMP_f072531383=JTdC"

    def test_valid_with_both(self):
        from src.arkham_mcp.config import Settings

        s = Settings(api_key="key", cookie="c=v")
        assert s.api_key == "key"
        assert s.cookie == "c=v"

    def test_multiple_cookies_in_one_string(self):
        """Cookie header может содержать несколько кук через '; '."""
        from src.arkham_mcp.config import Settings

        cookie = "AMP_f072531383=JTdC; sessionId=abc123; other=val"
        s = Settings(cookie=cookie)
        assert s.cookie == cookie
