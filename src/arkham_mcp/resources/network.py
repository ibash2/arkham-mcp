"""
MCP Resource: arkham://network/{chain}
MCP Resource: arkham://network/status

Provides network-level data: current status and 7-day history.
"""

import json

from fastmcp import FastMCP
from fastmcp.server.context import Context


async def _network_history(chain: str, client) -> str:
    """Business logic — testable without FastMCP context injection."""
    data = await client.get_network_history(chain, time_last="7d")
    return json.dumps({"chain": chain, "history": data}, indent=2)


async def _networks_status(client) -> str:
    """Business logic — testable without FastMCP context injection."""
    data = await client.get_networks_status()
    return json.dumps(data, indent=2)


def register(mcp: FastMCP) -> None:

    @mcp.resource(
        uri="arkham://network/{chain}",
        name="network_history",
        description=(
            "7-day price and volume history for a blockchain network. "
            "chain: 'ethereum' | 'bsc' | 'polygon' | 'arbitrum' | 'solana' | etc. "
            "Cached for 5 minutes."
        ),
        mime_type="application/json",
    )
    async def network_history_resource(chain: str, ctx: Context) -> str:
        return await _network_history(chain, ctx.lifespan_context["client"])

    @mcp.resource(
        uri="arkham://network/status",
        name="networks_status",
        description=(
            "Current status of all supported blockchain networks: "
            "price, 24h volume, gas fees. "
            "Cached for 5 minutes."
        ),
        mime_type="application/json",
    )
    async def networks_status_resource(ctx: Context) -> str:
        return await _networks_status(ctx.lifespan_context["client"])
