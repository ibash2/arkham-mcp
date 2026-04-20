"""
Activity tools — address flow summaries and DeFi positions.
"""

import asyncio
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

from .utils import to_table


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="get_address_activity",
        description=(
            "Get a summary of an address's on-chain activity over a time period. "
            "Aggregates inflow/outflow totals and top counterparties in a single call. "
            "time_last: '24h' | '7d' | '30d' (default '30d'). "
            "flow: 'in' | 'out' | 'all' (default 'all'). "
            "chains: comma-separated e.g. 'ethereum,bsc' (optional)."
        ),
    )
    async def get_address_activity(
        address: str,
        ctx: Context,
        time_last: str = "30d",
        flow: str = "all",
        chains: Optional[str] = None,
        top_counterparties: int = 10,
    ) -> dict:
        client = ctx.lifespan_context["client"]

        flow_data, counterparties = await asyncio.gather(
            client.get_address_flow(address, time_last=time_last, flow=flow, chains=chains),
            client.get_counterparties(
                address,
                time_last=time_last,
                chains=chains,
                limit=top_counterparties,
                sort_key="volumeUsd",
                sort_dir="desc",
            ),
            return_exceptions=True,
        )

        result: dict = {"address": address, "period": time_last, "chains_filter": chains}

        if not isinstance(flow_data, Exception) and isinstance(flow_data, dict):
            snapshots = flow_data.get("data") or flow_data.get("snapshots") or []
            total_in = sum(s.get("inflow", 0) or 0 for s in snapshots)
            total_out = sum(s.get("outflow", 0) or 0 for s in snapshots)
            result["total_inflow_usd"] = total_in
            result["total_outflow_usd"] = total_out
            result["net_flow_usd"] = total_in - total_out
            result["flow_snapshots"] = snapshots
        else:
            await ctx.warning(f"Flow fetch failed: {flow_data}")
            result["total_inflow_usd"] = None
            result["total_outflow_usd"] = None
            result["net_flow_usd"] = None
            result["flow_snapshots"] = []

        if not isinstance(counterparties, Exception) and isinstance(counterparties, dict):
            cp_list = counterparties.get("counterparties") or counterparties.get("data") or []
            result["top_counterparties"] = to_table([
                {
                    "address":     cp.get("address"),
                    "entity_name": (cp.get("arkhamEntity") or {}).get("name"),
                    "entity_type": (cp.get("arkhamEntity") or {}).get("type"),
                    "labels":      ", ".join(lbl.get("name", "") for lbl in (cp.get("arkhamLabel") or [])),
                    "volume_usd":  cp.get("volumeUsd"),
                    "tx_count":    cp.get("txCount"),
                    "direction":   cp.get("direction") or flow,
                }
                for cp in cp_list
            ])
        else:
            await ctx.warning(f"Counterparties fetch failed: {counterparties}")
            result["top_counterparties"] = []

        return result

    @mcp.tool(
        name="get_address_loans",
        description=(
            "Get active DeFi loan positions (supplied, borrowed, collateral) for an address. "
            "Covers Aave, Compound, and other lending protocols."
        ),
    )
    async def get_address_loans(address: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_address_loans(address)
