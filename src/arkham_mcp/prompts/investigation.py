"""
Investigation prompts — reusable multi-step analysis workflows.
"""

from fastmcp import FastMCP
from fastmcp.prompts import Message


def register(mcp: FastMCP) -> None:

    @mcp.prompt(
        name="investigate_address",
        description=(
            "Structured workflow for investigating an unknown blockchain address. "
            "Guides the agent through identity resolution, activity analysis, and risk assessment."
        ),
    )
    def investigate_address(address: str, depth: str = "full") -> list[Message]:
        steps = """
**Step 1 — Resolve identity**
Call `resolve_address("{address}")`.
- If `is_identified=true`: note the entity name, type, and labels.
- If `is_identified=false`: mark as UNKNOWN and proceed with caution.

**Step 2 — Analyze activity**
Call `get_address_activity("{address}", time_last="30d")`.
- Summarize: total inflow, total outflow, net flow.
- List top counterparties. Flag any that are unidentified or tagged as mixers/exchanges.

**Step 3 — Trace outgoing funds** *(depth=full only)*
Call `trace_fund_flow("{address}", time_last="7d")`.
- List all destinations: entity name, type, volume.
- Highlight any `suspicious_flags` (mixers, unidentified high-volume, sanctioned).
- Group by: exchange destinations vs. unknown destinations.

**Step 4 — Portfolio snapshot**
Review `top_holdings` from Step 1.
- What tokens does this address hold?
- Is the composition consistent with the known entity type?

**Step 5 — Write report**
Produce a structured report:

```
## Address Investigation: {address}

### Identity
- Entity: ...
- Type: ...
- Labels: ...
- Chains: ...

### Financial Summary (30d)
- Total Inflow: $...
- Total Outflow: $...
- Net Flow: $...
- Top Holdings: ...

### Key Counterparties
| Address | Entity | Volume USD | Direction |
|---------|--------|------------|-----------|
...

### Risk Assessment
- Flags: ...
- Mixer interactions: yes/no
- Exchange deposits: ...
- Unidentified destinations: N addresses ($X total)

### Conclusion
...
```
""".format(address=address)

        if depth == "quick":
            steps = """
**Quick investigation of {address}**

1. Call `resolve_address("{address}")` — identify the owner.
2. Call `get_address_activity("{address}", time_last="7d")` — recent activity.
3. Write a 3-sentence summary: who, what, any red flags.
""".format(address=address)

        return [
            Message(
                role="user",
                content=f"Investigate the following blockchain address: `{address}`\n\n{steps}",
            )
        ]

    @mcp.prompt(
        name="trace_funds",
        description=(
            "Follow the money from an origin address through its counterparties. "
            "Useful for forensic analysis, hack tracing, and sanction compliance."
        ),
    )
    def trace_funds(origin_address: str, time_window: str = "7d") -> list[Message]:
        return [
            Message(
                role="user",
                content=f"""Trace the fund flow from address `{origin_address}` over the last {time_window}.

Follow these steps:

**Step 1 — Identify the origin**
Call `resolve_address("{origin_address}")`.
Note the entity, labels, and current holdings.

**Step 2 — Map outgoing flows**
Call `trace_fund_flow("{origin_address}", time_last="{time_window}")`.
For each destination in `flows`:
- Record: address, entity, volume_usd, is_exchange, is_mixer, risk_flags.

**Step 3 — Investigate unknown destinations**
For any destination where `to_entity=null` and `volume_usd` is significant:
- Call `resolve_address(to_address)` to attempt identification.
- Call `get_address_activity(to_address, time_last="{time_window}")` to see where funds went next.

**Step 4 — Build the chain**
Present the fund flow as a chain:
```
{origin_address} (EntityA)
  ├─ → 0xAAA... (Binance deposit)   $X
  ├─ → 0xBBB... (UNKNOWN)           $Y
  │     └─ → 0xCCC... (Tornado Cash)
  └─ → 0xDDD... (Jump Trading)      $Z
```

**Step 5 — Risk summary**
- Final destinations (exchanges, mixers, unknown wallets).
- Total traceable vs. untraceable volume.
- Any OFAC/sanctioned addresses in the chain.
""",
            )
        ]

    @mcp.prompt(
        name="entity_due_diligence",
        description=(
            "Structured due diligence report for a known entity. "
            "Covers holdings, activity patterns, associated addresses, and risk signals."
        ),
    )
    def entity_due_diligence(entity_name: str) -> list[Message]:
        return [
            Message(
                role="user",
                content=f"""Perform due diligence on the entity: **{entity_name}**

**Step 1 — Confirm identity**
Call `search("{entity_name}")` to find the exact entity slug.
Then call `get_entity_profile(entity_slug)`.

**Step 2 — Holdings analysis**
From the profile:
- What is the total USD value held?
- What are the top 5 tokens by value?
- Which chains are most active?

**Step 3 — Activity patterns**
For the top 3 addresses (by balance from `top_holdings`):
- Call `get_address_activity(address, time_last="30d")`.
- Summarize inflow/outflow and main counterparties.

**Step 4 — Predicted addresses**
Review `predicted_addresses` from the entity profile.
- How many addresses are predicted vs. confirmed?
- What is the confidence distribution?

**Step 5 — Write due diligence report**

```
## Entity Due Diligence: {entity_name}

### Overview
- Type: ...
- Website: ...
- Known addresses: N
- Total holdings: $...

### Asset Breakdown
| Token | Chain | USD Value |
|-------|-------|-----------|
...

### Activity (30d)
- Net flow: $...
- Primary counterparties: ...

### Risk Signals
- ...

### Conclusion
Overall risk level: LOW / MEDIUM / HIGH
Reasoning: ...
```
""",
            )
        ]

    @mcp.prompt(
        name="market_briefing",
        description=(
            "Generate a current market briefing across all supported networks. "
            "Covers prices, volumes, gas fees, and altcoin performance."
        ),
    )
    def market_briefing() -> list[Message]:
        return [
            Message(
                role="user",
                content="""Generate a current crypto market briefing using Arkham data.

**Step 1** — Call `get_networks_status()` for current prices, volumes, and gas.
**Step 2** — Call `get_altcoin_index()` for altcoin performance.
**Step 3** — For the top 3 chains by volume, call `get_network_history(chain, time_last="7d")`.

Present the briefing in this format:

```
## Crypto Market Briefing — [current date]

### Network Status
| Chain    | Price   | 24h Vol | Gas (gwei) |
|----------|---------|---------|------------|
...

### Altcoin Index
...

### 7-Day Trends
...

### Key Observations
- ...
```
""",
            )
        ]
