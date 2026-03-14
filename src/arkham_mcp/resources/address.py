"""
MCP Resource: arkham://address/{address}

Returns a JSON snapshot of an address:
  entity, labels, predictions, chains, top holdings.

Resources are cached by the MCP client and suitable for inclusion
in context without an explicit tool call.
"""

import asyncio
import json

from fastmcp import FastMCP
from fastmcp.server.context import Context


async def _address_snapshot(address: str, client) -> str:
    """Business logic — testable without FastMCP context injection."""
    enriched, balances = await asyncio.gather(
        client.get_address_enriched(
            address,
            include_tags=True,
            include_clusters=True,
            include_entity_predictions=True,
        ),
        client.get_address_balances(address),
        return_exceptions=True,
    )

    entity = {}
    labels = []
    predictions = []
    chains = []
    tags = []
    top_holdings = []
    total_usd = None

    if not isinstance(enriched, Exception):
        entity = enriched.get("arkhamEntity") or {}
        labels = [lbl.get("name") for lbl in (enriched.get("arkhamLabel") or [])]
        predictions = [
            {"entity": p.get("entity", {}).get("name"), "confidence": p.get("confidence")}
            for p in (enriched.get("predictedEntity") or [])
        ]
        chains = enriched.get("chains") or []
        tags = [t.get("name") for t in (enriched.get("populatedTags") or [])]

    if not isinstance(balances, Exception):
        tokens = sorted(
            balances.get("tokens") or balances.get("data") or [],
            key=lambda t: t.get("usdValue", 0),
            reverse=True,
        )
        total_usd = sum(t.get("usdValue", 0) for t in tokens)
        top_holdings = [
            {
                "token": t.get("token", {}).get("symbol") or t.get("tokenId"),
                "chain": t.get("chain"),
                "usd_value": t.get("usdValue", 0),
            }
            for t in tokens[:10]
        ]

    return json.dumps(
        {
            "address": address,
            "entity": {
                "name": entity.get("name"),
                "type": entity.get("type"),
                "website": entity.get("website"),
            }
            if entity.get("name")
            else None,
            "labels": labels,
            "predictions": predictions,
            "chains": chains,
            "tags": tags,
            "top_holdings": top_holdings,
            "total_usd": total_usd,
            "is_identified": bool(entity.get("name")),
        },
        indent=2,
    )


def register(mcp: FastMCP) -> None:

    @mcp.resource(
        uri="arkham://address/{address}",
        name="address_profile",
        description=(
            "Blockchain address identity snapshot. "
            "Includes entity name, labels, ML predictions, chain presence, "
            "and top token holdings. Cached for 15 minutes."
        ),
        mime_type="application/json",
    )
    async def address_resource(address: str, ctx: Context) -> str:
        return await _address_snapshot(address, ctx.lifespan_context["client"])
