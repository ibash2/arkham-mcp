"""
Atomic tools — thin wrappers for direct API calls.
Used when the agent already knows exactly what it needs.
"""

from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

from ._transfer_utils import compact_transfer, meta_from_transfers


def register(mcp: FastMCP) -> None:

    @mcp.tool(
        name="search",
        description=(
            "Full-text search across Arkham's database. "
            "Returns matching entities, addresses, and tokens. "
            "Use this first when you only have a name or partial identifier."
        ),
    )
    async def search(query: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].search(query)

    @mcp.tool(
        name="get_token",
        description=(
            "Get token metadata and pricing info by chain and contract address. "
            "Returns name, symbol, price, CoinGecko ID, and linked entity."
        ),
    )
    async def get_token(chain: str, address: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_token_by_address(chain, address)

    @mcp.tool(
        name="get_token_by_coingecko_id",
        description="Get token data using a CoinGecko pricing ID (e.g. 'ethereum', 'usd-coin').",
    )
    async def get_token_by_coingecko_id(coingecko_id: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_token_by_id(coingecko_id)

    @mcp.tool(
        name="get_contract",
        description=(
            "Get contract metadata for a given chain and address. "
            "Returns deployer address, deploy tx, and linked token info."
        ),
    )
    async def get_contract(chain: str, address: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_contract(chain, address)

    @mcp.tool(
        name="get_networks_status",
        description=(
            "Get current status of all supported blockchain networks: "
            "price, 24h volume, gas fees. Useful for market context."
        ),
    )
    async def get_networks_status(ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_networks_status()

    @mcp.tool(
        name="get_network_history",
        description=(
            "Get historical price and volume data for a specific chain. "
            "chain: 'ethereum' | 'bsc' | 'polygon' | 'arbitrum' | 'solana' etc. "
            "time_last: '24h' | '7d' | '30d' (default '7d')."
        ),
    )
    async def get_network_history(
        chain: str,
        ctx: Context,
        time_last: str = "7d",
    ) -> dict:
        return await ctx.lifespan_context["client"].get_network_history(chain, time_last=time_last)

    @mcp.tool(
        name="get_chains",
        description="List all blockchain networks supported by Arkham.",
    )
    async def get_chains(ctx: Context) -> list:
        return await ctx.lifespan_context["client"].get_chains()

    @mcp.tool(
        name="get_entity_types",
        description="List all entity classification types used by Arkham (exchange, fund, bridge, etc.).",
    )
    async def get_entity_types(ctx: Context) -> list:
        return await ctx.lifespan_context["client"].get_entity_types()

    @mcp.tool(
        name="get_arkm_supply",
        description="Get current ARKM token circulating supply.",
    )
    async def get_arkm_supply(ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_arkm_circulating_supply()

    @mcp.tool(
        name="get_altcoin_index",
        description="Get the Arkham altcoin performance index.",
    )
    async def get_altcoin_index(ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_altcoin_index()

    @mcp.tool(
        name="get_funding_rates",
        description=(
            "Get max funding rate time series for a perpetual futures instrument. "
            "Useful for detecting funding spikes, squeeze setups, and long/short bias. "
            "base_token: token ID e.g. 'bitcoin', 'ethereum', 'bulla-3'. "
            "exchanges: comma-separated e.g. 'binance,okx,bybit,deribit,arkham'. "
            "time_period: '1d' | '1w' | '1m' | '3m' | '6m' | '1y'. "
            "token_margined: false = stablecoin-margined (default), true = coin-margined."
        ),
    )
    async def get_funding_rates(
        base_token: str,
        ctx: Context,
        exchanges: Optional[str] = None,
        time_period: Optional[str] = None,
        token_margined: Optional[bool] = None,
    ) -> dict:
        return await ctx.lifespan_context["client"].get_funding_rates(
            base_token,
            exchanges=exchanges,
            time_period=time_period,
            token_margined=token_margined,
        )

    @mcp.tool(
        name="get_entity_balance_changes",
        description=(
            "Ranked leaderboard of entities with the largest balance changes over a time period. "
            "Useful for spotting large capital movements. "
            "time_last: '24h' | '7d' | '30d'. "
            "entity_types: comma-separated types e.g. 'cex,fund'. "
            "entity_ids: comma-separated entity slugs. "
            "entity_tags: comma-separated tags."
        ),
    )
    async def get_entity_balance_changes(
        ctx: Context,
        time_last: Optional[str] = "24h",
        entity_types: Optional[str] = None,
        entity_ids: Optional[str] = None,
        entity_tags: Optional[str] = None,
        chains: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> dict:
        return await ctx.lifespan_context["client"].get_entity_balance_changes(
            time_last=time_last,
            entity_types=entity_types,
            entity_ids=entity_ids,
            entity_tags=entity_tags,
            chains=chains,
            limit=limit,
        )

    @mcp.tool(
        name="get_entity_counterparties",
        description=(
            "Get top transaction counterparties for a known entity (e.g. 'binance'). "
            "Parallel to get_address_activity but for whole entities. "
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
        name="get_address_loans",
        description=(
            "Get active DeFi loan positions (supplied, borrowed, collateral) for an address. "
            "Covers Aave, Compound, and other lending protocols."
        ),
    )
    async def get_address_loans(address: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_address_loans(address)

    @mcp.tool(
        name="get_entity_loans",
        description=(
            "Get active DeFi loan positions (supplied, borrowed, collateral) for a known entity. "
            "Covers Aave, Compound, and other lending protocols."
        ),
    )
    async def get_entity_loans(entity: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_entity_loans(entity)

    @mcp.tool(
        name="get_cluster_summary",
        description=(
            "Get summary statistics for a blockchain address cluster by cluster ID. "
            "Cluster IDs are returned in enriched address lookups (clusterId field)."
        ),
    )
    async def get_cluster_summary(cluster_id: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_cluster_summary(cluster_id)

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
            "  time_gte   — absolute start time as Unix milliseconds (e.g. 1700000000000); use instead of time_last for precise ranges\n"
            "  time_lte   — absolute end time as Unix milliseconds; combine with time_gte for a fixed window\n"
            "  usd_gte    — minimum transfer value in USD (string, e.g. '1000')\n"
            "  usd_lte    — maximum transfer value in USD (string, e.g. '50000')\n"
            "  sort_key   — 'time' | 'value' | 'usd'\n"
            "  sort_dir   — 'asc' | 'desc'\n"
            "  limit      — max records to return (default 50)\n"
            "  offset     — skip N records for pagination (e.g. offset=50 for page 2)\n"
            "  compact    — true (default): slim 11-field records + _meta summary (~65% fewer tokens); false: raw API response for debugging\n"
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
