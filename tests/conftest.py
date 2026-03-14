"""
Shared fixtures for all tests.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


# ── Mock client factory ────────────────────────────────────────────────────────

def make_client(**overrides) -> AsyncMock:
    """
    Build a mock DataProvider with sensible defaults for every method.
    Pass keyword overrides to replace specific method return values.
    """
    client = AsyncMock()

    defaults = {
        "get_address": {"address": "0xABC", "arkhamEntity": {"name": "Vitalik", "type": "individual"}},
        "get_address_all_chains": {"address": "0xABC", "chains": ["ethereum", "polygon"]},
        "get_address_enriched_all_chains": {"address": "0xABC", "chains": ["ethereum", "polygon", "bsc"]},
        "batch_addresses_all_chains": [{"address": "0xABC"}, {"address": "0xDEF"}],
        "batch_addresses_enriched_all_chains": [{"address": "0xABC"}, {"address": "0xDEF"}],
        "get_address_enriched": {
            "arkhamEntity": {"name": "Vitalik", "type": "individual", "website": None, "twitter": "VitalikButerin"},
            "arkhamLabel": [{"name": "ENS: vitalik.eth", "source": "ens"}],
            "predictedEntity": [{"entity": {"name": "Vitalik"}, "confidence": 0.95}],
            "chains": ["ethereum"],
            "populatedTags": [{"name": "public-figure"}],
            "clusterId": "cluster-1",
        },
        "batch_addresses": [{"address": "0xABC"}, {"address": "0xDEF"}],
        "batch_addresses_enriched": [
            {
                "address": "0xABC",
                "arkhamEntity": {"name": "Binance", "type": "cex"},
                "arkhamLabel": [{"name": "Binance Hot Wallet"}],
                "populatedTags": [],
                "chains": ["ethereum", "bsc"],
                "clusterId": "cluster-binance",
            },
            {
                "address": "0xDEF",
                "arkhamEntity": None,
                "arkhamLabel": [],
                "populatedTags": [{"name": "mixer"}],
                "chains": ["ethereum"],
                "clusterId": None,
            },
        ],
        "get_entity": {
            "name": "Binance", "type": "cex",
            "website": "https://binance.com", "twitter": "binance",
            "description": "Largest crypto exchange",
        },
        "get_entity_summary": {"addressCount": 500, "chainCount": 8, "totalUsd": 5_000_000_000},
        "get_entity_balances": {
            "tokens": [
                {"token": {"symbol": "BTC", "id": "bitcoin"}, "chain": "bitcoin", "usdValue": 3_000_000_000},
                {"token": {"symbol": "ETH", "id": "ethereum"}, "chain": "ethereum", "usdValue": 1_000_000_000},
                {"token": {"symbol": "USDT", "id": "tether"}, "chain": "ethereum", "usdValue": 500_000_000},
            ]
        },
        "get_entity_predictions": {
            "predictions": [
                {"address": "0xAAA", "chain": "ethereum", "confidence": 0.9},
                {"address": "0xBBB", "chain": "bsc", "confidence": 0.75},
            ]
        },
        "get_entity_balance_changes": {
            "entities": [
                {"entity": {"name": "Binance", "type": "cex"}, "changeUsd": 500_000_000},
                {"entity": {"name": "Jump Trading", "type": "fund"}, "changeUsd": -200_000_000},
            ]
        },
        "get_solana_entity_subaccount_balances": {"data": []},
        "get_entity_portfolio": {"snapshots": []},
        "get_entity_portfolio_timeseries": {"data": []},
        "get_entity_flow": {"data": [{"inflow": 100_000, "outflow": 80_000}]},
        "get_entity_history": {"data": [{"time": 1700000000000, "usd": 5_000_000_000}]},
        "get_entity_counterparties": {
            "counterparties": [
                {
                    "address": "0xEXCHANGE",
                    "arkhamEntity": {"name": "FTX", "type": "cex"},
                    "arkhamLabel": [],
                    "volumeUsd": 1_000_000,
                    "txCount": 5,
                    "direction": "out",
                }
            ]
        },
        "get_address_loans": {"positions": []},
        "get_entity_loans": {"positions": []},
        "get_cluster_summary": {"addressCount": 10, "totalUsd": 1_000_000},
        "get_address_balances": {
            "tokens": [
                {"token": {"symbol": "ETH", "id": "ethereum"}, "chain": "ethereum", "usdValue": 10_000, "amount": "5.0"},
                {"token": {"symbol": "USDC", "id": "usd-coin"}, "chain": "ethereum", "usdValue": 5_000, "amount": "5000"},
            ]
        },
        "get_address_flow": {
            "data": [
                {"inflow": 100_000, "outflow": 80_000},
                {"inflow": 50_000, "outflow": 60_000},
            ]
        },
        "get_counterparties": {
            "counterparties": [
                {
                    "address": "0xEXCHANGE",
                    "arkhamEntity": {"name": "Coinbase", "type": "cex"},
                    "arkhamLabel": [{"name": "Coinbase 1"}],
                    "volumeUsd": 500_000,
                    "txCount": 12,
                    "direction": "out",
                },
                {
                    "address": "0xUNKNOWN",
                    "arkhamEntity": None,
                    "arkhamLabel": [],
                    "volumeUsd": 200_000,
                    "txCount": 3,
                    "direction": "out",
                },
            ]
        },
        "get_solana_subaccount_balances": {"data": []},
        "get_portfolio": {
            "tokens": [
                {"tokenId": "ethereum", "token": {"symbol": "ETH"}, "usdValue": 10_000},
                {"tokenId": "usd-coin", "token": {"symbol": "USDC"}, "usdValue": 5_000},
            ]
        },
        "get_portfolio_timeseries": {"data": []},
        "get_address_history": {"data": []},
        "get_swaps": {"swaps": []},
        "get_transfers": {"transfers": [], "count": 0},
        "get_transfers_histogram": [{"time": 1700000000000, "count": 5, "usd": 50_000}],
        "get_transfers_histogram_simple": [{"time": 1700000000000, "count": 3}],
        "get_transfers_by_tx": [],
        "get_chains": ["ethereum", "bsc", "polygon", "arbitrum", "solana"],
        "get_entity_types": ["cex", "dex", "fund", "bridge", "individual", "mixer"],
        "get_networks_status": {"ethereum": {"price": 3000, "volume24h": 10_000_000}},
        "get_network_history": {"data": [{"time": 1700000000000, "price": 3000}]},
        "get_altcoin_index": {"index": 72, "change24h": 3.5},
        "get_arkm_circulating_supply": {"circulating": 150_000_000},
        "get_token_by_id": {"id": "ethereum", "symbol": "ETH", "price": 3000},
        "get_token_by_address": {"id": "ethereum", "symbol": "ETH"},
        "get_contract": {"address": "0xCONTRACT", "deployer": "0xDEPLOYER"},
        "search": {"results": [{"type": "entity", "name": "Binance", "slug": "binance"}]},
    }

    for method, return_value in {**defaults, **overrides}.items():
        getattr(client, method).return_value = return_value

    return client


# ── Mock Context factory ───────────────────────────────────────────────────────

def make_ctx(client=None) -> MagicMock:
    """Build a mock FastMCP Context with state containing a mock client."""
    ctx = MagicMock()
    ctx.lifespan_context = {"client": client or make_client()}
    ctx.info = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.error = AsyncMock()
    return ctx
