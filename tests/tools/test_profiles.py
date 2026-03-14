"""
Tests for tools/profiles.py:
  - _top_balances()
  - resolve_address()
  - get_entity_profile()
  - compare_addresses()
"""

import pytest
from unittest.mock import AsyncMock, patch

from tests.conftest import make_client, make_ctx

# Import the pure helper directly
from src.arkham_mcp.tools.profiles import _top_balances


# ── _top_balances ──────────────────────────────────────────────────────────────

class TestTopBalances:

    def test_sorts_by_usd_value_descending(self):
        data = {
            "tokens": [
                {"token": {"symbol": "USDC"}, "chain": "ethereum", "usdValue": 100, "amount": "100"},
                {"token": {"symbol": "ETH"}, "chain": "ethereum", "usdValue": 5000, "amount": "2"},
                {"token": {"symbol": "BTC"}, "chain": "bitcoin", "usdValue": 3000, "amount": "0.1"},
            ]
        }
        result = _top_balances(data)
        assert result[0]["token"] == "ETH"
        assert result[1]["token"] == "BTC"
        assert result[2]["token"] == "USDC"

    def test_respects_top_n(self):
        data = {
            "tokens": [{"token": {"symbol": f"T{i}"}, "chain": "eth", "usdValue": i, "amount": "1"}
                       for i in range(20)]
        }
        result = _top_balances(data, top_n=5)
        assert len(result) == 5

    def test_uses_data_key_as_fallback(self):
        data = {"data": [{"token": {"symbol": "ETH"}, "chain": "ethereum", "usdValue": 1000, "amount": "1"}]}
        result = _top_balances(data)
        assert len(result) == 1
        assert result[0]["token"] == "ETH"

    def test_uses_tokenId_when_no_symbol(self):
        data = {"tokens": [{"tokenId": "some-token", "chain": "eth", "usdValue": 50, "amount": "1"}]}
        result = _top_balances(data)
        assert result[0]["token"] == "some-token"

    def test_empty_tokens_returns_empty_list(self):
        assert _top_balances({}) == []
        assert _top_balances({"tokens": []}) == []

    def test_missing_usd_value_treated_as_zero(self):
        data = {"tokens": [
            {"token": {"symbol": "ETH"}, "chain": "eth", "amount": "1"},  # no usdValue
        ]}
        result = _top_balances(data)
        assert result[0]["usd_value"] == 0


# ── resolve_address ────────────────────────────────────────────────────────────

class TestResolveAddress:

    @pytest.mark.asyncio
    async def test_identified_address(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("resolve_address")

        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["address"] == "0xABC"
        assert result["is_identified"] is True
        assert result["entity"]["name"] == "Vitalik"
        assert result["entity"]["twitter"] == "VitalikButerin"
        assert result["labels"] == [{"name": "ENS: vitalik.eth", "source": "ens"}]
        assert result["predictions"][0]["confidence"] == 0.95
        assert result["tags"] == ["public-figure"]
        assert result["cluster_id"] == "cluster-1"
        assert result["total_usd"] == 15_000
        assert len(result["top_holdings"]) == 2

    @pytest.mark.asyncio
    async def test_unidentified_address(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("resolve_address")

        client = make_client(
            get_address_enriched={
                "arkhamEntity": {},
                "arkhamLabel": [],
                "predictedEntity": [],
                "chains": ["ethereum"],
                "populatedTags": [],
                "clusterId": None,
            }
        )
        ctx = make_ctx(client)

        result = await tool.fn(address="0xUNKNOWN", ctx=ctx)

        assert result["is_identified"] is False
        assert result["entity"] is None

    @pytest.mark.asyncio
    async def test_enriched_fetch_failure_degrades_gracefully(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("resolve_address")

        client = make_client()
        client.get_address_enriched.side_effect = Exception("API error")
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["entity"] is None
        assert result["labels"] == []
        assert result["predictions"] == []
        assert result["is_identified"] is False
        ctx.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_balances_fetch_failure_degrades_gracefully(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("resolve_address")

        client = make_client()
        client.get_address_balances.side_effect = Exception("timeout")
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["top_holdings"] == []
        assert result["total_usd"] is None
        assert result["is_identified"] is True  # enriched still worked


# ── get_entity_profile ─────────────────────────────────────────────────────────

class TestGetEntityProfile:

    @pytest.mark.asyncio
    async def test_full_profile(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_entity_profile")

        ctx = make_ctx(make_client())
        result = await tool.fn(entity="binance", ctx=ctx)

        assert result["entity_slug"] == "binance"
        assert result["name"] == "Binance"
        assert result["type"] == "cex"
        assert result["address_count"] == 500
        assert result["total_usd"] == 5_000_000_000
        assert result["top_holdings"][0]["token"] == "BTC"
        assert len(result["predicted_addresses"]) == 2

    @pytest.mark.asyncio
    async def test_partial_failure_still_returns_result(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_entity_profile")

        client = make_client()
        client.get_entity_summary.side_effect = Exception("not found")
        client.get_entity_predictions.side_effect = Exception("not found")
        ctx = make_ctx(client)

        result = await tool.fn(entity="binance", ctx=ctx)

        assert result["name"] == "Binance"       # entity_data worked
        assert "total_usd" not in result          # summary failed
        assert result["predicted_addresses"] == []
        assert ctx.warning.call_count == 2


# ── compare_addresses ──────────────────────────────────────────────────────────

class TestCompareAddresses:

    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_input(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("compare_addresses")

        ctx = make_ctx(make_client())
        result = await tool.fn(addresses=[], ctx=ctx)
        assert result == []

    @pytest.mark.asyncio
    async def test_compare_two_addresses(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("compare_addresses")

        ctx = make_ctx(make_client())
        result = await tool.fn(addresses=["0xABC", "0xDEF"], ctx=ctx)

        assert len(result) == 2
        assert result[0]["address"] == "0xABC"
        assert result[0]["entity_name"] == "Binance"
        assert result[0]["entity_type"] == "cex"
        assert result[1]["address"] == "0xDEF"
        assert result[1]["entity_name"] is None
        assert "mixer" in result[1]["tags"]

    @pytest.mark.asyncio
    async def test_batch_failure_raises_runtime_error(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("compare_addresses")

        client = make_client()
        client.batch_addresses_enriched.side_effect = Exception("batch failed")
        ctx = make_ctx(client)

        with pytest.raises(RuntimeError, match="Batch enriched lookup failed"):
            await tool.fn(addresses=["0xABC", "0xDEF"], ctx=ctx)

    @pytest.mark.asyncio
    async def test_total_usd_computed_correctly(self):
        from src.arkham_mcp.tools.profiles import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("compare_addresses")

        client = make_client(
            batch_addresses_enriched=[{
                "address": "0xABC",
                "arkhamEntity": {"name": "Test", "type": "fund"},
                "arkhamLabel": [],
                "populatedTags": [],
                "chains": ["ethereum"],
                "clusterId": None,
            }],
            get_address_balances={
                "tokens": [
                    {"token": {"symbol": "ETH"}, "chain": "ethereum", "usdValue": 8_000, "amount": "4"},
                    {"token": {"symbol": "BTC"}, "chain": "bitcoin", "usdValue": 2_000, "amount": "0.05"},
                ]
            }
        )
        ctx = make_ctx(client)

        result = await tool.fn(addresses=["0xABC"], ctx=ctx)
        assert result[0]["total_usd"] == 10_000
        assert result[0]["top_token"] == "ETH"
