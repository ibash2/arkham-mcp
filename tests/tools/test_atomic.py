"""
Tests for tools/atomic.py — thin wrappers around DataProvider methods.
"""

import pytest

from tests.conftest import make_client, make_ctx


async def get_tool(name: str):
    from fastmcp import FastMCP
    from src.arkham_mcp.tools.atomic import register

    mcp = FastMCP("test")
    register(mcp)
    return await mcp.get_tool(name)


class TestAtomicTools:

    @pytest.mark.asyncio
    async def test_search(self):
        tool = await get_tool("search")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(query="binance", ctx=ctx)
        client.search.assert_called_once_with("binance")
        assert "results" in result

    @pytest.mark.asyncio
    async def test_get_token(self):
        tool = await get_tool("get_token")
        client = make_client()
        ctx = make_ctx(client)

        await tool.fn(chain="ethereum", address="0xTOKEN", ctx=ctx)
        client.get_token_by_address.assert_called_once_with("ethereum", "0xTOKEN")

    @pytest.mark.asyncio
    async def test_get_token_by_coingecko_id(self):
        tool = await get_tool("get_token_by_coingecko_id")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(coingecko_id="ethereum", ctx=ctx)
        client.get_token_by_id.assert_called_once_with("ethereum")
        assert result["symbol"] == "ETH"

    @pytest.mark.asyncio
    async def test_get_contract(self):
        tool = await get_tool("get_contract")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(chain="ethereum", address="0xCONTRACT", ctx=ctx)
        client.get_contract.assert_called_once_with("ethereum", "0xCONTRACT")
        assert result["deployer"] == "0xDEPLOYER"

    @pytest.mark.asyncio
    async def test_get_networks_status(self):
        tool = await get_tool("get_networks_status")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(ctx=ctx)
        client.get_networks_status.assert_called_once()
        assert "ethereum" in result

    @pytest.mark.asyncio
    async def test_get_network_history_default_time(self):
        tool = await get_tool("get_network_history")
        client = make_client()
        ctx = make_ctx(client)

        await tool.fn(chain="ethereum", ctx=ctx)
        client.get_network_history.assert_called_once_with("ethereum", time_last="7d")

    @pytest.mark.asyncio
    async def test_get_network_history_custom_time(self):
        tool = await get_tool("get_network_history")
        client = make_client()
        ctx = make_ctx(client)

        await tool.fn(chain="solana", ctx=ctx, time_last="30d")
        client.get_network_history.assert_called_once_with("solana", time_last="30d")

    @pytest.mark.asyncio
    async def test_get_chains(self):
        tool = await get_tool("get_chains")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(ctx=ctx)
        assert "ethereum" in result

    @pytest.mark.asyncio
    async def test_get_entity_types(self):
        tool = await get_tool("get_entity_types")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(ctx=ctx)
        assert "cex" in result

    @pytest.mark.asyncio
    async def test_get_arkm_supply(self):
        tool = await get_tool("get_arkm_supply")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(ctx=ctx)
        assert result["circulating"] == 150_000_000

    @pytest.mark.asyncio
    async def test_get_altcoin_index(self):
        tool = await get_tool("get_altcoin_index")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(ctx=ctx)
        assert result["index"] == 72
