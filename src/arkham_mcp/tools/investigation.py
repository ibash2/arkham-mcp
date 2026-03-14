"""
Investigation tools — multi-step aggregation for fund flow tracing.
These are the most powerful tools for forensic analysis.
"""

import asyncio
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

# Tags that indicate high-risk or opaque destinations
_RISK_TAGS = frozenset({
    "mixer", "tornado", "tornado-cash", "sanctioned", "ofac",
    "darknet", "hack", "exploit", "phishing", "scam",
    "rugpull", "drainer",
})

_EXCHANGE_TYPES = frozenset({"cex", "exchange", "cex-deposit"})


def _extract_risk_flags(entity: dict | None, tags: list[str]) -> list[str]:
    flags = []
    if not entity or not entity.get("name"):
        flags.append("unidentified_destination")
    if entity and entity.get("type") in {"mixer"}:
        flags.append("mixer")
    for tag in tags:
        if tag.lower() in _RISK_TAGS:
            flags.append(tag.lower())
    return flags


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="trace_fund_flow",
        description=(
            "Trace where funds flow from a given address (1 hop). "
            "For each outgoing counterparty: resolves identity, flags risks "
            "(mixers, unknown destinations, high-volume unidentified). "
            "time_last: '24h' | '7d' | '30d' (default '7d'). "
            "min_volume_usd: filter out counterparties below this threshold. "
            "Returns a structured flow graph ready for analysis."
        ),
    )
    async def trace_fund_flow(
        address: str,
        ctx: Context,
        time_last: str = "7d",
        min_volume_usd: float = 0.0,
        chains: Optional[str] = None,
        max_counterparties: int = 20,
    ) -> dict:
        client = ctx.lifespan_context["client"]

        # Step 1: get outgoing counterparties
        await ctx.info(f"Fetching outgoing counterparties for {address}...")
        cp_data = await client.get_counterparties(
            address,
            flow="out",
            time_last=time_last,
            chains=chains,
            limit=max_counterparties,
            sort_key="volumeUsd",
            sort_dir="desc",
        )

        cp_list = cp_data.get("counterparties") or cp_data.get("data") or [] if isinstance(cp_data, dict) else []
        if min_volume_usd > 0:
            cp_list = [cp for cp in cp_list if (cp.get("volumeUsd") or 0) >= min_volume_usd]

        if not cp_list:
            return {
                "origin": address,
                "period": time_last,
                "flows": [],
                "suspicious_flags": [],
                "summary": "No outgoing flows found for the given parameters.",
            }

        # Step 2: batch resolve all counterparty addresses
        cp_addresses = [cp.get("address") for cp in cp_list if cp.get("address")]
        await ctx.info(f"Resolving {len(cp_addresses)} counterparty addresses...")

        enriched_batch = await client.batch_addresses_enriched(cp_addresses)
        enriched_map: dict[str, dict] = {
            item.get("address"): item for item in enriched_batch
            if isinstance(enriched_batch, list)
        }

        # Step 3: build flow graph
        flows = []
        all_flags: list[str] = []

        for cp in cp_list:
            cp_addr = cp.get("address")
            enriched = enriched_map.get(cp_addr, {})
            entity = enriched.get("arkhamEntity") or {}
            labels = [lbl.get("name") for lbl in (enriched.get("arkhamLabel") or [])]
            tags = [t.get("name", "") for t in (enriched.get("populatedTags") or [])]

            entity_type = entity.get("type", "")
            is_exchange = entity_type in _EXCHANGE_TYPES
            is_mixer = entity_type == "mixer" or any(
                t.lower() in _RISK_TAGS for t in tags
            )

            flags = _extract_risk_flags(entity if entity.get("name") else None, tags)
            all_flags.extend(flags)

            flows.append({
                "to_address": cp_addr,
                "to_entity": entity.get("name"),
                "to_entity_type": entity_type or None,
                "to_labels": labels,
                "to_tags": tags,
                "volume_usd": cp.get("volumeUsd"),
                "tx_count": cp.get("txCount"),
                "chains": enriched.get("chains") or [],
                "is_exchange": is_exchange,
                "is_mixer": is_mixer,
                "risk_flags": flags,
            })

        # Step 4: surface origin identity
        origin_enriched = await client.get_address_enriched(address, include_tags=True)
        origin_entity = origin_enriched.get("arkhamEntity") or {}

        return {
            "origin": {
                "address": address,
                "entity": origin_entity.get("name"),
                "entity_type": origin_entity.get("type"),
            },
            "period": time_last,
            "total_outflow_usd": sum(f["volume_usd"] or 0 for f in flows),
            "flows": flows,
            "suspicious_flags": list(set(all_flags)),
            "exchange_destinations": [
                f["to_entity"] for f in flows if f["is_exchange"] and f["to_entity"]
            ],
            "unidentified_count": sum(1 for f in flows if not f["to_entity"]),
        }

    @mcp.tool(
        name="get_swaps",
        description=(
            "Get DEX/swap activity for an address or entity. "
            "Returns trades with token pairs, amounts, DEX used, and timestamps. "
            "Rate-limited to 1 request/second. "
            "Provide either address or entity_slug, not both. "
            "time_last: '24h' | '7d' | '30d'. "
            "flow: 'in' | 'out' | 'all'. "
            "tokens: comma-separated token IDs or contract addresses."
        ),
    )
    async def get_swaps(
        ctx: Context,
        address: Optional[str] = None,
        entity_slug: Optional[str] = None,
        time_last: str = "7d",
        chains: Optional[str] = None,
        flow: Optional[str] = None,
        tokens: Optional[str] = None,
        limit: int = 50,
        sort_dir: str = "desc",
    ) -> dict:
        if not address and not entity_slug:
            raise ValueError("Provide either 'address' or 'entity_slug'.")
        return await ctx.lifespan_context["client"].get_swaps(
            address=address,
            entity=entity_slug,
            time_last=time_last,
            chains=chains,
            flow=flow,
            tokens=tokens,
            limit=limit,
            sort_dir=sort_dir,
        )
