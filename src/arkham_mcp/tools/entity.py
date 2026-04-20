"""
Entity tools — thin wrappers for entity-specific API endpoints.
"""

from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="get_entity_balance_changes",
        description=(
            "Ranked leaderboard of entities with the largest balance changes over a time period. "
            "Useful for spotting who is accumulating or distributing a token. "
            "interval: '24h' | '7d' | '30d' (preferred). "
            "order_by: 'balance_usd_pct_change' | 'balance_usd_change' (default: pct_change). "
            "pricing_ids: CoinGecko token ID to filter by token (e.g. 'bitcoin', 'skyai'). "
            "balance_min: exclude entities below this USD balance (e.g. 100000). "
            "entity_types: comma-separated types e.g. 'cex,fund'. "
            "entity_ids: comma-separated entity slugs."
        ),
    )
    async def get_entity_balance_changes(
        ctx: Context,
        interval: Optional[str] = "7d",
        order_by: Optional[str] = "balance_usd_pct_change",
        order_dir: Optional[str] = "desc",
        pricing_ids: Optional[str] = None,
        balance_min: Optional[float] = None,
        entity_types: Optional[str] = None,
        entity_ids: Optional[str] = None,
        entity_tags: Optional[str] = None,
        chains: Optional[str] = None,
        limit: Optional[int] = 50,
        offset: Optional[int] = None,
    ) -> dict:
        return await ctx.lifespan_context["client"].get_entity_balance_changes(
            interval=interval,
            order_by=order_by,
            order_dir=order_dir,
            pricing_ids=pricing_ids,
            balance_min=balance_min,
            entity_types=entity_types,
            entity_ids=entity_ids,
            entity_tags=entity_tags,
            chains=chains,
            limit=limit,
            offset=offset,
        )

    @mcp.tool(
        name="get_entity_counterparties",
        description=(
            "Get top transaction counterparties for a known entity (e.g. 'binance'). "
            "flow: 'in' | 'out' | 'all'. time_last: '24h' | '7d' | '30d'."
        ),
    )
    async def get_entity_counterparties(
        entity: str,
        ctx: Context,
        flow: Optional[str] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        return await ctx.lifespan_context["client"].get_entity_counterparties(
            entity,
            flow=flow,
            time_last=time_last,
            chains=chains,
            limit=limit,
        )

    @mcp.tool(
        name="get_entity_flow",
        description=(
            "Get historical USD inflow/outflow data for a known entity. "
            "flow: 'in' | 'out' | 'all'. time_last: '24h' | '7d' | '30d'."
        ),
    )
    async def get_entity_flow(
        entity: str,
        ctx: Context,
        flow: Optional[str] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
    ) -> dict:
        return await ctx.lifespan_context["client"].get_entity_flow(
            entity,
            flow=flow,
            time_last=time_last,
            chains=chains,
        )

    @mcp.tool(
        name="get_entity_history",
        description=(
            "Get historical USD balance snapshots for a known entity. "
            "time_last: '24h' | '7d' | '30d'."
        ),
    )
    async def get_entity_history(
        entity: str,
        ctx: Context,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
    ) -> dict:
        return await ctx.lifespan_context["client"].get_entity_history(
            entity,
            time_last=time_last,
            chains=chains,
        )

    @mcp.tool(
        name="get_entity_loans",
        description=(
            "Get active DeFi loan positions (supplied, borrowed, collateral) for a known entity. "
            "Covers Aave, Compound, and other lending protocols."
        ),
    )
    async def get_entity_loans(entity: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_entity_loans(entity)
