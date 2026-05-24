"""
Portfolio tools — snapshot and historical token holdings for addresses.
"""

import asyncio
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

from .utils import to_table


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="get_portfolio",
        description=(
            "Get current token portfolio for an address. "
            "Returns all token holdings with USD values at the current moment. "
            "Optionally pass time_ms (Unix milliseconds) to get a historical snapshot."
        ),
    )
    async def get_portfolio(
        address: str,
        ctx: Context,
        time_ms: Optional[int] = None,
    ) -> dict:
        import time as _time
        raw = await ctx.lifespan_context["client"].get_portfolio(
            address, time=time_ms if time_ms is not None else int(_time.time() * 1000)
        )
        rows = []
        for chain, tokens in raw.items():
            if not isinstance(tokens, dict):
                continue
            for token_id, t in tokens.items():
                if not isinstance(t, dict):
                    continue
                rows.append({
                    "token":    t.get("symbol") or token_id,
                    "name":     t.get("name"),
                    "token_id": token_id,
                    "chain":    chain,
                    "balance":  t.get("balance"),
                    "price":    t.get("price"),
                    "usd":      round(t.get("usd") or 0, 2),
                })
        rows.sort(key=lambda r: r["usd"], reverse=True)
        total = sum(r["usd"] for r in rows)
        return {
            "address":   address,
            "total_usd": round(total, 2),
            "holdings":  to_table(rows, ["token", "name", "token_id", "chain", "balance", "price", "usd"]),
        }

    @mcp.tool(
        name="get_portfolio_change",
        description=(
            "Use this tool to answer questions about portfolio changes, token accumulation, "
            "buying/selling activity, or balance growth over time. "
            "DO NOT use get_transfers for this — use this tool instead. "
            "Compares token balances between two timestamps and returns: "
            "added (new tokens), removed (closed positions), changed (balance increased = buying, decreased = selling). "
            "Timestamps are Unix milliseconds. "
            "Example: to find what a wallet is accumulating, look at changed rows where delta_balance > 0."
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
            client.get_portfolio(address, time=from_ts),
            client.get_portfolio(address, time=to_ts),
            return_exceptions=True,
        )

        if isinstance(before, Exception):
            raise RuntimeError(f"Portfolio (before) fetch failed: {before}")
        if isinstance(after, Exception):
            raise RuntimeError(f"Portfolio (after) fetch failed: {after}")

        def to_map(portfolio_data: dict) -> dict[str, dict]:
            result = {}
            for chain, tokens in portfolio_data.items():
                if not isinstance(tokens, dict):
                    continue
                for token_id, t in tokens.items():
                    if not isinstance(t, dict):
                        continue
                    result[f"{chain}:{token_id}"] = {"chain": chain, "token_id": token_id, **t}
            return result

        before_map = to_map(before)
        after_map = to_map(after)
        all_ids = set(before_map) | set(after_map)
        added, removed, changed = [], [], []

        for tid in all_ids:
            b = before_map.get(tid)
            a = after_map.get(tid)
            entry = a or b
            symbol = entry.get("symbol") or entry.get("token_id") or tid
            token_id = entry.get("token_id", tid)
            chain = entry.get("chain", "")

            if b is None:
                added.append({"token": symbol, "token_id": token_id, "chain": chain, "usd_value": round(a.get("usd") or 0, 2)})
            elif a is None:
                removed.append({"token": symbol, "token_id": token_id, "chain": chain, "usd_value": round(b.get("usd") or 0, 2)})
            else:
                bv = b.get("usd") or 0
                av = a.get("usd") or 0
                delta = av - bv
                pct = (delta / bv * 100) if bv else None
                if abs(delta) > 0.01:
                    changed.append({
                        "token":          symbol,
                        "token_id":       token_id,
                        "chain":          chain,
                        "before_balance": b.get("balance") or 0,
                        "after_balance":  a.get("balance") or 0,
                        "before_price":   b.get("price"),
                        "after_price":    a.get("price"),
                        "before_usd":     round(bv, 2),
                        "after_usd":      round(av, 2),
                        "delta_usd":      round(delta, 2),
                        "delta_pct":      round(pct, 2) if pct is not None else None,
                    })

        changed.sort(key=lambda x: abs(x["delta_usd"]), reverse=True)
        net = (
            sum(c["delta_usd"] for c in changed)
            + sum(a["usd_value"] for a in added)
            - sum(r["usd_value"] for r in removed)
        )
        return {
            "address":        address,
            "from_ts":        from_ts,
            "to_ts":          to_ts,
            "net_change_usd": round(net, 2),
            "added":   to_table(sorted(added,   key=lambda x: x["usd_value"], reverse=True), ["token", "token_id", "chain", "usd_value"]),
            "removed": to_table(sorted(removed, key=lambda x: x["usd_value"], reverse=True), ["token", "token_id", "chain", "usd_value"]),
            "changed": to_table(changed, ["token", "token_id", "chain", "before_balance", "after_balance", "before_price", "after_price", "before_usd", "after_usd", "delta_usd", "delta_pct"]),
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
