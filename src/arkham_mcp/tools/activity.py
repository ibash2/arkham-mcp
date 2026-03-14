"""
Activity tools — aggregate flow, history, and portfolio data for addresses.
"""

import asyncio
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context


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
            client.get_address_flow(
                address,
                time_last=time_last,
                flow=flow,
                chains=chains,
            ),
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

        result: dict = {
            "address": address,
            "period": time_last,
            "chains_filter": chains,
        }

        # --- flow summary ---
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

        # --- counterparties ---
        if not isinstance(counterparties, Exception) and isinstance(counterparties, dict):
            cp_list = counterparties.get("counterparties") or counterparties.get("data") or []
            result["top_counterparties"] = [
                {
                    "address": cp.get("address"),
                    "entity_name": (cp.get("arkhamEntity") or {}).get("name"),
                    "entity_type": (cp.get("arkhamEntity") or {}).get("type"),
                    "labels": [lbl.get("name") for lbl in (cp.get("arkhamLabel") or [])],
                    "volume_usd": cp.get("volumeUsd"),
                    "tx_count": cp.get("txCount"),
                    "direction": cp.get("direction") or flow,
                }
                for cp in cp_list
            ]
        else:
            await ctx.warning(f"Counterparties fetch failed: {counterparties}")
            result["top_counterparties"] = []

        return result

    @mcp.tool(
        name="get_portfolio_change",
        description=(
            "Compare an address's token portfolio between two points in time. "
            "Shows added, removed, and changed positions with USD deltas. "
            "Timestamps are Unix milliseconds."
        ),
    )
    async def get_portfolio_change(
        address: str,
        from_ts: int,
        to_ts: int,
        ctx: Context,
    ) -> dict:
        client = ctx.lifespan_context["client"]

        before, after = await asyncio.gather(
            client.get_portfolio(address, time_lte=from_ts),
            client.get_portfolio(address, time_lte=to_ts),
            return_exceptions=True,
        )

        if isinstance(before, Exception):
            raise RuntimeError(f"Portfolio (before) fetch failed: {before}")
        if isinstance(after, Exception):
            raise RuntimeError(f"Portfolio (after) fetch failed: {after}")

        def to_map(portfolio_data: dict) -> dict[str, dict]:
            tokens = portfolio_data.get("tokens") or portfolio_data.get("data") or []
            return {
                (t.get("tokenId") or t.get("token", {}).get("id")): t
                for t in tokens
            }

        before_map = to_map(before)
        after_map = to_map(after)

        all_ids = set(before_map) | set(after_map)

        added, removed, changed = [], [], []

        for tid in all_ids:
            b = before_map.get(tid)
            a = after_map.get(tid)
            symbol = (a or b).get("token", {}).get("symbol") or tid

            if b is None:
                added.append({"token": symbol, "usd_value": a.get("usdValue", 0)})
            elif a is None:
                removed.append({"token": symbol, "usd_value": b.get("usdValue", 0)})
            else:
                bv = b.get("usdValue", 0) or 0
                av = a.get("usdValue", 0) or 0
                delta = av - bv
                pct = (delta / bv * 100) if bv else None
                if abs(delta) > 0.01:
                    changed.append({
                        "token": symbol,
                        "before_usd": bv,
                        "after_usd": av,
                        "delta_usd": delta,
                        "delta_pct": round(pct, 2) if pct is not None else None,
                    })

        changed.sort(key=lambda x: abs(x["delta_usd"]), reverse=True)

        return {
            "address": address,
            "from_ts": from_ts,
            "to_ts": to_ts,
            "net_change_usd": sum(c["delta_usd"] for c in changed)
                + sum(a["usd_value"] for a in added)
                - sum(r["usd_value"] for r in removed),
            "added": sorted(added, key=lambda x: x["usd_value"], reverse=True),
            "removed": sorted(removed, key=lambda x: x["usd_value"], reverse=True),
            "changed": changed,
        }

    @mcp.tool(
        name="get_address_history",
        description=(
            "Get historical USD balance snapshots for an address. "
            "Shows how the total value held changed over time. "
            "time_last: '24h' | '7d' | '30d'. "
            "chains: comma-separated (optional)."
        ),
    )
    async def get_address_history(
        address: str,
        ctx: Context,
        time_last: str = "30d",
        chains: Optional[str] = None,
    ) -> dict:
        return await ctx.lifespan_context["client"].get_address_history(
            address, time_last=time_last, chains=chains
        )

    @mcp.tool(
        name="get_portfolio_timeseries",
        description=(
            "Get daily token-level holdings for an address over time. "
            "Returns a time series broken down by token and chain. "
            "time_last: '7d' | '30d' | '90d'. "
            "pricing_id: CoinGecko ID to price holdings in (e.g. 'bitcoin', 'ethereum')."
        ),
    )
    async def get_portfolio_timeseries(
        address: str,
        ctx: Context,
        pricing_id: Optional[str] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        chains: Optional[str] = None,
    ) -> dict:
        return await ctx.lifespan_context["client"].get_portfolio_timeseries(
            address,
            pricing_id=pricing_id,
            time_last=time_last,
            time_gte=time_gte,
            time_lte=time_lte,
            chains=chains,
        )
