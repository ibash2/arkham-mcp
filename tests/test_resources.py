"""
Tests for resources/address.py, entity.py, network.py.

We test the module-level _impl functions directly to avoid FastMCP's
context dependency injection (which requires a live server context).
"""

import json
import pytest

from tests.conftest import make_client


# ── address resource ───────────────────────────────────────────────────────────

class TestAddressResource:

    @pytest.mark.asyncio
    async def test_returns_valid_json(self):
        from src.arkham_mcp.resources.address import _address_snapshot

        client = make_client()
        raw = await _address_snapshot("0xABC", client)
        data = json.loads(raw)

        assert data["address"] == "0xABC"
        assert data["is_identified"] is True
        assert data["entity"]["name"] == "Vitalik"
        assert data["total_usd"] == 15_000
        assert len(data["top_holdings"]) == 2

    @pytest.mark.asyncio
    async def test_unidentified_address(self):
        from src.arkham_mcp.resources.address import _address_snapshot

        client = make_client(
            get_address_enriched={
                "arkhamEntity": {},
                "arkhamLabel": [],
                "predictedEntity": [],
                "chains": [],
                "populatedTags": [],
                "clusterId": None,
            },
            get_address_balances={"tokens": []}
        )
        raw = await _address_snapshot("0xUNKNOWN", client)
        data = json.loads(raw)

        assert data["is_identified"] is False
        assert data["entity"] is None
        assert data["total_usd"] == 0

    @pytest.mark.asyncio
    async def test_enriched_failure_returns_partial_data(self):
        from src.arkham_mcp.resources.address import _address_snapshot

        client = make_client()
        client.get_address_enriched.side_effect = Exception("API error")

        raw = await _address_snapshot("0xABC", client)
        data = json.loads(raw)

        assert data["entity"] is None
        assert data["labels"] == []
        assert data["top_holdings"]  # balances still worked

    @pytest.mark.asyncio
    async def test_registered_as_template_resource(self):
        from src.arkham_mcp.resources.address import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        templates = await mcp.list_resource_templates()
        uris = [t.uri_template for t in templates]
        assert "arkham://address/{address}" in uris


# ── entity resource ────────────────────────────────────────────────────────────

class TestEntityResource:

    @pytest.mark.asyncio
    async def test_returns_valid_json(self):
        from src.arkham_mcp.resources.entity import _entity_profile

        raw = await _entity_profile("binance", make_client())
        data = json.loads(raw)

        assert data["slug"] == "binance"
        assert data["name"] == "Binance"
        assert data["type"] == "cex"
        assert data["address_count"] == 500
        assert data["total_usd"] == 5_000_000_000
        assert data["top_holdings"][0]["token"] == "BTC"

    @pytest.mark.asyncio
    async def test_partial_failure_omits_fields(self):
        from src.arkham_mcp.resources.entity import _entity_profile

        client = make_client()
        client.get_entity_summary.side_effect = Exception("not found")

        raw = await _entity_profile("binance", client)
        data = json.loads(raw)

        assert data["name"] == "Binance"
        assert "address_count" not in data
        assert "total_usd" not in data
        assert data["top_holdings"]  # balances still worked

    @pytest.mark.asyncio
    async def test_registered_as_template_resource(self):
        from src.arkham_mcp.resources.entity import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        templates = await mcp.list_resource_templates()
        uris = [t.uri_template for t in templates]
        assert "arkham://entity/{slug}" in uris


# ── network resources ──────────────────────────────────────────────────────────

class TestNetworkResources:

    @pytest.mark.asyncio
    async def test_network_history_returns_json(self):
        from src.arkham_mcp.resources.network import _network_history

        raw = await _network_history("ethereum", make_client())
        data = json.loads(raw)

        assert data["chain"] == "ethereum"
        assert "history" in data

    @pytest.mark.asyncio
    async def test_network_history_calls_7d(self):
        from src.arkham_mcp.resources.network import _network_history

        client = make_client()
        await _network_history("solana", client)

        client.get_network_history.assert_called_once_with("solana", time_last="7d")

    @pytest.mark.asyncio
    async def test_networks_status_returns_json(self):
        from src.arkham_mcp.resources.network import _networks_status

        raw = await _networks_status(make_client())
        data = json.loads(raw)

        assert "ethereum" in data

    @pytest.mark.asyncio
    async def test_registered_as_static_resource(self):
        from src.arkham_mcp.resources.network import register
        from fastmcp import FastMCP

        mcp = FastMCP("test")
        register(mcp)
        resources = await mcp.list_resources()
        uris = [str(r.uri) for r in resources]
        assert "arkham://network/status" in uris
