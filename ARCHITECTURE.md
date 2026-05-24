# Architecture

## Overview

```
AI client (Claude, Cursor, etc.)
        │  MCP (stdio)
        ▼
   server.py  ←── FastMCP entry point
        │
        ├── tools/          ←── MCP tools exposed to the AI
        │     ├── activity.py
        │     ├── atomic.py
        │     ├── entity.py
        │     ├── forensics.py
        │     ├── market.py
        │     ├── portfolio.py
        │     ├── profiles.py
        │     ├── token.py
        │     └── transfers.py
        │
        └── providers/      ←── data source abstraction
              ├── base.py         DataProvider protocol (interface)
              ├── arkham.py       direct HTTP → api.arkm.com
              └── playwright.py   headless Chromium + cookie
```

## Key components

### `server.py`

Entry point. Creates a `FastMCP` instance, registers all tool modules, and wires up the provider via a lifespan context. The active provider is injected into every tool call via `ctx.lifespan_context["client"]`.

### `config.py`

`Settings` reads configuration from environment variables with the `ARKHAM_` prefix:

| Variable | Default | Description |
|---|---|---|
| `ARKHAM_PROVIDER` | `playwright` | Which provider to use: `arkham` or `playwright` |
| `ARKHAM_API_KEY` | — | API key for the `arkham` provider |
| `ARKHAM_COOKIE` | — | Raw `Cookie:` header for the `playwright` provider |
| `ARKHAM_BASE_URL` | `https://api.arkm.com` | API base URL |

### `providers/`

Providers implement the `DataProvider` protocol defined in `base.py`. The protocol uses structural subtyping — no inheritance needed, just implement the methods.

`providers/__init__.py` holds the registry that maps provider names to factory functions:

```python
_REGISTRY = {
    "arkham": arkham.create_provider,
    "playwright": _playwright_provider,
}
```

Each factory is an async context manager that yields an object satisfying `DataProvider`.

**`arkham` provider** — makes direct HTTP requests via `aiohttp`. Works with an API key or no auth (guest mode). Rate-limited endpoints (`get_transfers`, `get_counterparties`, `get_swaps`) are throttled to 1 req/sec via an internal `RateLimiter`.

**`playwright` provider** — launches a headless Chromium browser via Patchright, injects the user's cookie, then proxies all requests through the browser session. This bypasses Cloudflare restrictions. Requires `patchright install chromium` on first use.

### `tools/`

Each module has a single `register(mcp: FastMCP)` function that decorates functions with `@mcp.tool(...)`. Tools receive the active provider from context:

```python
def register(mcp: FastMCP) -> None:
    @mcp.tool(name="...", description="...")
    async def my_tool(param: str, ctx: Context) -> dict:
        client = ctx.lifespan_context["client"]
        return await client.some_method(param)
```

## Data flow

```
Tool call from AI
  → tool function extracts params
  → calls provider method (e.g. client.get_transfers(...))
  → provider makes HTTP request (direct or via browser)
  → raw JSON response
  → tool formats/filters and returns to AI
```

## Adding a new provider

1. Create `src/arkham_mcp/providers/myname.py`
2. Implement all methods from `DataProvider` in `base.py`
3. Expose a factory:
   ```python
   from contextlib import asynccontextmanager

   @asynccontextmanager
   async def create_provider(settings):
       async with MyProvider(settings) as p:
           yield p
   ```
4. Register in `providers/__init__.py`:
   ```python
   from . import myname
   _REGISTRY["myname"] = myname.create_provider
   ```
5. Set `ARKHAM_PROVIDER=myname` in `.env`

## Adding a new tool

1. Add the function to the relevant module in `tools/` (or create a new one)
2. Decorate with `@mcp.tool(name=..., description=...)`
3. If creating a new module, add `your_module.register(mcp)` in `server.py`
4. The method you call must exist on `DataProvider` in `base.py` — add it there and implement it in both `arkham.py` and `playwright.py`
