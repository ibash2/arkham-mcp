"""
Tests for tools/investigation.py:
  - _extract_risk_flags()
  - trace_fund_flow()
  - get_swaps()
"""

import pytest

from tests.conftest import make_client, make_ctx
from src.arkham_mcp.tools.investigation import _extract_risk_flags


async def get_tool(name: str):
    from fastmcp import FastMCP
    from src.arkham_mcp.tools.investigation import register

    mcp = FastMCP("test")
    register(mcp)
    return await mcp.get_tool(name)


# ── _extract_risk_flags ────────────────────────────────────────────────────────

class TestExtractRiskFlags:

    def test_unidentified_when_entity_is_none(self):
        flags = _extract_risk_flags(None, [])
        assert "unidentified_destination" in flags

    def test_unidentified_when_entity_has_no_name(self):
        flags = _extract_risk_flags({}, [])
        assert "unidentified_destination" in flags

    def test_no_unidentified_when_entity_identified(self):
        flags = _extract_risk_flags({"name": "Binance", "type": "cex"}, [])
        assert "unidentified_destination" not in flags

    def test_mixer_flag_from_entity_type(self):
        flags = _extract_risk_flags({"name": "TornadoCash", "type": "mixer"}, [])
        assert "mixer" in flags

    def test_risk_flag_from_tags(self):
        flags = _extract_risk_flags({"name": "Hack Wallet"}, ["hack", "exploit"])
        assert "hack" in flags
        assert "exploit" in flags

    def test_tag_matching_is_case_insensitive(self):
        flags = _extract_risk_flags({"name": "X"}, ["MIXER", "Tornado"])
        assert "mixer" in flags
        assert "tornado" in flags

    def test_benign_tags_produce_no_flags(self):
        flags = _extract_risk_flags({"name": "Coinbase"}, ["exchange", "kyc-verified"])
        assert not any(f in flags for f in ["unidentified_destination", "mixer"])

    def test_multiple_risk_sources_combined(self):
        flags = _extract_risk_flags(None, ["tornado", "darknet"])
        assert "unidentified_destination" in flags
        assert "tornado" in flags
        assert "darknet" in flags


# ── trace_fund_flow ────────────────────────────────────────────────────────────

