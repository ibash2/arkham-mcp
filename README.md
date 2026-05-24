# arkham-mcp

Ask your AI anything about crypto wallets and on-chain activity — powered by [Arkham Intelligence](https://intel.arkm.com).

Works with Claude, Cursor, VS Code, and any AI tool that supports MCP.

## Install

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/ibash2/arkham-mcp/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/ibash2/arkham-mcp/main/install.ps1 | iex
```

The installer picks your AI client and sets everything up.

## Access

**Browser session (recommended)** — runs via a headless browser that handles auth automatically, same as visiting the site as a guest. No API key needed, no rate limits. The installer guides you through it.

**API key** — available in [intel.arkm.com](https://intel.arkm.com) → Settings → API. More restricted than the browser session, harder to obtain.

> User account features (custom entities, saved queries) are in progress.

## What it can look up

| | |
|---|---|
| **Wallet identity** | Owner, labels, entity type, known affiliations |
| **Transaction history** | Transfers, DEX trades, DeFi loans |
| **Fund tracing** | Hop-by-hop forward/backward tracing |
| **Forensics** | Coordinated wallets, wash trading, pump & dump signals |
| **Entity data** | Exchange balances, fund portfolios, historical holdings |
| **Market data** | Token prices, volumes, funding rates, gas fees |

## Troubleshooting

**`403 Forbidden`** — restart the installer and choose Browser session.

**Nothing happens after install** — restart your AI client.

## For developers

See [CONTRIBUTING.md](CONTRIBUTING.md) and [ARCHITECTURE.md](ARCHITECTURE.md).

## License

MIT
