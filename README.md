# arkham-mcp

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MCP server for [Arkham Intelligence](https://intel.arkm.com) — a blockchain analytics platform. Connects Arkham's capabilities to AI agents (Claude Code, Claude Desktop, Cursor, VS Code, and any MCP-compatible client).

Once connected, the agent can:

- identify wallet owners and their on-chain connections
- trace where funds were sent (hop by hop)
- find wallets controlled by the same actor
- detect wash trading, bots, layering, and dust attacks
- pull full profiles for exchanges and funds with balances
- monitor markets: prices, volumes, funding rates

---

## Installation

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/ibash2/arkham-mcp/main/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/ibash2/arkham-mcp/main/install.ps1 | iex
```

The installer will automatically install `uv` if needed, clone the repo, ask which clients to configure (Claude Code, Claude Desktop, Cursor, VS Code), and prompt for your API key or cookie.

### Manual installation

```bash
git clone https://github.com/ibash2/arkham-mcp
cd arkham-mcp
uv sync
```

---

## Getting Credentials

### Option A — API Key (recommended)

1. Go to [intel.arkm.com](https://intel.arkm.com)
2. Settings → API → Create API Key
3. Copy the key

### Option B — Browser Cookie

Use this if the API key returns 403 (Cloudflare). The server will run through a headless Chromium browser using your session.

1. Log in to [intel.arkm.com](https://intel.arkm.com)
2. DevTools → Network → click any request → Headers → copy the full `Cookie:` header value

---

## Verify It Works

After connecting, ask the agent:

```
Who owns 0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE?
```

If the agent returns an entity name, labels, and balance — everything is working.

---

## Example Prompts

```
Who owns 0xabc123...? Is it an exchange or a private wallet?
```

```
Trace where funds from 0xabc123... went over the last 7 days
```

```
Do these 5 addresses belong to the same person?
0xAAA..., 0xBBB..., 0xCCC..., 0xDDD..., 0xEEE...
```

```
Do a full investigation of 0xabc123...
Who is it, where did the money come from, where was it sent, any mixer connections?
```

```
Analyze the transaction pattern for 0xabc123... over 30 days. Is this a bot? Wash trading?
```

```
How much Bitcoin does Binance hold right now?
```

```
Which entities had the largest balance increases in the last 24 hours?
```

```
Show current BTC funding rates on Binance and OKX
```

---

## Providers

| Provider | How it works | When to use |
|---|---|---|
| `arkham` (default) | Direct HTTP requests to the API | You have an API key |
| `playwright` | Headless Chromium + cookie | API key fails with 403 |

---

## Tools Reference

### Identity

| Tool | Description |
|---|---|
| `search` | Full-text search: entities, addresses, tokens |
| `resolve_address` | Owner, labels, ML predictions, balances |
| `get_entity_profile` | Full entity dossier: metadata, stats, tokens |

### Activity & Transfers

| Tool | Description |
|---|---|
| `get_address_activity` | Inflow/outflow totals + top counterparties |
| `get_transfers` | Filtered on-chain transfers with entity labels |
| `get_transfers_by_tx` | All transfers within a transaction hash |
| `get_transfers_histogram` | Transfer count/volume bucketed by time |
| `get_swaps` | DEX trades by address or entity |
| `get_address_history` | Historical USD balance snapshots |
| `get_address_loans` | Active DeFi loan positions |

### Portfolio

| Tool | Description |
|---|---|
| `get_portfolio_change` | Portfolio diff between two timestamps |
| `get_portfolio_timeseries` | Daily token-level holdings over time |

### Fund Tracing

| Tool | Description |
|---|---|
| `trace_fund_flow` | Outgoing flows (1 hop) with risk flags |
| `trace_fund_source` | Backward tracing: CEX / mixer / fresh wallet |

### Forensics

| Tool | Description |
|---|---|
| `find_coordinated_wallets` | Wallets operated by the same actor |
| `aggregate_wallet_activity` | Buyer/seller leaderboard by tx count or volume |
| `scan_token_manipulation` | Pump & dump, wash trading, coordinated accumulation |

### Entity Data

| Tool | Description |
|---|---|
| `get_entity_counterparties` | Top counterparties for a known entity |
| `get_entity_flow` | Historical USD inflow/outflow |
| `get_entity_history` | Historical USD balance snapshots |
| `get_entity_balance_changes` | Entities with largest balance changes |
| `get_entity_loans` | Active DeFi loan positions for an entity |

### Market Data

| Tool | Description |
|---|---|
| `get_networks_status` | Prices, 24h volumes, gas fees across all networks |
| `get_network_history` | Historical price/volume for a network |
| `get_token` | Token metadata and price |
| `get_token_by_coingecko_id` | Token data by CoinGecko ID |
| `get_funding_rates` | Perpetual futures funding rates |
| `get_altcoin_index` | Arkham altcoin performance index |
| `get_arkm_supply` | Current ARKM token circulating supply |

---

## Prompts

Ready-made multi-step workflows.

| Prompt | Description |
|---|---|
| `investigate_address` | Full investigation: identity → activity → tracing → report |
| `investigate_token` | Token holders, flows, manipulation signals |

---

## Resources

| URI | Returns |
|---|---|
| `arkham://address/{address}` | Entity, labels, predictions, top holdings |
| `arkham://entity/{slug}` | Entity profile: metadata, stats, tokens |
| `arkham://network/{chain}` | 7-day price and volume history |
| `arkham://network/status` | Current prices, volumes, gas for all networks |

---

## Development

```bash
uv sync --dev
uv run pytest
uv run pytest --cov=src/arkham_mcp --cov-report=term-missing
uv run pytest tests/integrations -m integration  # requires credentials
```

---

## Troubleshooting

**`Authentication required`** → Set `ARKHAM_API_KEY` or `ARKHAM_COOKIE` in your environment.

**`403 Forbidden` from Cloudflare** → Use browser cookie mode: run the installer and choose "Browser cookie".

**Cookie expired** → Log in to intel.arkm.com again and copy a fresh `Cookie:` header.

**`ModuleNotFoundError`** → Run `uv sync`.

**Rate limit errors** → `get_transfers` is limited to 1 req/sec on the Arkham side. Expected.

---

## License

MIT