class TestTraceFundFlow:

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_counterparties(self):
        tool = await get_tool("trace_fund_flow")
        client = make_client(get_counterparties={"counterparties": []})
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["flows"] == []
        assert result["suspicious_flags"] == []
        assert "No outgoing flows" in result["summary"]

    @pytest.mark.asyncio
    async def test_full_flow_graph_built(self):
        tool = await get_tool("trace_fund_flow")
        client = make_client()
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["origin"]["address"] == "0xABC"
        assert result["origin"]["entity"] == "Vitalik"
        assert len(result["flows"]) == 2
        assert result["total_outflow_usd"] == 700_000  # 500k + 200k

    @pytest.mark.asyncio
    async def test_exchange_destination_flagged(self):
        tool = await get_tool("trace_fund_flow")
        client = make_client(
            batch_addresses_enriched=[
                {
                    "address": "0xEXCHANGE",
                    "arkhamEntity": {"name": "Coinbase", "type": "cex"},
                    "arkhamLabel": [],
                    "populatedTags": [],
                    "chains": ["ethereum"],
                },
            ]
        )
        # Only one counterparty
        client.get_counterparties.return_value = {
            "counterparties": [
                {"address": "0xEXCHANGE", "volumeUsd": 100_000, "txCount": 5}
            ]
        }
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        flow = result["flows"][0]
        assert flow["is_exchange"] is True
        assert flow["is_mixer"] is False
        assert "Coinbase" in result["exchange_destinations"]

    @pytest.mark.asyncio
    async def test_mixer_destination_flagged(self):
        tool = await get_tool("trace_fund_flow")
        client = make_client(
            batch_addresses_enriched=[{
                "address": "0xMIXER",
                "arkhamEntity": {"name": "Tornado Cash", "type": "mixer"},
                "arkhamLabel": [],
                "populatedTags": [{"name": "tornado"}],
                "chains": ["ethereum"],
            }]
        )
        client.get_counterparties.return_value = {
            "counterparties": [{"address": "0xMIXER", "volumeUsd": 50_000, "txCount": 2}]
        }
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        flow = result["flows"][0]
        assert flow["is_mixer"] is True
        assert "mixer" in result["suspicious_flags"]
        assert "tornado" in result["suspicious_flags"]

    @pytest.mark.asyncio
    async def test_unidentified_destination_counted(self):
        tool = await get_tool("trace_fund_flow")
        client = make_client(
            batch_addresses_enriched=[{
                "address": "0xUNKNOWN",
                "arkhamEntity": None,
                "arkhamLabel": [],
                "populatedTags": [],
                "chains": [],
            }]
        )
        client.get_counterparties.return_value = {
            "counterparties": [{"address": "0xUNKNOWN", "volumeUsd": 10_000, "txCount": 1}]
        }
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["unidentified_count"] == 1
        assert "unidentified_destination" in result["suspicious_flags"]

    @pytest.mark.asyncio
    async def test_min_volume_filter_applied(self):
        tool = await get_tool("trace_fund_flow")
        client = make_client()
        ctx = make_ctx(client)

        # Default counterparties have volumes 500k and 200k
        result = await tool.fn(address="0xABC", ctx=ctx, min_volume_usd=300_000)

        assert len(result["flows"]) == 1
        assert result["flows"][0]["volume_usd"] == 500_000

    @pytest.mark.asyncio
    async def test_counterparties_called_with_flow_out(self):
        tool = await get_tool("trace_fund_flow")
        client = make_client()
        ctx = make_ctx(client)

        await tool.fn(address="0xABC", ctx=ctx, time_last="24h", chains="ethereum")

        client.get_counterparties.assert_called_once_with(
            "0xABC",
            flow="out",
            time_last="24h",
            chains="ethereum",
            limit=20,
            sort_key="volumeUsd",
            sort_dir="desc",
        )

    @pytest.mark.asyncio
    async def test_suspicious_flags_are_deduplicated(self):
        """Two unidentified destinations → only one 'unidentified_destination' flag."""
        tool = await get_tool("trace_fund_flow")
        client = make_client(
            batch_addresses_enriched=[
                {"address": "0xA", "arkhamEntity": None, "arkhamLabel": [], "populatedTags": [], "chains": []},
                {"address": "0xB", "arkhamEntity": None, "arkhamLabel": [], "populatedTags": [], "chains": []},
            ]
        )
        client.get_counterparties.return_value = {
            "counterparties": [
                {"address": "0xA", "volumeUsd": 100, "txCount": 1},
                {"address": "0xB", "volumeUsd": 100, "txCount": 1},
            ]
        }
        ctx = make_ctx(client)

        result = await tool.fn(address="0xABC", ctx=ctx)

        assert result["suspicious_flags"].count("unidentified_destination") == 1


# ── get_swaps ──────────────────────────────────────────────────────────────────

class TestGetSwaps:

    @pytest.mark.asyncio
    async def test_raises_when_no_address_or_entity(self):
        tool = await get_tool("get_swaps")
        ctx = make_ctx(make_client())

        with pytest.raises(ValueError, match="Provide either"):
            await tool.fn(ctx=ctx)

    @pytest.mark.asyncio
    async def test_calls_client_with_address(self):
        tool = await get_tool("get_swaps")
        client = make_client()
        ctx = make_ctx(client)

        await tool.fn(ctx=ctx, address="0xABC", time_last="24h")

        client.get_swaps.assert_called_once_with(
            address="0xABC",
            entity=None,
            time_last="24h",
            chains=None,
            limit=50,
            sort_dir="desc",
        )

    @pytest.mark.asyncio
    async def test_calls_client_with_entity(self):
        tool = await get_tool("get_swaps")
        client = make_client()
        ctx = make_ctx(client)

        await tool.fn(ctx=ctx, entity_slug="binance", time_last="7d", chains="ethereum")

        client.get_swaps.assert_called_once_with(
            address=None,
            entity="binance",
            time_last="7d",
            chains="ethereum",
            limit=50,
            sort_dir="desc",
        )
