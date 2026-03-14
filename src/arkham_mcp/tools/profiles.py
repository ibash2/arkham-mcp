"""
Profile tools — aggregate multiple API calls into a single coherent response.
These are the primary entry points for address and entity investigation.
"""

import asyncio
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context


def _top_balances(balances_data: dict, top_n: int = 10) -> list[dict]:
    """Extract and sort top holdings by USD value."""
    tokens = balances_data.get("tokens") or balances_data.get("data") or []
    sorted_tokens = sorted(tokens, key=lambda t: t.get("usdValue", 0), reverse=True)
    return [
        {
            "token": t.get("token", {}).get("symbol") or t.get("tokenId"),
            "chain": t.get("chain"),
            "usd_value": t.get("usdValue", 0),
            "amount": t.get("amount"),
        }
        for t in sorted_tokens[:top_n]
    ]


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="resolve_address",
        description=(
            "Identify who owns a blockchain address. "
            "Returns entity name, labels, ML predictions, chain presence, "
            "and current top token holdings. "
            "Always call this first when investigating an unknown address."
        ),
    )
    async def resolve_address(address: str, ctx: Context) -> dict:
        client = ctx.lifespan_context["client"]

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

        result: dict = {"address": address}

        # --- identity ---
        if not isinstance(enriched, Exception) and isinstance(enriched, dict):
            entity = enriched.get("arkhamEntity") or {}
            result["entity"] = {
                "name": entity.get("name"),
                "type": entity.get("type"),
                "website": entity.get("website"),
                "twitter": entity.get("twitter"),
            } if entity else None

            result["labels"] = enriched.get("arkhamLabel") or []
            result["predictions"] = [
                {"entity": p.get("entity", {}).get("name"), "confidence": p.get("confidence")}
                for p in (enriched.get("predictedEntity") or [])
            ]
            result["chains"] = enriched.get("chains") or []
            result["tags"] = [
                t.get("name") for t in (enriched.get("populatedTags") or [])
            ]
            result["cluster_id"] = enriched.get("clusterId")
        else:
            await ctx.warning(f"Could not fetch enriched data: {enriched}")
            result["entity"] = None
            result["labels"] = []
            result["predictions"] = []

        # --- balances ---
        if not isinstance(balances, Exception) and isinstance(balances, dict):
            top = _top_balances(balances)
            total_usd = sum(b["usd_value"] for b in top)
            result["top_holdings"] = top
            result["total_usd"] = total_usd
        else:
            await ctx.warning(f"Could not fetch balances: {balances}")
            result["top_holdings"] = []
            result["total_usd"] = None

        result["is_identified"] = bool(result.get("entity") and result["entity"].get("name"))
        return result

    @mcp.tool(
        name="get_entity_profile",
        description=(
            "Get a full profile for a known Arkham entity (e.g. 'binance', 'jump-trading'). "
            "Aggregates entity metadata, statistics, token holdings, and predicted addresses. "
            "Use search() first if you are unsure about the exact entity slug."
        ),
    )
    async def get_entity_profile(entity: str, ctx: Context) -> dict:
        client = ctx.lifespan_context["client"]

        entity_data, summary, balances, predictions = await asyncio.gather(
            client.get_entity(entity),
            client.get_entity_summary(entity),
            client.get_entity_balances(entity),
            client.get_entity_predictions(entity),
            return_exceptions=True,
        )

        result: dict = {"entity_slug": entity}

        if not isinstance(entity_data, Exception) and isinstance(entity_data, dict):
            result["name"] = entity_data.get("name")
            result["type"] = entity_data.get("type")
            result["website"] = entity_data.get("website")
            result["twitter"] = entity_data.get("twitter")
            result["description"] = entity_data.get("description")
        else:
            await ctx.warning(f"Entity fetch failed: {entity_data}")

        if not isinstance(summary, Exception) and isinstance(summary, dict):
            result["address_count"] = summary.get("addressCount")
            result["chain_count"] = summary.get("chainCount")
            result["total_usd"] = summary.get("totalUsd")
        else:
            await ctx.warning(f"Summary fetch failed: {summary}")

        if not isinstance(balances, Exception) and isinstance(balances, dict):
            result["top_holdings"] = _top_balances(balances)
        else:
            await ctx.warning(f"Balances fetch failed: {balances}")
            result["top_holdings"] = []

        if not isinstance(predictions, Exception):
            pred_list = predictions.get("predictions") if isinstance(predictions, dict) else (predictions if isinstance(predictions, list) else [])
            result["predicted_addresses"] = [
                {
                    "address": p.get("address"),
                    "chain": p.get("chain"),
                    "confidence": p.get("confidence"),
                }
                for p in pred_list[:20]
            ]
        else:
            await ctx.warning(f"Predictions fetch failed: {predictions}")
            result["predicted_addresses"] = []

        return result

    @mcp.tool(
        name="compare_addresses",
        description=(
            "Compare multiple blockchain addresses side by side. "
            "Returns a table with entity, labels, total USD holdings, and chains for each. "
            "Accepts up to 1000 addresses. "
            "Useful for determining if a group of addresses belongs to the same entity."
        ),
    )
    async def compare_addresses(addresses: list[str], ctx: Context) -> list[dict]:
        if not addresses:
            return []

        client = ctx.lifespan_context["client"]

        enriched_batch, *balances_list = await asyncio.gather(
            client.batch_addresses_enriched(addresses),
            *[client.get_address_balances(addr) for addr in addresses],
            return_exceptions=True,
        )

        if isinstance(enriched_batch, Exception):
            raise RuntimeError(f"Batch enriched lookup failed: {enriched_batch}")

        results = []
        for i, item in enumerate(enriched_batch):
            addr = addresses[i]
            if not isinstance(item, dict):
                results.append({"address": addr, "error": f"unexpected response: {item}"})
                continue
            entity = item.get("arkhamEntity") or {}
            balances = balances_list[i] if i < len(balances_list) else None

            total_usd = None
            top_token = None
            if not isinstance(balances, Exception) and balances:
                tokens = sorted(
                    balances.get("tokens") or balances.get("data") or [],
                    key=lambda t: t.get("usdValue", 0),
                    reverse=True,
                )
                total_usd = sum(t.get("usdValue", 0) for t in tokens)
                top_token = tokens[0].get("token", {}).get("symbol") if tokens else None

            results.append({
                "address": addr,
                "entity_name": entity.get("name"),
                "entity_type": entity.get("type"),
                "labels": [lbl.get("name") for lbl in (item.get("arkhamLabel") or [])],
                "tags": [t.get("name") for t in (item.get("populatedTags") or [])],
                "chains": item.get("chains") or [],
                "total_usd": total_usd,
                "top_token": top_token,
                "cluster_id": item.get("clusterId"),
            })

        return results
