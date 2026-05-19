# arkham-mcp

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

MCP server for [Arkham Intelligence](https://intel.arkm.com) — a blockchain analytics platform. Connects Arkham's capabilities to AI agents (Claude Desktop, Qwen Code, OpenCode, and any MCP-compatible client).

Once connected, the agent can:

- identify wallet owners and their on-chain connections
- trace where funds were sent (hop by hop)
- find wallets controlled by the same actor
- detect wash trading, bots, layering, and dust attacks
- pull full profiles for exchanges and funds with balances
- monitor markets: prices, volumes, funding rates

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Getting Credentials](#getting-credentials)
- [Connecting to AI Clients](#connecting-to-ai-clients)
- [Playwright Mode](#playwright-mode)
- [Verify It Works](#verify-it-works)
- [Example Prompts](#example-prompts)
- [Providers](#providers)
- [Tools Reference](#tools-reference)
- [Prompts](#prompts)
- [Resources](#resources)
- [Development](#development)
- [Troubleshooting](#troubleshooting)

---

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) — package manager
- Arkham API key **or** browser session cookie (details below)

---

## Installation

```bash
# Linux / macOS
curl -fsSL https://raw.githubusercontent.com/ibash2/arkham-mcp/main/install.sh | bash

# Windows (PowerShell)
irm https://raw.githubusercontent.com/ibash2/arkham-mcp/main/install.ps1 | iex
```

The installer will:
1. Install `uv` automatically if not present
2. Clone the repo to `~/.local/share/arkham-mcp` (Linux/macOS) or `%LOCALAPPDATA%\arkham-mcp` (Windows)
3. Ask which AI clients to configure (Claude Code, Claude Desktop, Cursor, VS Code)
4. Ask for your API key or cookie
5. Write the MCP config for each selected client

### Manual installation

```bash
git clone https://github.com/ibash2/arkham-mcp
cd arkham-mcp
uv sync
```

---

## Getting Credentials

You need at least one of the two options below.

### Option A — API Key (recommended)

1. Go to [intel.arkm.com](https://intel.arkm.com)
2. Settings → API → Create API Key
3. Copy the key

### Option B — Browser Cookie

Use this if the API key doesn't work (Cloudflare 403). The server will run through a headless Chromium browser using your session.

1. Log in to [intel.arkm.com](https://intel.arkm.com) in your browser
2. DevTools → Application → Cookies → `intel.arkm.com`
3. Copy the value of the `AMP_f072531383` cookie (or the entire `Cookie:` header from any request in the Network tab)

---

## Connecting to AI Clients

### Step 1 — Export your API key

Add this line to your shell profile (`~/.zshrc`, `~/.bashrc`, etc.) so all clients pick it up automatically:

```bash
export ARKHAM_API_KEY=your_key_here
```

Then reload:

```bash
source ~/.zshrc   # or ~/.bashrc
```

### Claude Code

The project includes `.mcp.json` — Claude Code reads it automatically when you open the project folder.

No extra steps needed. Just open the folder and the `arkham` server appears in your MCP list.

---

### Claude Desktop

Open: **Settings → Developer → Edit Config** and add:

```json
{
  "mcpServers": {
    "arkham": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/arkham-mcp", "run", "arkham-mcp"],
      "env": {
        "ARKHAM_API_KEY": "your_key_here",
        "ARKHAM_BASE_URL": "https://api.arkm.com",
        "ARKHAM_PROVIDER": "arkham"
      }
    }
  }
}
```

Replace `/absolute/path/to/arkham-mcp` with the actual path on your machine. Restart Claude Desktop.

---

### Cursor

The project includes `.cursor/mcp.json` — Cursor reads it automatically when you open the project folder.

If `ARKHAM_API_KEY` is set in your shell profile, no further configuration is needed.

---

### VS Code (GitHub Copilot)

The project includes `.vscode/mcp.json`. VS Code will prompt you to enter your API key the first time — it is stored securely and not committed to the repo.

---

### OpenCode

Use `opencode.json` from the repository root — it is already configured for stdio transport.

---

## Playwright Mode

Use this mode when the `arkham` provider returns `403 Forbidden` from Cloudflare. The server launches a **headless** Chromium browser (no window opens) and uses your logged-in session instead of an API key.

Cloudflare challenges are handled fully automatically — the server detects the challenge page, clicks the Turnstile checkbox by itself, and proceeds without any user interaction.

### Step 1 — Get your browser cookie

1. Log in to [intel.arkm.com](https://intel.arkm.com) in Chrome or Firefox
2. Open DevTools → **Network** tab → refresh the page
3. Click any request to `intel.arkm.com` → **Headers** → copy the full `Cookie:` header value

### Step 2 — Install Chromium

```bash
uv run python -m playwright install chromium
```

### Step 3 — Configure your client

**Claude Code** — edit `.mcp.json` in the project root:

```json
{
  "mcpServers": {
    "arkham": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "arkham-mcp"],
      "env": {
        "ARKHAM_COOKIE": "${ARKHAM_COOKIE}",
        "ARKHAM_BASE_URL": "https://api.arkm.com",
        "ARKHAM_PROVIDER": "playwright"
      }
    }
  }
}
```

Then export the cookie in your shell profile:

```bash
export ARKHAM_COOKIE="AMP_f072531383=JTdC..."
```

**Claude Desktop** — in `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arkham": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/arkham-mcp", "run", "arkham-mcp"],
      "env": {
        "ARKHAM_COOKIE": "AMP_f072531383=JTdC...",
        "ARKHAM_BASE_URL": "https://api.arkm.com",
        "ARKHAM_PROVIDER": "playwright"
      }
    }
  }
}
```

**Cursor** — edit `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "arkham": {
      "command": "uv",
      "args": ["run", "arkham-mcp"],
      "env": {
        "ARKHAM_COOKIE": "${ARKHAM_COOKIE}",
        "ARKHAM_BASE_URL": "https://api.arkm.com",
        "ARKHAM_PROVIDER": "playwright"
      }
    }
  }
}
```

> **Cookie expiry** — Arkham session cookies expire periodically. If you start getting auth errors, repeat Step 1 and update the cookie value.

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
Analyze the transaction pattern for 0xabc123... over 30 days.
Is this a bot? Wash trading?
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

The operating mode is set via the `ARKHAM_PROVIDER` variable.

| Provider | How it works | When to use |
|---|---|---|
| `arkham` (default) | Direct HTTP requests to the API | You have an API key, no Cloudflare issues |
| `playwright` | Headless Chromium + cookie | API key fails, Cloudflare blocks with 403 |

---

## Tools Reference

### Identity

| Tool | Description |
|---|---|
| `search` | Full-text search: finds entities, addresses, tokens |
| `resolve_address` | Identifies address owner, labels, ML predictions, balances |
| `get_entity_profile` | Full entity dossier: metadata, stats, tokens, predicted addresses |
| `compare_addresses` | Side-by-side comparison for up to 1000 addresses |
| `get_cluster_summary` | Summary for a wallet cluster by cluster ID |

### Activity & Transfers

| Tool | Description |
|---|---|
| `get_address_activity` | Inflow/outflow totals + top counterparties for a time window |
| `get_transfers` | Filtered on-chain transfers with entity labels |
| `get_transfers_by_tx` | All transfers within a specific transaction hash |
| `get_transfers_histogram` | Transfer count/volume bucketed by time |
| `get_swaps` | DEX trades by address or entity |
| `get_address_history` | Historical USD balance snapshots for an address |
| `get_address_loans` | Active DeFi loan positions (Aave, Compound, etc.) |

### Portfolio

| Tool | Description |
|---|---|
| `get_portfolio_change` | Portfolio diff between two Unix timestamps |
| `get_portfolio_timeseries` | Daily token-level holdings over time |

### Fund Tracing

| Tool | Description |
|---|---|
| `trace_fund_flow` | Outgoing flows (1 hop) with risk flags: mixers, unknown wallets, CEX |
| `trace_fund_source` | Backward tracing: where did funds come from (CEX / mixer / fresh wallet) |

### Forensics

| Tool | Description |
|---|---|
| `analyze_transfers_pattern` | Classifies pattern: `bot_market_maker` / `wash_trading` / `layered_disbursement` / `dust_attack` / `normal_trading` |
| `find_coordinated_wallets` | Finds wallets operated by the same actor via cluster, counterparties, timing |
| `aggregate_wallet_activity` | Buyer/seller leaderboard ranked by tx count or volume |

### Entity Data

| Tool | Description |
|---|---|
| `get_entity_counterparties` | Top counterparties for a known entity |
| `get_entity_flow` | Historical USD inflow/outflow for an entity |
| `get_entity_history` | Historical USD balance snapshots for an entity |
| `get_entity_balance_changes` | Leaderboard of entities with the largest balance changes |
| `get_entity_loans` | Active DeFi loan positions for an entity |

### Market Data

| Tool | Description |
|---|---|
| `get_networks_status` | Prices, 24h volumes, gas fees across all networks |
| `get_network_history` | Historical price/volume for a specific network |
| `get_chains` | List of all supported blockchains |
| `get_entity_types` | List of all entity classification types |
| `get_token` | Token metadata and price by network + contract address |
| `get_token_by_coingecko_id` | Token data by CoinGecko ID |
| `get_contract` | Contract metadata: deployer, deploy tx, linked token |
| `get_funding_rates` | Perpetual futures funding rates by token and exchange |
| `get_altcoin_index` | Arkham altcoin performance index |
| `get_arkm_supply` | Current ARKM token circulating supply |

---

## Prompts

Ready-made multi-step workflows. The agent calls the relevant tools in sequence and produces a structured report.

| Prompt | Description |
|---|---|
| `investigate_address` | Full investigation: identity → activity → tracing → report |
| `trace_funds` | Follow the money — transfer chain with visual output |
| `entity_due_diligence` | Due diligence on an entity: assets, activity, risk signals |
| `market_briefing` | Market overview: prices, volumes, gas, altcoin index |

Example in Claude Desktop:

```
Run the investigate_address prompt for 0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE
```

---

## Resources

MCP resources are cacheable data snapshots the client can read directly without calling a tool.

| URI | Returns |
|---|---|
| `arkham://address/{address}` | Entity, labels, predictions, top holdings |
| `arkham://entity/{slug}` | Entity profile: metadata, stats, tokens |
| `arkham://network/{chain}` | 7-day price and volume history |
| `arkham://network/status` | Current prices, volumes, gas for all networks |

---

## Development

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# With coverage
uv run pytest --cov=src/arkham_mcp --cov-report=term-missing

# Integration tests (real API — credentials required)
uv run pytest tests/integrations -m integration
```

### Project Structure

```
src/arkham_mcp/
├── server.py              # Entry point: FastMCP app, tool/resource/prompt registration
├── config.py              # Settings via ARKHAM_* environment variables
├── client.py              # High-level API client
├── cache.py               # Response caching
├── providers/
│   ├── base.py            # DataProvider Protocol (interface)
│   ├── arkham.py          # Direct HTTP provider
│   └── playwright.py      # Headless Chromium provider
├── tools/                 # All MCP tools
├── resources/             # MCP resources (arkham://)
└── prompts/               # Structured investigation workflows
```

### Adding a New Provider

1. Create `src/arkham_mcp/providers/myprovider.py` implementing all methods of the `DataProvider` Protocol
2. Register it in `src/arkham_mcp/providers/__init__.py`
3. Set `ARKHAM_PROVIDER=myprovider` in `.env`

---

## Troubleshooting

**`Authentication required: set ARKHAM_API_KEY or ARKHAM_COOKIE`**
→ `.env` is not filled in. Make sure at least one variable is set.

**`403 Forbidden` from Cloudflare**
→ Switch to the playwright provider:
```bash
ARKHAM_PROVIDER=playwright
ARKHAM_COOKIE=your_cookie
uv run python -m playwright install chromium
```

**Playwright doesn't bypass Cloudflare**
→ Your cookie has expired. Log in to intel.arkm.com again and copy a fresh one.

**`ModuleNotFoundError`**
→ Run `uv sync`.

**Rate limit errors**
→ The `get_transfers` tool is limited to 1 request/sec on the Arkham API side. This is expected.

---

## License

MIT
