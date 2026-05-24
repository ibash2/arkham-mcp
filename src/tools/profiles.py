"""
Profile tools — aggregate multiple API calls into a single coherent response.
These are the primary entry points for address and entity investigation.
"""

import asyncio
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

from .utils import to_table


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

            result["labels"] = [l.get("name") for l in (enriched.get("arkhamLabel") or [])]
            result["predictions"] = to_table([
                {"entity": p.get("entity", {}).get("name"), "confidence": p.get("confidence")}
                for p in (enriched.get("predictedEntity") or [])
            ])
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
            result["top_holdings"] = to_table(top, ["token", "chain", "usd_value", "amount"])
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
            result["top_holdings"] = to_table(_top_balances(balances), ["token", "chain", "usd_value", "amount"])
        else:
            await ctx.warning(f"Balances fetch failed: {balances}")
            result["top_holdings"] = to_table([])

        if not isinstance(predictions, Exception):
            pred_list = predictions.get("predictions") if isinstance(predictions, dict) else (predictions if isinstance(predictions, list) else [])
            result["predicted_addresses"] = to_table([
                {
                    "address": p.get("address"),
                    "chain": p.get("chain"),
                    "confidence": p.get("confidence"),
                }
                for p in pred_list[:20]
            ])
        else:
            await ctx.warning(f"Predictions fetch failed: {predictions}")
            result["predicted_addresses"] = []

        return result

    @mcp.tool(
        name="investigate_address",
        description=(
            "ALWAYS call this tool first when asked to investigate, analyze, research, "
            "or identify a blockchain address or wallet. "
            "Returns a step-by-step investigation plan — follow every step in order. "
            "depth: 'full' (default) for complete analysis, 'quick' for a brief summary."
        ),
    )
    async def investigate_address(address: str, ctx: Context, depth: str = "full") -> str:
        import time as _time
        now_ms = int(_time.time() * 1000)
        from_ms = now_ms - 2_592_000_000  # 30 days ago

        if depth == "quick":
            return (
                f"Quick investigation of `{address}` — follow these steps:\n\n"
                f"1. Call `resolve_address(\"{address}\")` — identify the owner.\n"
                f"2. Call `get_transfers(base=\"{address}\", time_last=\"7d\", sort_key=\"usd\", sort_dir=\"desc\", limit=20)` — largest transfers.\n"
                f"3. Call `get_portfolio(\"{address}\")` — current holdings.\n"
                f"4. Write a 3-sentence summary: who, what they hold, any red flags."
            )

        return f"""Investigation plan for `{address}` — execute every step in order:

**Step 1 — Resolve identity**
Call `resolve_address("{address}")`.
- If `is_identified=true`: note entity name, type, labels.
- If `is_identified=false`: mark UNKNOWN and proceed with caution.

**Step 2 — Current portfolio**
Call `get_portfolio("{address}")`.
- List top 5 holdings by USD value.
- Flag unusual tokens (obscure DeFi, wrapped assets).

**Step 3 — Portfolio changes (30d)**
Call `get_portfolio_change("{address}", from_ts={from_ms}, to_ts={now_ms})`.
- added = new positions opened. removed = positions closed.
- changed: delta_balance > 0 means accumulating (buying), delta_balance < 0 means distributing (selling).

**Step 4 — Analyze transfers**
Call `get_transfers(base="{address}", time_last="30d", sort_key="usd", sort_dir="desc", limit=50)`.
- Largest inflows and outflows. Notable counterparties.
- Flag mixers, sanctioned addresses, recurring patterns.

**Step 5 — Trace outgoing funds**
Call `trace_fund_flow("{address}", time_last="7d")`.
- Destinations: entity, type, volume. Group: exchanges vs unknown.
- Highlight suspicious_flags.
"""
