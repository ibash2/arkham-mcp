"""
Transfer tools — on-chain transfers, swaps, and statistical analysis.
"""

from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

from .utils import (
    _is_fake_token,
    amount_stats,
    compact_transfer,
    counterparty_stats,
    meta_from_transfers,
    timing_stats,
    to_table,
)


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="get_transfers",
        description=(
            "Get on-chain token transfers with rich filtering. "
            "The most powerful Arkham endpoint — returns individual transfer records with entity labels.\n"
            "PARAMETERS:\n"
            "  base       — pivot address or entity (e.g. '0xabc' or 'binance')\n"
            "  flow       — 'in' | 'out' | 'self' | 'all'\n"
            "  from_addr  — filter by sender; supports 'type:cex', 'deposit:binance', comma-separated\n"
            "  to         — filter by receiver; same syntax as from_addr\n"
            "  tokens     — comma-separated token IDs or contract addresses\n"
            "  chains     — comma-separated chain names (e.g. 'bsc,ethereum')\n"
            "  time_last  — relative window: '1h' | '24h' | '7d' | '30d'\n"
            "  time_gte   — absolute start time as Unix milliseconds\n"
            "  time_lte   — absolute end time as Unix milliseconds\n"
            "  usd_gte    — minimum transfer value in USD (string, e.g. '1000')\n"
            "  usd_lte    — maximum transfer value in USD (string, e.g. '50000')\n"
            "  sort_key   — 'time' | 'value' | 'usd'\n"
            "  sort_dir   — 'asc' | 'desc'\n"
            "  limit      — max records to return (default 50)\n"
            "  offset     — skip N records for pagination\n"
            "  compact    — true (default): slim records + _meta summary; false: raw API response\n"
            "Rate-limited to 1 req/sec."
        ),
    )
    async def get_transfers(
        ctx: Context,
        base: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
        from_addr: Optional[str] = None,
        to: Optional[str] = None,
        tokens: Optional[str] = None,
        counterparties: Optional[str] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = 50,
        offset: Optional[int] = None,
        compact: bool = True,
    ) -> dict:
        raw = await ctx.lifespan_context["client"].get_transfers(
            base=base,
            chains=chains,
            flow=flow,
            from_addr=from_addr,
            to=to,
            tokens=tokens,
            counterparties=counterparties,
            time_last=time_last,
            time_gte=time_gte,
            time_lte=time_lte,
            usd_gte=usd_gte,
            usd_lte=usd_lte,
            sort_key=sort_key,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        if not compact:
            return raw
        transfers = (raw or {}).get("transfers") or []
        return {
            "_meta":     meta_from_transfers(transfers),
            "transfers": [compact_transfer(t) for t in transfers],
        }

    @mcp.tool(
        name="get_transfers_by_tx",
        description=(
            "Get all token and native transfers within a specific transaction. "
            "Returns enriched transfer objects with entity labels. "
            "transfer_type: 'external' | 'internal' | 'token'."
        ),
    )
    async def get_transfers_by_tx(
        tx_hash: str,
        ctx: Context,
        chain: Optional[str] = None,
        transfer_type: Optional[str] = None,
    ) -> list:
        return await ctx.lifespan_context["client"].get_transfers_by_tx(
            tx_hash,
            chain=chain,
            transfer_type=transfer_type,
        )

    @mcp.tool(
        name="get_transfers_histogram",
        description=(
            "Get transfer count/volume histogram bucketed by time. "
            "Useful for visualizing flow patterns and activity spikes over time. "
            "time_last: '1h' | '24h' | '7d' | '30d'. "
            "time_gte / time_lte: Unix milliseconds for precise ranges."
        ),
    )
    async def get_transfers_histogram(
        ctx: Context,
        base: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
        from_addr: Optional[str] = None,
        to: Optional[str] = None,
        tokens: Optional[str] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
    ) -> list:
        return await ctx.lifespan_context["client"].get_transfers_histogram_simple(
            base=base,
            chains=chains,
            flow=flow,
            from_addr=from_addr,
            to=to,
            tokens=tokens,
            time_last=time_last,
            time_gte=time_gte,
            time_lte=time_lte,
            usd_gte=usd_gte,
            usd_lte=usd_lte,
        )

    @mcp.tool(
        name="get_transfer_stats",
        description=(
            "Fetch transfers and compute statistical summary: timing distribution, "
            "amount spread, counterparty concentration, and fake-token count. "
            "Use when you need quantitative insight into transfer behaviour — "
            "volumes, intervals, unique senders/receivers. "
            "base: pivot address or entity. flow: 'in'|'out'|'all'. "
            "time_last: '24h'|'7d'|'30d'. tokens: comma-separated token IDs. "
            "include_raw: set true to also return individual transfer records."
        ),
    )
    async def get_transfer_stats(
        ctx: Context,
        base: Optional[str] = None,
        flow: Optional[str] = None,
        time_last: Optional[str] = "7d",
        tokens: Optional[str] = None,
        chains: Optional[str] = None,
        from_addr: Optional[str] = None,
        to: Optional[str] = None,
        usd_gte: Optional[str] = None,
        limit: int = 100,
        include_raw: bool = False,
    ) -> dict:
        client = ctx.lifespan_context["client"]
        raw = await client.get_transfers(
            base=base,
            flow=flow,
            time_last=time_last,
            tokens=tokens,
            chains=chains,
            from_addr=from_addr,
            to=to,
            usd_gte=usd_gte,
            sort_key="time",
            sort_dir="asc",
            limit=limit,
        )
        transfers = (raw or {}).get("transfers") or []
        if not transfers:
            return {"total_transfers_analyzed": 0}

        fake_count = sum(1 for t in transfers if _is_fake_token(t))
        result: dict = {
            "total_transfers_analyzed": len(transfers),
            "fake_token_count":         fake_count,
            "timing":                   timing_stats(transfers),
            "amounts":                  amount_stats(transfers),
            "counterparties":           counterparty_stats(transfers, pivot=base),
        }
        if include_raw:
            result["transfers"] = [compact_transfer(t) for t in transfers]
        return result

    @mcp.tool(
        name="get_swaps",
        description=(
            "Get DEX/swap activity for an address or entity. "
            "Returns trades with token pairs, amounts, DEX used, and timestamps. "
            "Rate-limited to 1 request/second. "
            "Provide either base (address) or entity_slug, not both.\n"
            "PARAMETERS:\n"
            "  base        — pivot address (e.g. '0xabc...')\n"
            "  entity_slug — entity slug (e.g. 'binance')\n"
            "  chains      — comma-separated chain names (e.g. 'ethereum,bsc')\n"
            "  token_from  — token sold in the swap\n"
            "  token_to    — token bought in the swap\n"
            "  protocols   — DEX protocol filter (e.g. 'pancakeswap,uniswap')\n"
            "  usd_gte     — min trade value in USD\n"
            "  usd_lte     — max trade value in USD\n"
            "  time_last   — '1h' | '24h' | '7d' | '30d'\n"
            "  sort_key    — 'time' | 'usd' (default 'time')\n"
            "  sort_dir    — 'asc' | 'desc' (default 'desc')\n"
            "  limit       — max records (default 50)\n"
            "  offset      — pagination offset"
        ),
    )
    async def get_swaps(
        ctx: Context,
        base: Optional[str] = None,
        entity_slug: Optional[str] = None,
        chains: Optional[str] = None,
        token_from: Optional[str] = None,
        token_to: Optional[str] = None,
        protocols: Optional[str] = None,
        usd_gte: Optional[float] = None,
        usd_lte: Optional[float] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        sort_key: Optional[str] = None,
        sort_dir: str = "desc",
        limit: int = 50,
        offset: Optional[int] = None,
    ) -> dict:
        if not base and not entity_slug:
            raise ValueError("Provide either 'base' or 'entity_slug'.")
        raw = await ctx.lifespan_context["client"].get_swaps(
            base=base,
            entity=entity_slug,
            chains=chains,
            token_from=token_from,
            token_to=token_to,
            protocols=protocols,
            usd_gte=usd_gte,
            usd_lte=usd_lte,
            time_last=time_last,
            time_gte=time_gte,
            time_lte=time_lte,
            sort_key=sort_key,
            sort_dir=sort_dir,
            limit=limit,
            offset=offset,
        )
        swaps = raw.get("swaps") or raw.get("data") or []
        rows = [
            {
                "time":       (s.get("blockTimestamp") or "")[:16],
                "chain":      s.get("chain"),
                "protocol":   s.get("protocol") or s.get("dex"),
                "token_in":   (s.get("tokenIn") or s.get("fromToken") or {}).get("symbol"),
                "amount_in":  s.get("amountIn") or s.get("fromAmount"),
                "token_out":  (s.get("tokenOut") or s.get("toToken") or {}).get("symbol"),
                "amount_out": s.get("amountOut") or s.get("toAmount"),
                "usd":        round(s.get("usdValue") or s.get("historicalUSD") or 0, 2),
                "tx":         (s.get("transactionHash") or "")[:12] + "…",
            }
            for s in swaps
        ]
        return {"_meta": {"returned": len(rows)}, "swaps": to_table(rows)}
