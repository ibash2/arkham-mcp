# arkham-mcp

**Ask your AI assistant anything about crypto wallets, transactions, and on-chain activity — powered by [Arkham Intelligence](https://intel.arkm.com).**

Works with Claude, Cursor, VS Code, and any AI tool that supports MCP.

---

## What you can do

Ask your AI in plain language — no code, no SQL, no manual lookups:

> *"Who owns this wallet? Is it a known exchange or a private holder?"*

> *"Trace where the money from this address went over the last week"*

> *"Do these 5 wallets belong to the same person?"*

> *"Is there wash trading happening on this token?"*

> *"How much BTC does Binance hold right now?"*

> *"Do a full investigation of this address — who is it, where did the money come from, any mixer connections?"*

---

## Install in one command

**macOS / Linux:**
```bash
curl -fsSL https://raw.githubusercontent.com/ibash2/arkham-mcp/main/install.sh | bash
```

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/ibash2/arkham-mcp/main/install.ps1 | iex
```

The installer asks which AI client to configure, then walks you through access setup. That's it.

---

## Access options

### Free — Browser session (recommended)

No API key needed. Works through your free Arkham account.

1. Create a free account at [intel.arkm.com](https://intel.arkm.com)
2. Open DevTools (F12) → Network tab → click any request → copy the `Cookie:` header value
3. During install, choose **Cookie** and paste it

This gives you full access to everything Arkham has.

### Free — Guest mode

No account needed at all. Works for most public on-chain data.

During install, just press Enter to skip authentication.

### API Key

For advanced users or automation. Get a key at [intel.arkm.com](https://intel.arkm.com) → Settings → API.

---

## What it can look up

| | |
|---|---|
| **Wallet identity** | Owner name, labels, entity type, known affiliations |
| **Transaction history** | Transfers, DEX trades, DeFi loans |
| **Fund tracing** | Follow money hop by hop, backward to source |
| **Forensics** | Coordinated wallets, wash trading, bot detection, pump & dump signals |
| **Entity data** | Exchange balances, fund portfolios, historical holdings |
| **Market data** | Token prices, volumes, funding rates, network gas fees |

---

## Troubleshooting

**Cookie expired** → Log into intel.arkm.com again and copy a fresh `Cookie:` header.

**`403 Forbidden`** → Switch to Cookie mode — this bypasses Cloudflare restrictions.

**Nothing happens after install** → Restart your AI client (Claude, Cursor, etc.).

---

## License

MIT
