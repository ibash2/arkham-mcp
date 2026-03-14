"""
Arkham Intel MCP Server — entry point.
"""

from contextlib import asynccontextmanager

from fastmcp import FastMCP

from .config import get_settings
from .providers import get_provider
from .tools import atomic, profiles, activity, investigation, forensics
from .resources import address as address_resource
from .resources import entity as entity_resource
from .resources import network as network_resource
from .prompts import investigation as investigation_prompts


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
        "Start investigations with resolve_address() or search(). "
        "For forensic tracing use trace_fund_flow(). "
        "Structured workflows are available as prompts: "
        "investigate_address, trace_funds, entity_due_diligence, market_briefing. "
        "Forensic analysis tools: "
        "analyze_transfers_pattern (bot/wash/layered pattern detection), "
        "find_coordinated_wallets (cluster & timing-based coordination), "
        "trace_fund_source (backward hop tracing, CEX/mixer/fresh-wallet classification), "
        "scan_token_manipulation (pump & dump, wash trading, spoofing score 0-100), "
        "aggregate_wallet_activity (auto-paginated leaderboard: top buyers/sellers ranked by tx_count or volume)."
    ),
    lifespan=lifespan,
)

# --- register tools ---
atomic.register(mcp)
profiles.register(mcp)
activity.register(mcp)
investigation.register(mcp)
forensics.register(mcp)

# --- register resources ---
address_resource.register(mcp)
entity_resource.register(mcp)
network_resource.register(mcp)

# --- register prompts ---
investigation_prompts.register(mcp)


if __name__ == "__main__":
    mcp.run()
