"""
Atomic tools — thin wrappers for direct API lookups.
"""

from fastmcp import FastMCP
from fastmcp.server.context import Context


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
        description="Get token data using a CoinGecko pricing ID (e.g. 'ethereum', 'usd-coin', 'skyai').",
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
        name="get_cluster_summary",
        description=(
            "Get summary statistics for a blockchain address cluster by cluster ID. "
            "Cluster IDs are returned in enriched address lookups (clusterId field)."
        ),
    )
    async def get_cluster_summary(cluster_id: str, ctx: Context) -> dict:
        return await ctx.lifespan_context["client"].get_cluster_summary(cluster_id)
