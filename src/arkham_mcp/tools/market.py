"""
Market tools — network status, derivatives data, and market metrics.
"""

from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context


def register(mcp: FastMCP) -> None:

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
            "base_token: token ID e.g. 'bitcoin', 'ethereum', 'skyai'. "
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
        name="get_open_interest",
        description=(
            "USD open interest time series for a token's perpetual futures. "
            "Measures derivatives positioning size. Rising OI + rising price = strong trend. "
            "Rising OI + falling price = potential short squeeze. "
            "base_token: CoinGecko ID (e.g. 'bitcoin', 'skyai'). "
            "exchanges: comma-separated e.g. 'binance,okx,bybit,deribit'. "
            "instrument_type: 'perp' (default) | 'future' | 'option'. "
            "time_period: '1d' | '7d' | '1m' | '3m' | '6m' | '1y'."
        ),
    )
    async def get_open_interest(
        base_token: str,
        ctx: Context,
        exchanges: Optional[str] = None,
        instrument_type: str = "perp",
        time_period: str = "30d",
    ) -> dict:
        return await ctx.lifespan_context["client"].get_open_interest(
            base_token,
            exchanges=exchanges,
            instrument_type=instrument_type,
            time_period=time_period,
        )

    @mcp.tool(
        name="get_volume_timeseries",
        description=(
            "USD trading volume time series across exchanges for a token. "
            "Useful for detecting volume spikes and exchange distribution. "
            "base_token: CoinGecko ID (e.g. 'bitcoin', 'skyai'). "
            "exchanges: comma-separated e.g. 'binance,bybit,okx,deribit'. "
            "instrument_type: 'perp' | 'future' | 'spot'. "
            "time_period: '1h' | '24h' | '7d' | '1m' | '3m'."
        ),
    )
    async def get_volume_timeseries(
        base_token: str,
        ctx: Context,
        exchanges: Optional[str] = None,
        instrument_type: str = "perp",
        time_period: str = "24h",
    ) -> dict:
        return await ctx.lifespan_context["client"].get_volume_timeseries(
            base_token,
            exchanges=exchanges,
            instrument_type=instrument_type,
            time_period=time_period,
        )
