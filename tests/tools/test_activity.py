"""
Tests for tools/activity.py:
  - get_address_activity()
  - get_portfolio_change()
"""

import pytest

from tests.conftest import make_client, make_ctx


# ── get_address_activity ───────────────────────────────────────────────────────

class TestGetAddressActivity:

    @pytest.mark.asyncio
    async def test_aggregates_flow_and_counterparties(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_address_activity")

        ctx = make_ctx(make_client())

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["address"] == "0xABC"
        assert result["period"] == "30d"
        assert result["total_inflow_usd"] == 150_000   # 100k + 50k
        assert result["total_outflow_usd"] == 140_000  # 80k + 60k
        assert result["net_flow_usd"] == 10_000
        assert len(result["top_counterparties"]) == 2

    @pytest.mark.asyncio
    async def test_counterparty_fields_mapped_correctly(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_address_activity")

        ctx = make_ctx(make_client())

        result = await tool.fn(address="0xABC", ctx=ctx)
        cp = result["top_counterparties"][0]

        assert cp["address"] == "0xEXCHANGE"
        assert cp["entity_name"] == "Coinbase"
        assert cp["entity_type"] == "cex"
        assert cp["volume_usd"] == 500_000
        assert cp["tx_count"] == 12
        assert cp["labels"] == ["Coinbase 1"]

    @pytest.mark.asyncio
    async def test_flow_failure_degrades_gracefully(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_address_activity")

        client = make_client()
        client.get_address_flow.side_effect = Exception("timeout")
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["total_inflow_usd"] is None
        assert result["total_outflow_usd"] is None
        assert result["flow_snapshots"] == []
        ctx.warning.assert_called()

    @pytest.mark.asyncio
    async def test_counterparties_failure_degrades_gracefully(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_address_activity")

        client = make_client()
        client.get_counterparties.side_effect = Exception("rate limit")
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["top_counterparties"] == []
        ctx.warning.assert_called()

    @pytest.mark.asyncio
    async def test_both_fail_returns_empty_result(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_address_activity")

        client = make_client()
        client.get_address_flow.side_effect = Exception("err")
        client.get_counterparties.side_effect = Exception("err")
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["total_inflow_usd"] is None
        assert result["top_counterparties"] == []

    @pytest.mark.asyncio
    async def test_passes_time_last_to_client(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_address_activity")

        client = make_client()
        ctx = make_ctx(client)

        await tool.fn(address="0xABC", ctx=ctx, time_last="7d")

        client.get_address_flow.assert_called_once_with(
            "0xABC", time_last="7d", flow="all", chains=None
        )
        client.get_counterparties.assert_called_once_with(
            "0xABC", time_last="7d", chains=None, limit=10,
            sort_key="volumeUsd", sort_dir="desc"
        )

    @pytest.mark.asyncio
    async def test_uses_snapshots_key_as_fallback(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_address_activity")

        client = make_client(
            get_address_flow={"snapshots": [{"inflow": 1000, "outflow": 500}]}
        )
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)
        assert result["total_inflow_usd"] == 1000
        assert result["total_outflow_usd"] == 500


# ── get_portfolio_change ───────────────────────────────────────────────────────

class TestGetPortfolioChange:

    @pytest.mark.asyncio
    async def test_detects_added_token(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_portfolio_change")

        client = make_client()
        client.get_portfolio.side_effect = [
            # before: only ETH
            {"tokens": [{"tokenId": "ethereum", "token": {"symbol": "ETH"}, "usdValue": 10_000}]},
            # after: ETH + new USDC
            {"tokens": [
                {"tokenId": "ethereum", "token": {"symbol": "ETH"}, "usdValue": 10_000},
                {"tokenId": "usd-coin", "token": {"symbol": "USDC"}, "usdValue": 5_000},
            ]},
        ]
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", from_ts=1000, to_ts=2000, ctx=ctx)

        assert len(result["added"]) == 1
        assert result["added"][0]["token"] == "USDC"
        assert result["added"][0]["usd_value"] == 5_000
        assert result["removed"] == []
        assert result["net_change_usd"] == 5_000

    @pytest.mark.asyncio
    async def test_detects_removed_token(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_portfolio_change")

        client = make_client()
        client.get_portfolio.side_effect = [
            {"tokens": [
                {"tokenId": "ethereum", "token": {"symbol": "ETH"}, "usdValue": 10_000},
                {"tokenId": "usd-coin", "token": {"symbol": "USDC"}, "usdValue": 5_000},
            ]},
            {"tokens": [
                {"tokenId": "ethereum", "token": {"symbol": "ETH"}, "usdValue": 10_000},
            ]},
        ]
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", from_ts=1000, to_ts=2000, ctx=ctx)

        assert len(result["removed"]) == 1
        assert result["removed"][0]["token"] == "USDC"
        assert result["net_change_usd"] == -5_000

    @pytest.mark.asyncio
    async def test_detects_changed_position(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_portfolio_change")

        client = make_client()
        client.get_portfolio.side_effect = [
            {"tokens": [{"tokenId": "ethereum", "token": {"symbol": "ETH"}, "usdValue": 10_000}]},
            {"tokens": [{"tokenId": "ethereum", "token": {"symbol": "ETH"}, "usdValue": 15_000}]},
        ]
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", from_ts=1000, to_ts=2000, ctx=ctx)

        assert len(result["changed"]) == 1
        eth = result["changed"][0]
        assert eth["token"] == "ETH"
        assert eth["delta_usd"] == 5_000
        assert eth["delta_pct"] == 50.0

    @pytest.mark.asyncio
    async def test_ignores_negligible_changes(self):
        """Delta < 0.01 USD should not appear in changed."""
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_portfolio_change")

        client = make_client()
        client.get_portfolio.side_effect = [
            {"tokens": [{"tokenId": "eth", "token": {"symbol": "ETH"}, "usdValue": 10_000.001}]},
            {"tokens": [{"tokenId": "eth", "token": {"symbol": "ETH"}, "usdValue": 10_000.000}]},
        ]
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", from_ts=1000, to_ts=2000, ctx=ctx)
        assert result["changed"] == []

    @pytest.mark.asyncio
    async def test_before_fetch_failure_raises(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_portfolio_change")

        client = make_client()
        client.get_portfolio.side_effect = Exception("not found")
        ctx = make_ctx(client)

        with pytest.raises(RuntimeError, match="Portfolio \\(before\\) fetch failed"):
            await tool.fn(address="0xABC", from_ts=1000, to_ts=2000, ctx=ctx)

    @pytest.mark.asyncio
    async def test_after_fetch_failure_raises(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_portfolio_change")

        client = make_client()
        client.get_portfolio.side_effect = [
            {"tokens": [{"tokenId": "eth", "token": {"symbol": "ETH"}, "usdValue": 1000}]},
            Exception("not found"),
        ]
        ctx = make_ctx(client)

        with pytest.raises(RuntimeError, match="Portfolio \\(after\\) fetch failed"):
            await tool.fn(address="0xABC", from_ts=1000, to_ts=2000, ctx=ctx)

    @pytest.mark.asyncio
    async def test_changed_sorted_by_abs_delta(self):
        from fastmcp import FastMCP
        from src.arkham_mcp.tools.activity import register

        mcp = FastMCP("test")
        register(mcp)
        tool = await mcp.get_tool("get_portfolio_change")

        client = make_client()
        client.get_portfolio.side_effect = [
            {"tokens": [
                {"tokenId": "a", "token": {"symbol": "A"}, "usdValue": 1000},
                {"tokenId": "b", "token": {"symbol": "B"}, "usdValue": 100},
            ]},
            {"tokens": [
                {"tokenId": "a", "token": {"symbol": "A"}, "usdValue": 1500},   # delta +500
                {"tokenId": "b", "token": {"symbol": "B"}, "usdValue": 50},     # delta -50
            ]},
        ]
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", from_ts=1000, to_ts=2000, ctx=ctx)

        assert result["changed"][0]["token"] == "A"  # largest abs delta first
        assert result["changed"][1]["token"] == "B"
