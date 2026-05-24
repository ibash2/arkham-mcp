"""
Arkham Intel MCP Server — entry point.
"""

from contextlib import asynccontextmanager

from fastmcp import FastMCP

from .config import get_settings
from .providers import get_provider
from .tools import atomic, profiles, activity, portfolio, entity, transfers, market, token, forensics


@asynccontextmanager
async def lifespan(app: FastMCP):
    async with get_provider(get_settings()) as provider:
        yield {"client": provider}


mcp = FastMCP(
    name="Arkham Intel",
    instructions=(
        "You have access to Arkham Intelligence — a blockchain analytics platform. "
        "Use it to identify wallet owners, trace fund flows, analyze entity holdings, "
        "and monitor on-chain activity. "
        "ALWAYS call investigate_address(address) first when asked to investigate or analyze a wallet. "
        "ALWAYS call investigate_token(token) first when asked to investigate or analyze a token. "
        "For forensic tracing use trace_fund_flow(). "
        "Structured workflows: investigate_address (wallet), investigate_token (token). "
        "Forensic analysis tools: "
        "find_coordinated_wallets (cluster & timing-based coordination), "
        "trace_fund_source (backward hop tracing, CEX/mixer/fresh-wallet classification), "
        "aggregate_wallet_activity (auto-paginated leaderboard: top buyers/sellers ranked by tx_count or volume), "
        "scan_token_manipulation (pump & dump, wash trading, coordinated accumulation signals)."
    ),
    lifespan=lifespan,
)

# --- register tools ---
atomic.register(mcp)
profiles.register(mcp)
activity.register(mcp)
portfolio.register(mcp)
entity.register(mcp)
transfers.register(mcp)
market.register(mcp)
token.register(mcp)
forensics.register(mcp)

if __name__ == "__main__":
    mcp.run()
