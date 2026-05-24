# Contributing

## Setup

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/ibash2/arkham-mcp
cd arkham-mcp
uv sync --dev
```

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```env
ARKHAM_PROVIDER=arkham       # or: playwright
ARKHAM_API_KEY=your_key      # for arkham provider
ARKHAM_COOKIE=your_cookie    # for playwright provider
```

## Running the server locally

```bash
uv run arkham-mcp
```

Or connect it to Claude Code by pointing `~/.claude.json` to your local path:

```json
{
  "mcpServers": {
    "arkham": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "/path/to/arkham-mcp", "run", "arkham-mcp"]
    }
  }
}
```

## Tests

```bash
# Unit tests (no credentials needed)
uv run pytest

# With coverage
uv run pytest --cov=src/arkham_mcp --cov-report=term-missing

# Integration tests (hit real Arkham API — requires credentials in .env)
uv run pytest tests/integrations -m integration
```

Unit tests use mocked providers and run offline. Integration tests are marked with `@pytest.mark.integration` and are excluded from the default run.

## Project structure

```
src/
  server.py          # FastMCP entry point, tool registration
  config.py          # Settings from ARKHAM_* env vars
  client.py          # ArkhamClient (aiohttp, auth, rate limiting)
  cache.py           # Simple in-memory response cache
  providers/
    base.py          # DataProvider protocol — the interface all providers implement
    arkham.py        # Direct HTTP provider
    playwright.py    # Headless browser provider
  tools/
    activity.py      # Address flow and counterparties
    atomic.py        # investigate_address / investigate_token workflows
    entity.py        # Entity-level data
    forensics.py     # Wallet clustering, manipulation detection
    market.py        # Prices, volumes, funding rates
    portfolio.py     # Holdings and portfolio timeseries
    profiles.py      # Address and entity identity
    token.py         # Token metadata and holders
    transfers.py     # On-chain transfers
installer/
  install.py         # Interactive installer UI
  config_paths.py    # Config file locations per client/OS
  config_writer.py   # Atomic JSON config writer
  mcp_entry.py       # Builds the mcpServers entry
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for a deeper explanation of how the pieces fit together.

## Adding a new tool

1. Find or create the right module in `src/tools/`
2. Add your function inside the `register(mcp)` function:
   ```python
   @mcp.tool(name="my_tool", description="What it does and when to use it.")
   async def my_tool(address: str, ctx: Context) -> dict:
       client = ctx.lifespan_context["client"]
       return await client.some_method(address)
   ```
3. Make sure the method you call exists on `DataProvider` in `base.py`. If not, add it there and implement it in both `arkham.py` and `playwright.py`.
4. Write a test in `tests/tools/`.

## Adding a new provider

See [ARCHITECTURE.md — Adding a new provider](ARCHITECTURE.md#adding-a-new-provider).

## Pull requests

- Keep PRs focused — one feature or fix per PR
- All unit tests must pass: `uv run pytest`
- New tools need a unit test with a mocked provider
- New provider methods need implementation in both `arkham.py` and `playwright.py`
