"""
MCP Resource: arkham://entity/{slug}

Returns a JSON profile of a known Arkham entity:
  metadata, statistics, top holdings.
"""

import asyncio
import json

from fastmcp import FastMCP
from fastmcp.server.context import Context


async def _entity_profile(slug: str, client) -> str:
    """Business logic — testable without FastMCP context injection."""
    entity_data, summary, balances = await asyncio.gather(
        client.get_entity(slug),
        client.get_entity_summary(slug),
        client.get_entity_balances(slug),
        return_exceptions=True,
    )

    result: dict = {"slug": slug}

    if not isinstance(entity_data, Exception):
        result.update(
            {
                "name": entity_data.get("name"),
                "type": entity_data.get("type"),
                "website": entity_data.get("website"),
                "twitter": entity_data.get("twitter"),
                "description": entity_data.get("description"),
            }
        )

    if not isinstance(summary, Exception):
        result.update(
            {
                "address_count": summary.get("addressCount"),
                "chain_count": summary.get("chainCount"),
                "total_usd": summary.get("totalUsd"),
            }
        )

    if not isinstance(balances, Exception):
        tokens = sorted(
            balances.get("tokens") or balances.get("data") or [],
            key=lambda t: t.get("usdValue", 0),
            reverse=True,
        )
        result["top_holdings"] = [
            {
                "token": t.get("token", {}).get("symbol") or t.get("tokenId"),
                "chain": t.get("chain"),
                "usd_value": t.get("usdValue", 0),
            }
            for t in tokens[:10]
        ]
    else:
        result["top_holdings"] = []

    return json.dumps(result, indent=2)


def register(mcp: FastMCP) -> None:

    @mcp.resource(
        uri="arkham://entity/{slug}",
        name="entity_profile",
        description=(
            "Profile of a known Arkham entity (exchange, fund, protocol, etc). "
            "Includes name, type, total holdings, top tokens, and address count. "
            "Use the entity slug (e.g. 'binance', 'jump-trading'). "
            "Cached for 1 hour."
        ),
        mime_type="application/json",
    )
    async def entity_resource(slug: str, ctx: Context) -> str:
        return await _entity_profile(slug, ctx.lifespan_context["client"])
