"""
Async Python client for the Arkham Intelligence API.
Docs: https://intel.arkm.com/api/docs
"""

import asyncio
import time
from typing import Any, AsyncIterator, Optional

import hashlib
import aiohttp
from urllib.parse import urlparse

from .cache import ResponseCache, TTL_STATIC, TTL_ENTITY, TTL_ADDRESS, TTL_MARKET, TTL_FLOW

BASE_URL = "https://intel.arkm.com/api"


class RateLimiter:
    """Token-bucket rate limiter for endpoints with 1 req/sec limit."""

    def __init__(self, rate: float = 1.0):
        self.rate = rate
        self._last_call = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self):
        async with self._lock:
            now = time.monotonic()
            wait = (1.0 / self.rate) - (now - self._last_call)
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = time.monotonic()


class ArkhamAPIError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.message = message


class ArkhamClient:
    """
    Async client for the Arkham Intelligence API.

    Поддерживает два режима аутентификации (можно использовать оба одновременно):
      - API Key:  ArkhamClient(api_key="your_key")
      - Cookie:   ArkhamClient(cookie="AMP_f072531383=...")
      - Both:     ArkhamClient(api_key="key", cookie="AMP_...=...")

    Usage:
        async with ArkhamClient(api_key="your_key") as client:
            data = await client.get_address("0xabc...")

        async with ArkhamClient(cookie="AMP_f072531383=JTdC...") as client:
            data = await client.get_address("0xabc...")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        cookie: Optional[str] = None,
        base_url: str = BASE_URL,
    ):
        if not api_key and not cookie:
            raise ValueError("Either api_key or cookie must be provided.")
        self.api_key = api_key
        self.cookie = cookie
        self.base_url = base_url.rstrip("/")
        self._session: Optional[aiohttp.ClientSession] = None
        self._slow_limiter = RateLimiter(rate=1.0)  # counterparties & swaps
        self.cache = ResponseCache()
        self.CLIENT_KEY = "gh67j345kl6hj5k432"

    def generate_hash(self, url):
        pathname = urlparse(url).path
        intermediate_hash = hashlib.sha256(f"{pathname}:{str(int(time.time()))}:{self.CLIENT_KEY}".encode()).hexdigest()
        final_hash = hashlib.sha256(f"{self.CLIENT_KEY}:{intermediate_hash}".encode()).hexdigest()
        return final_hash

    def _build_auth_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        if self.api_key:
            headers["API-Key"] = self.api_key
        if self.cookie:
            headers["Cookie"] = self.cookie
        return headers

    async def __aenter__(self) -> "ArkhamClient":
        self._session = aiohttp.ClientSession(
            headers=self._build_auth_headers(),
            raise_for_status=False,
        )
        return self

    async def __aexit__(self, *_):
        if self._session:
            await self._session.close()
            self._session = None

    # ------------------------------------------------------------------ helpers

    def _url(self, path: str) -> str:
        return f"{self.base_url}/{path.lstrip('/')}"

    @staticmethod
    def _build_params(**kwargs) -> dict:
        return {k: v for k, v in kwargs.items() if v is not None}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict] = None,
        json: Optional[Any] = None,
        rate_limited: bool = False,
    ) -> Any:
        if self._session is None:
            raise RuntimeError("Client is not open. Use `async with ArkhamClient(...)`.")

        if rate_limited:
            await self._slow_limiter.acquire()

        url = self._url(path)

        headers = {"X-Payload": self.generate_hash(url), "X-Timestamp": str(int(time.time()))}

        async with self._session.request(method, url, params=params, json=json, headers=headers) as resp:
            body = await resp.json(content_type=None)
            if resp.status >= 400:
                msg = body.get("message") or body.get("error") or str(body)
                raise ArkhamAPIError(resp.status, msg)
            return body

    async def _get(self, path: str, params: Optional[dict] = None, **kw) -> Any:
        return await self._request("GET", path, params=params, **kw)

    async def _post(self, path: str, json: Any, params: Optional[dict] = None, **kw) -> Any:
        return await self._request("POST", path, params=params, json=json, **kw)

    async def _cached_get(
        self,
        path: str,
        ttl: float,
        params: Optional[dict] = None,
    ) -> Any:
        """GET with TTL cache. Cache key includes path + sorted params."""
        params_key = "&".join(f"{k}={v}" for k, v in sorted((params or {}).items()))
        cache_key = f"{path}?{params_key}"
        return await self.cache.get_or_fetch(cache_key, ttl, lambda: self._get(path, params))

    # ===================================================================
    # Intelligence — Address
    # ===================================================================

    async def get_address(self, address: str) -> dict:
        """Single address intelligence lookup."""
        return await self._cached_get(f"/intelligence/address/{address}", TTL_ADDRESS)

    async def get_address_all_chains(self, address: str) -> dict:
        """Multi-chain address intelligence."""
        return await self._cached_get(f"/intelligence/address/{address}/all", TTL_ADDRESS)

    async def get_address_enriched_all_chains(self, address: str) -> dict:
        """Multi-chain enriched address intelligence across all supported networks."""
        return await self._cached_get(f"/intelligence/address_enriched/{address}/all", TTL_ADDRESS)

    async def get_address_enriched(
        self,
        address: str,
        *,
        include_tags: Optional[bool] = None,
        include_clusters: Optional[bool] = None,
        include_entity_predictions: Optional[bool] = None,
    ) -> dict:
        """Address intelligence with tags, clusters, and ML predictions."""
        params = self._build_params(
            includeTags=include_tags,
            includeClusters=include_clusters,
            includeEntityPredictions=include_entity_predictions,
        )
        return await self._cached_get(f"/intelligence/address_enriched/{address}", TTL_ADDRESS, params or None)

    async def batch_addresses(self, addresses: list[str]) -> list[dict]:
        """Batch address intelligence — up to 1000 addresses."""
        if len(addresses) > 1000:
            raise ValueError("Batch size cannot exceed 1000 addresses.")
        return await self._post("/intelligence/address/batch", json={"addresses": addresses})

    async def batch_addresses_all_chains(self, addresses: list[str]) -> list[dict]:
        """Batch multi-chain address intelligence — up to 1000 addresses."""
        if len(addresses) > 1000:
            raise ValueError("Batch size cannot exceed 1000 addresses.")
        return await self._post("/intelligence/address/batch/all", json={"addresses": addresses})

    async def batch_addresses_enriched(self, addresses: list[str]) -> list[dict]:
        """Batch enriched address intelligence — up to 1000 addresses."""
        if len(addresses) > 1000:
            raise ValueError("Batch size cannot exceed 1000 addresses.")
        return await self._post("/intelligence/address_enriched/batch", json={"addresses": addresses})

    async def batch_addresses_enriched_all_chains(self, addresses: list[str]) -> list[dict]:
        """Batch enriched multi-chain address intelligence — up to 1000 addresses."""
        if len(addresses) > 1000:
            raise ValueError("Batch size cannot exceed 1000 addresses.")
        return await self._post("/intelligence/address_enriched/batch/all", json={"addresses": addresses})

    # ===================================================================
    # Intelligence — Entity
    # ===================================================================

    async def get_entity(self, entity: str) -> dict:
        """Entity overview data."""
        return await self._cached_get(f"/intelligence/entity/{entity}", TTL_ENTITY)

    async def get_entity_summary(self, entity: str) -> dict:
        """Aggregated entity statistics."""
        return await self._cached_get(f"/intelligence/entity/{entity}/summary", TTL_ENTITY)

    async def get_entity_predictions(self, entity: str) -> dict:
        """ML-generated address predictions for an entity."""
        return await self._cached_get(f"/intelligence/entity_predictions/{entity}", TTL_ENTITY)

    async def get_entity_balance_changes(
        self,
        *,
        chains: Optional[str] = None,
        entity_types: Optional[str] = None,
        entity_ids: Optional[str] = None,
        entity_tags: Optional[str] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> dict:
        """Ranked list of entities with balance changes over a time interval."""
        params = self._build_params(
            chains=chains,
            entityTypes=entity_types,
            entityIds=entity_ids,
            entityTags=entity_tags,
            timeLast=time_last,
            timeGte=time_gte,
            timeLte=time_lte,
            sortKey=sort_key,
            sortDir=sort_dir,
            limit=limit,
            offset=offset,
        )
        return await self._get("/intelligence/entity_balance_changes", params or None)

    # ===================================================================
    # Intelligence — Token & Contract
    # ===================================================================

    async def get_token_by_id(self, coingecko_id: str) -> dict:
        """Token data by CoinGecko pricing ID."""
        return await self._cached_get(f"/intelligence/token/{coingecko_id}", TTL_ADDRESS)

    async def get_token_by_address(self, chain: str, address: str) -> dict:
        """Token data by chain and contract address."""
        return await self._cached_get(f"/intelligence/token/{chain}/{address}", TTL_ADDRESS)

    async def get_contract(self, chain: str, address: str) -> dict:
        """Contract metadata including deployer info."""
        return await self._cached_get(f"/intelligence/contract/{chain}/{address}", TTL_ADDRESS)

    # ===================================================================
    # Intelligence — Search
    # ===================================================================

    async def search(self, query: str) -> dict:
        """Full-text search across entities, addresses, and tokens."""
        return await self._get("/intelligence/search", params={"query": query})

    # ===================================================================
    # Balances & Portfolio
    # ===================================================================

    async def get_address_balances(
        self,
        address: str,
        *,
        chains: Optional[str] = None,
    ) -> dict:
        """Current token holdings for an address."""
        params = self._build_params(chains=chains)
        return await self._cached_get(f"/balances/address/{address}", TTL_MARKET, params or None)

    async def get_entity_balances(
        self,
        entity: str,
        *,
        chains: Optional[str] = None,
    ) -> dict:
        """Current token holdings for an entity."""
        params = self._build_params(chains=chains)
        return await self._cached_get(f"/balances/entity/{entity}", TTL_MARKET, params or None)

    async def get_solana_subaccount_balances(self, addresses: str) -> dict:
        """Solana staking/lending positions for addresses (comma-separated)."""
        return await self._get(f"/balances/solana/subaccounts/address/{addresses}")

    async def get_solana_entity_subaccount_balances(self, entities: str) -> dict:
        """Solana staking/lending positions for entities (comma-separated slugs)."""
        return await self._get(f"/balances/solana/subaccounts/entity/{entities}")

    async def get_entity_portfolio(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
    ) -> dict:
        """Historical portfolio snapshots for an entity."""
        params = self._build_params(timeGte=time_gte, timeLte=time_lte)
        return await self._get(f"/portfolio/entity/{entity}", params or None)

    async def get_entity_portfolio_timeseries(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        chains: Optional[str] = None,
    ) -> dict:
        """Daily token holdings time series for an entity."""
        params = self._build_params(timeGte=time_gte, timeLte=time_lte, chains=chains)
        return await self._get(f"/portfolio/timeSeries/entity/{entity}", params or None)

    async def get_portfolio(
        self,
        address: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
    ) -> dict:
        """Historical portfolio snapshots for an address."""
        params = self._build_params(timeGte=time_gte, timeLte=time_lte)
        return await self._get(f"/portfolio/address/{address}", params or None)

    async def get_portfolio_timeseries(
        self,
        address: str,
        *,
        pricing_id: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
    ) -> dict:
        """Daily token holdings time series for an address."""
        params = self._build_params(
            pricingId=pricing_id,
            timeGte=time_gte,
            timeLte=time_lte,
            timeLast=time_last,
            chains=chains,
        )
        return await self._get(f"/portfolio/timeSeries/address/{address}", params or None)

    # ===================================================================
    # Historical Flow & Balance
    # ===================================================================

    async def get_address_history(
        self,
        address: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
    ) -> dict:
        """Historical USD balance snapshots for an address."""
        params = self._build_params(timeGte=time_gte, timeLte=time_lte, timeLast=time_last, chains=chains)
        return await self._get(f"/history/address/{address}", params or None)

    async def get_address_flow(
        self,
        address: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
    ) -> dict:
        """
        Historical USD inflows/outflows for an address.
        flow: "in" | "out" | "self" | "all"
        """
        params = self._build_params(
            timeGte=time_gte,
            timeLte=time_lte,
            timeLast=time_last,
            chains=chains,
            flow=flow,
        )
        return await self._get(f"/flow/address/{address}", params or None)

    async def get_entity_flow(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
    ) -> dict:
        """
        Historical USD inflows/outflows for an entity.
        flow: "in" | "out" | "self" | "all"
        """
        params = self._build_params(
            timeGte=time_gte,
            timeLte=time_lte,
            timeLast=time_last,
            chains=chains,
            flow=flow,
        )
        return await self._get(f"/flow/entity/{entity}", params or None)

    async def get_entity_history(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
    ) -> dict:
        """Historical USD balance snapshots for an entity."""
        params = self._build_params(timeGte=time_gte, timeLte=time_lte, timeLast=time_last, chains=chains)
        return await self._get(f"/history/entity/{entity}", params or None)

    # ===================================================================
    # Counterparties  (rate-limited: 1 req/sec)
    # ===================================================================

    async def get_counterparties(
        self,
        address: str,
        *,
        flow: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
    ) -> dict:
        """
        Top transaction counterparties for an address.
        Rate-limited to 1 request/second.
        flow: "in" | "out" | "self" | "all"
        """
        params = self._build_params(
            flow=flow,
            timeGte=time_gte,
            timeLte=time_lte,
            timeLast=time_last,
            chains=chains,
            limit=limit,
            offset=offset,
            sortKey=sort_key,
            sortDir=sort_dir,
        )
        return await self._get(f"/counterparties/address/{address}", params or None, rate_limited=True)

    async def get_entity_counterparties(
        self,
        entity: str,
        *,
        flow: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
    ) -> dict:
        """
        Top transaction counterparties for an entity.
        Rate-limited to 1 request/second.
        flow: "in" | "out" | "self" | "all"
        """
        params = self._build_params(
            flow=flow,
            timeGte=time_gte,
            timeLte=time_lte,
            timeLast=time_last,
            chains=chains,
            limit=limit,
            offset=offset,
            sortKey=sort_key,
            sortDir=sort_dir,
        )
        return await self._get(f"/counterparties/entity/{entity}", params or None, rate_limited=True)

    # ===================================================================
    # Swaps / DEX  (rate-limited: 1 req/sec)
    # ===================================================================

    async def get_swaps(
        self,
        address: Optional[str] = None,
        entity: Optional[str] = None,
        *,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
        tokens: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
    ) -> dict:
        """
        DEX trade data.
        Rate-limited to 1 request/second.
        Requires either `address` or `entity`.
        """
        if not address and not entity:
            raise ValueError("Either `address` or `entity` must be provided.")
        params = self._build_params(
            address=address,
            entity=entity,
            chains=chains,
            flow=flow,
            tokens=tokens,
            timeGte=time_gte,
            timeLte=time_lte,
            timeLast=time_last,
            limit=limit,
            offset=offset,
            sortKey=sort_key,
            sortDir=sort_dir,
        )
        return await self._get("/swaps", params, rate_limited=True)

    # ===================================================================
    # Loans / DeFi positions
    # ===================================================================

    async def get_address_loans(self, address: str) -> dict:
        """Loaned, supplied, and borrowed DeFi positions for an address."""
        return await self._cached_get(f"/loans/address/{address}", TTL_ADDRESS)

    async def get_entity_loans(self, entity: str) -> dict:
        """Loaned, supplied, and borrowed DeFi positions for an entity."""
        return await self._cached_get(f"/loans/entity/{entity}", TTL_ENTITY)

    # ===================================================================
    # Cluster
    # ===================================================================

    async def get_cluster_summary(self, cluster_id: str) -> dict:
        """Summary statistics for a blockchain address cluster."""
        return await self._cached_get(f"/cluster/{cluster_id}/summary", TTL_ADDRESS)

    # ===================================================================
    # Update / Feed endpoints  (cursor-paginated)
    # ===================================================================

    async def get_address_updates(
        self,
        *,
        since: Optional[int] = None,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> dict:
        """
        Address intelligence changes (cursor-paginated).
        status: "new" | "updated" | "deleted"
        Max time window: 7 days.
        """
        params = self._build_params(since=since, pageToken=page_token, status=status, limit=limit)
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        return await self._get("/intelligence/addresses/updates", params or None)

    async def get_address_tag_updates(
        self,
        *,
        since: Optional[int] = None,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> dict:
        """Address-tag association changes (cursor-paginated)."""
        params = self._build_params(since=since, pageToken=page_token, status=status, limit=limit)
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        return await self._get("/intelligence/address_tags/updates", params or None)

    async def get_entity_updates(
        self,
        *,
        since: Optional[int] = None,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> dict:
        """Entity metadata changes — name, type, deletion (cursor-paginated)."""
        params = self._build_params(since=since, pageToken=page_token, status=status, limit=limit)
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        return await self._get("/intelligence/entities/updates", params or None)

    async def get_tag_updates(
        self,
        *,
        since: Optional[int] = None,
        from_ts: Optional[int] = None,
        to_ts: Optional[int] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
        page_token: Optional[str] = None,
    ) -> dict:
        """Tag definition changes (cursor-paginated)."""
        params = self._build_params(since=since, pageToken=page_token, status=status, limit=limit)
        if from_ts is not None:
            params["from"] = from_ts
        if to_ts is not None:
            params["to"] = to_ts
        return await self._get("/intelligence/tags/updates", params or None)

    # ===================================================================
    # Network & Market Data
    # ===================================================================

    async def get_chains(self) -> list:
        """List of all supported blockchain networks."""
        return await self._cached_get("/chains", TTL_STATIC)

    async def get_entity_types(self) -> list:
        """Available entity classification types."""
        return await self._cached_get("/intelligence/entity_types", TTL_STATIC)

    async def get_networks_status(self) -> dict:
        """Current network metrics: price, volume, gas fees."""
        return await self._cached_get("/networks/status", TTL_MARKET)

    async def get_network_history(
        self,
        chain: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
    ) -> dict:
        """Historical price/volume data for a network."""
        params = self._build_params(timeGte=time_gte, timeLte=time_lte, timeLast=time_last)
        return await self._get(f"/networks/history/{chain}", params or None)

    async def get_altcoin_index(self) -> dict:
        """Altcoin performance metrics."""
        return await self._cached_get("/marketdata/altcoin_index", TTL_MARKET)

    async def get_funding_rates(
        self,
        base_token: str,
        *,
        exchanges: Optional[str] = None,
        time_period: Optional[str] = None,
        token_margined: Optional[bool] = None,
    ) -> dict:
        """
        Max funding rate time series for a perpetual futures instrument.

        base_token: token ID (e.g. 'bitcoin', 'bulla-3')
        exchanges: comma-separated exchange slugs (e.g. 'binance,okx,bybit,deribit,arkham')
        time_period: '1d' | '1w' | '1m' | '3m' | '6m' | '1y'
        token_margined: True = coin-margined contracts, False = stablecoin-margined
        """
        params = self._build_params(
            baseToken=base_token,
            exchanges=exchanges,
            timePeriod=time_period,
            tokenMargined=token_margined,
        )
        return await self._get("/marketdata/max_instrument_funding_rates_time_series", params or None)

    async def get_arkm_circulating_supply(self) -> dict:
        """ARKM token circulating supply."""
        return await self._cached_get("/arkm/circulating", TTL_MARKET)

    # ===================================================================
    # Pagination helper
    # ===================================================================

    async def paginate_updates(
        self,
        endpoint_fn,
        **kwargs,
    ) -> AsyncIterator[dict]:
        """
        Async generator that automatically follows cursor pagination
        for any of the `get_*_updates` methods.

        Example:
            async for page in client.paginate_updates(
                client.get_address_updates, since=1700000000000, limit=100
            ):
                for item in page["items"]:
                    process(item)
        """
        page_token: Optional[str] = kwargs.pop("page_token", None)
        while True:
            result = await endpoint_fn(**kwargs, page_token=page_token)
            yield result
            if not result.get("hasMore"):
                break
            page_token = result.get("pageToken")
            if not page_token:
                break

    # ===================================================================
    # Transfers  (rate-limited: 1 req/sec)
    # ===================================================================

    async def get_transfers(
        self,
        *,
        base: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
        from_addr: Optional[str] = None,
        to: Optional[str] = None,
        tokens: Optional[str] = None,
        counterparties: Optional[str] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        value_gte: Optional[str] = None,
        value_lte: Optional[str] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> dict:
        """
        On-chain token transfers with rich filtering.
        Rate-limited to 1 request/second.

        base: address or entity slug to pivot on (e.g. '0xabc' or 'binance')
        from_addr / to: source/dest filter — supports special syntax:
            'type:cex', 'deposit:binance', comma-separated addresses
        tokens: comma-separated token IDs or contract addresses
        flow: 'in' | 'out' | 'self' | 'all'
        time_last: '24h' | '7d' | '30d'
        """
        params = self._build_params(
            base=base,
            chains=chains,
            flow=flow,
            to=to,
            tokens=tokens,
            counterparties=counterparties,
            timeLast=time_last,
            timeGte=time_gte,
            timeLte=time_lte,
            valueGte=value_gte,
            valueLte=value_lte,
            usdGte=usd_gte,
            usdLte=usd_lte,
            sortKey=sort_key,
            sortDir=sort_dir,
            limit=limit,
            offset=offset,
        )
        # `from` is a Python keyword — add manually
        if from_addr is not None:
            params["from"] = from_addr
        return await self._get("/transfers", params or None, rate_limited=True)

    async def get_transfers_histogram(
        self,
        *,
        base: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
        from_addr: Optional[str] = None,
        to: Optional[str] = None,
        tokens: Optional[str] = None,
        counterparties: Optional[str] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        value_gte: Optional[str] = None,
        value_lte: Optional[str] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
        granularity: Optional[str] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list:
        """
        Detailed transfer volume histogram by time bucket (API-tier only).
        Rate-limited to 1 request/second.

        granularity: '1h' | '1d' (only '1d' for ranges > 30 days)
        """
        params = self._build_params(
            base=base,
            chains=chains,
            flow=flow,
            to=to,
            tokens=tokens,
            counterparties=counterparties,
            timeLast=time_last,
            timeGte=time_gte,
            timeLte=time_lte,
            valueGte=value_gte,
            valueLte=value_lte,
            usdGte=usd_gte,
            usdLte=usd_lte,
            granularity=granularity,
            sortKey=sort_key,
            sortDir=sort_dir,
            limit=limit,
            offset=offset,
        )
        if from_addr is not None:
            params["from"] = from_addr
        return await self._get("/transfers/histogram", params or None, rate_limited=True)

    async def get_transfers_histogram_simple(
        self,
        *,
        base: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
        from_addr: Optional[str] = None,
        to: Optional[str] = None,
        tokens: Optional[str] = None,
        counterparties: Optional[str] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        value_gte: Optional[str] = None,
        value_lte: Optional[str] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list:
        """
        Simplified transfer count/volume histogram (public endpoint, no API tier required).
        """
        params = self._build_params(
            base=base,
            chains=chains,
            flow=flow,
            to=to,
            tokens=tokens,
            counterparties=counterparties,
            timeLast=time_last,
            timeGte=time_gte,
            timeLte=time_lte,
            valueGte=value_gte,
            valueLte=value_lte,
            usdGte=usd_gte,
            usdLte=usd_lte,
            sortKey=sort_key,
            sortDir=sort_dir,
            limit=limit,
            offset=offset,
        )
        if from_addr is not None:
            params["from"] = from_addr
        return await self._get("/transfers/histogram/simple", params or None)

    async def get_transfers_by_tx(
        self,
        tx_hash: str,
        *,
        chain: Optional[str] = None,
        transfer_type: Optional[str] = None,
    ) -> list:
        """
        All token and native transfers within a specific transaction.

        tx_hash: transaction hash
        chain: blockchain identifier (e.g. 'ethereum', 'bsc')
        transfer_type: 'external' | 'internal' | 'token'
        """
        params = self._build_params(chain=chain, transferType=transfer_type)
        return await self._get(f"/transfers/tx/{tx_hash}", params or None)


# ===================================================================
# Quick usage example
# ===================================================================


async def _example():
    import os

    # Режим 1: API ключ
    # async with ArkhamClient(api_key=os.environ["ARKHAM_API_KEY"]) as client:

    # Режим 2: Cookie
    # async with ArkhamClient(cookie=os.environ["ARKHAM_COOKIE"]) as client:

    # Режим 3: оба
    async with ArkhamClient(
        api_key=os.environ.get("ARKHAM_API_KEY"),
        cookie=os.environ.get("ARKHAM_COOKIE"),
    ) as client:
        # Single address lookup
        addr = await client.get_address("0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045")
        print("Address:", addr)

        # Batch lookup
        batch = await client.batch_addresses(
            [
                "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045",
                "0xBE0eB53F46cd790Cd13851d5EFf43D12404d33E8",
            ]
        )
        print("Batch:", batch)

        # Paginate address updates
        async for page in client.paginate_updates(
            client.get_address_updates,
            since=1_700_000_000_000,
            limit=100,
        ):
            print(f"Got {len(page.get('items', []))} updates")


if __name__ == "__main__":
    asyncio.run(_example())
