"""
Token investigation tools — analyse a specific token from all angles.
"""

import asyncio
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

from .utils import to_table


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="get_token_holders",
        description=(
            "Top holders of a token. "
            "token: CoinGecko ID or symbol (e.g. 'bitcoin', 'skyai'). "
            "group_by_entity: true = aggregate wallets belonging to the same entity. "
            "min_usd: filter out holders below this USD value (default 0). "
            "limit: max rows to return (default 20). "
            "Use to assess holder concentration and identify major participants."
        ),
    )
    async def get_token_holders(
        token: str,
        ctx: Context,
        group_by_entity: bool = False,
        min_usd: float = 0,
        limit: int = 20,
    ) -> dict:
        raw = await ctx.lifespan_context["client"].get_token_holders(
            token, group_by_entity=group_by_entity
        )
        if isinstance(raw, list):
            holders = raw
        else:
            holders = (
                raw.get("holders")
                or raw.get("topHolders")
                or raw.get("data")
                or raw.get("accounts")
                or []
            )
        if not holders and isinstance(raw, dict):
            return {"token": token, "_raw_keys": list(raw.keys()), "_raw_sample": raw}
        rows = []
        for h in holders:
            entity = h.get("arkhamEntity") or {}
            usd = h.get("usdValue") or h.get("usd") or 0
            if usd < min_usd:
                continue
            rows.append({
                "address":     (h.get("address") or {}).get("address") or h.get("address"),
                "entity":      entity.get("name"),
                "entity_type": entity.get("type"),
                "balance":     h.get("balance"),
                "usd_value":   usd,
                "pct_supply":  h.get("pctOfCirculatingSupply") or h.get("pct"),
            })
        rows = rows[:limit]
        return {
            "token":   token,
            "holders": to_table(rows, ["address", "entity", "entity_type", "balance", "usd_value", "pct_supply"]),
        }

    @mcp.tool(
        name="get_token_market",
        description=(
            "Current market data for a token: price, 24h change, volume, market cap, "
            "circulating supply, FDV. "
            "token: CoinGecko ID or symbol (e.g. 'bitcoin', 'skyai')."
        ),
    )
    async def get_token_market(token: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_token_market(token)

    @mcp.tool(
        name="get_token_top_flow",
        description=(
            "Top on-chain flows for a token — biggest addresses moving the token in/out. "
            "token: CoinGecko ID or symbol. "
            "time_last: '1h' | '24h' | '7d' | '30d' (default '24h'). "
            "chains: comma-separated chain filter (optional)."
        ),
    )
    async def get_token_top_flow(
        token: str,
        ctx: Context,
        time_last: str = "24h",
        chains: Optional[str] = None,
    ) -> dict:
        raw = await ctx.lifespan_context["client"].get_token_top_flow(
            token, time_last=time_last, chains=chains
        )
        items = raw if isinstance(raw, list) else (raw.get("data") or raw.get("flows") or [])
        rows = []
        for item in items:
            addr_obj = item.get("address") or {}
            entity = addr_obj.get("arkhamEntity") or {}
            label = addr_obj.get("arkhamLabel") or {}
            rows.append({
                "address":     addr_obj.get("address"),
                "entity":      entity.get("name"),
                "entity_type": entity.get("type"),
                "label":       label.get("name"),
                "chain":       addr_obj.get("chain"),
                "contract":    addr_obj.get("contract"),
                "in_usd":      round(item.get("inUSD") or 0, 2),
                "out_usd":     round(item.get("outUSD") or 0, 2),
                "net_usd":     round((item.get("inUSD") or 0) - (item.get("outUSD") or 0), 2),
                "in_value":    round(item.get("inValue") or 0, 2),
                "out_value":   round(item.get("outValue") or 0, 2),
            })
        rows.sort(key=lambda r: abs(r["in_usd"]) + abs(r["out_usd"]), reverse=True)
        return {
            "token":   token,
            "period":  time_last,
            "flows":   to_table(rows, ["address", "entity", "entity_type", "label", "chain",
                                       "contract", "in_usd", "out_usd", "net_usd",
                                       "in_value", "out_value"]),
        }

    @mcp.tool(
        name="get_token_liquidity_pools",
        description=(
            "Find liquidity pools for a token. "
            "token: CoinGecko ID or symbol. "
            "time_last: '24h' | '7d' | '30d' (default '7d')."
        ),
    )
    async def get_token_liquidity_pools(
        token: str,
        ctx: Context,
        time_last: str = "7d",
    ) -> dict:
        raw = await ctx.lifespan_context["client"].get_token_top_flow(token, time_last=time_last)
        items = raw if isinstance(raw, list) else (raw.get("data") or raw.get("flows") or [])

        seen: set[str] = set()
        rows = []
        for item in items:
            addr_obj = item.get("address") or {}
            if not addr_obj.get("contract"):
                continue
            entity = addr_obj.get("arkhamEntity") or {}
            label = addr_obj.get("arkhamLabel") or {}
            label_name = label.get("name") or ""
            is_pool = entity.get("type") == "dex" or "pool" in label_name.lower()
            if not is_pool:
                continue
            addr = addr_obj.get("address")
            if not addr or addr in seen:
                continue
            seen.add(addr)
            rows.append({
                "address": addr,
                "chain":   addr_obj.get("chain"),
                "dex":     entity.get("name"),
                "label":   label_name,
            })

        return {
            "token": token,
            "pools": to_table(rows, ["address", "chain", "dex", "label"]),
        }

    @mcp.tool(
        name="analyze_exit_liquidity",
        description=(
            "Analyze whether one or more wallets can exit a token position without crashing the price. "
            "Returns a step-by-step instruction plan — follow every step in order. "
            "token: CoinGecko ID or symbol. "
            "addresses: list of wallet addresses to check (e.g. ['0xabc...', '0xdef...']). "
            "Use when you want to assess sell pressure risk or detect 'trapped' holders."
        ),
    )
    async def analyze_exit_liquidity(
        token: str,
        addresses: list[str],
        ctx: Context,
    ) -> str:
        addr_list = "\n".join(f'  - `{a}`' for a in addresses)
        addrs_repr = ", ".join(f'"{a}"' for a in addresses)
        return f"""Exit liquidity analysis for `{token}` — execute every step in order:

**Step 1 — Token market data**
Call `get_token_market("{token}")`.
- Note current price, market cap, 24h volume.

**Step 2 — Wallet holdings**
For each address, call `get_portfolio(address)`:
{addr_list}
- Find the `{token}` position: balance and USD value.
- Sum total USD held across all wallets — this is the combined sell pressure.

**Step 3 — Find liquidity pools**
Call `get_token_liquidity_pools("{token}")`.
- List all DEX pools: address, chain, DEX name.

**Step 4 — Pool reserves**
For each pool address from Step 3, call `get_portfolio(pool_address)`.
- Extract token reserves: how much `{token}` and how much paired asset (USDT/BNB/ETH etc.) is in each pool.
- Sum all `{token}` reserves across pools — this is total available liquidity.

**Step 5 — Price impact calculation**
For each pool apply x·y=k formula:
- reserve_token = USD value of `{token}` side of pool
- price_impact = sell_usd / (reserve_token + sell_usd) × 100%

Calculate for each wallet individually and for all wallets combined ({addrs_repr}):
- What % price drop if one wallet sells?
- What % price drop if all wallets sell simultaneously?

**Step 6 — Conclusion**
Answer these questions:
1. Can the wallets exit without moving price more than 5–10%?
2. If no — what is the realistic exit price (accounting for slippage)?
3. Are the holders likely "trapped" (position too large relative to liquidity)?
4. Is there asymmetry — do some wallets hold far more than the pool can absorb?

Write a concise verdict: EXIT POSSIBLE / PARTIALLY POSSIBLE / TRAPPED.
"""

    @mcp.tool(
        name="investigate_token",
        description=(
            "ALWAYS call this first when asked to investigate, analyze, or research a token. "
            "Returns a step-by-step investigation plan — follow every step in order. "
            "token: CoinGecko ID or symbol (e.g. 'bitcoin', 'skyai'). "
            "depth: 'full' (default) | 'quick'."
        ),
    )
    async def investigate_token(
        token: str,
        ctx: Context,
        depth: str = "full",
    ) -> str:
        if depth == "quick":
            return (
                f"Quick token investigation of `{token}`:\n\n"
                f"1. `get_token_by_coingecko_id(\"{token}\")` — metadata and identity.\n"
                f"2. `get_token_market(\"{token}\")` — price, volume, market cap.\n"
                f"3. `get_token_holders(\"{token}\", group_by_entity=true)` — top holders.\n"
                f"4. Write 3-sentence summary: what the token is, who holds it, any red flags."
            )

        return f"""Token investigation plan for `{token}` — execute every step in order:

**Step 1 — Token identity**
Call `get_token_by_coingecko_id("{token}")`.
- Note name, symbol, linked entity, chains.

**Step 2 — Market data**
Call `get_token_market("{token}")`.
- Current price, 24h change %, volume, market cap, circulating supply, FDV.
- Flag: FDV >> market cap = large unlock risk.

**Step 3 — Top holders**
Call `get_token_holders("{token}", group_by_entity=true)`.
- Identify concentration: top 10 hold what % of supply?
- Are large holders identified entities (VCs, funds, CEX) or unknown wallets?

**Step 4 — Recent large transfers**
Call `get_transfers(tokens="{token}", base="all", sort_key="usd", sort_dir="desc", time_last="7d", limit=30)`.
- Large sends to CEX = potential sell pressure.
- Large CEX withdrawals = accumulation signal.

**Step 5 — Entity balance changes (7d)**
Call `get_entity_balance_changes(pricing_ids="{token}", interval="7d", order_by="balance_usd_pct_change", order_dir="desc", balance_min=100000, limit=20)`.
- Who is accumulating (pct_change > 0) vs distributing (pct_change < 0)?

**Step 6 — Token top flow (24h)**
Call `get_token_top_flow("{token}", time_last="24h")`.
- Where is the token flowing right now? Identify dominant routes.

**Step 7 — Funding rates (perps)**
Call `get_funding_rates("{token}", exchanges="binance,okx,bybit,deribit", time_period="7d", token_margined=false)`.
- Positive funding = longs paying shorts (bullish bias).
- Negative funding = shorts paying longs (bearish bias).

**Step 8 — Open interest (30d)**
Call `get_open_interest("{token}", exchanges="binance,okx,bybit,deribit", instrument_type="perp", time_period="30d")`.
- Rising OI + rising price = trend strength. Rising OI + falling price = short buildup.

**Step 9 — Exchange volumes (24h)**
Call `get_volume_timeseries("{token}", exchanges="binance,bybit,okx,deribit", instrument_type="perp", time_period="24h")`.
- Volume spikes = catalysts. Compare spot vs perp volume ratio.

**Step 10 — Write analysis**
Summarise: token overview, holder structure, capital flow (accumulation or distribution?),
derivatives positioning, risk flags (concentration, unlock risk, unknown buyers, wash trading signals).
"""
