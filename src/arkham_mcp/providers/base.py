"""
DataProvider — Protocol (interface) for blockchain data sources.

Any class that implements all these async methods satisfies the Protocol
without explicit inheritance (structural subtyping).

To add a new provider:
  1. Implement all methods below in a new file, e.g. providers/nansen.py
  2. Register it in providers/__init__.py
  3. Set ARKHAM_PROVIDER=nansen in .env
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class DataProvider(Protocol):

    # ── Intelligence / Address ──────────────────────────────────────────

    async def get_address(self, address: str) -> dict: ...

    async def get_address_all_chains(self, address: str) -> dict: ...

    async def get_address_enriched_all_chains(self, address: str) -> dict: ...

    async def get_address_enriched(
        self,
        address: str,
        *,
        include_tags: Optional[bool] = None,
        include_clusters: Optional[bool] = None,
        include_entity_predictions: Optional[bool] = None,
    ) -> dict: ...

    async def batch_addresses(self, addresses: list[str]) -> list[dict]: ...

    async def batch_addresses_all_chains(self, addresses: list[str]) -> list[dict]: ...

    async def batch_addresses_enriched(self, addresses: list[str]) -> list[dict]: ...

    async def batch_addresses_enriched_all_chains(self, addresses: list[str]) -> list[dict]: ...

    # ── Intelligence / Entity ───────────────────────────────────────────

    async def get_entity(self, entity: str) -> dict: ...

    async def get_entity_summary(self, entity: str) -> dict: ...

    async def get_entity_predictions(self, entity: str) -> dict: ...

    async def get_entity_balance_changes(
        self,
        *,
        chains: Optional[str] = None,
        entity_type: Optional[str] = None,
        time_last: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> dict: ...

    # ── Intelligence / Token & Contract ────────────────────────────────

    async def get_token_by_id(self, coingecko_id: str) -> dict: ...

    async def get_token_by_address(self, chain: str, address: str) -> dict: ...

    async def get_contract(self, chain: str, address: str) -> dict: ...

    # ── Search ──────────────────────────────────────────────────────────

    async def search(self, query: str) -> dict: ...

    # ── Balances ────────────────────────────────────────────────────────

    async def get_address_balances(
        self,
        address: str,
        *,
        chains: Optional[str] = None,
    ) -> dict: ...

    async def get_entity_balances(
        self,
        entity: str,
        *,
        chains: Optional[str] = None,
    ) -> dict: ...

    async def get_solana_subaccount_balances(self, addresses: str) -> dict: ...

    async def get_solana_entity_subaccount_balances(self, entities: str) -> dict: ...

    # ── Portfolio ───────────────────────────────────────────────────────

    async def get_portfolio(
        self,
        address: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
    ) -> dict: ...

    async def get_portfolio_timeseries(
        self,
        address: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        chains: Optional[str] = None,
    ) -> dict: ...

    async def get_entity_portfolio(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
    ) -> dict: ...

    async def get_entity_portfolio_timeseries(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        chains: Optional[str] = None,
    ) -> dict: ...

    # ── Historical Flow & Balance ───────────────────────────────────────

    async def get_address_history(
        self,
        address: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
    ) -> dict: ...

    async def get_address_flow(
        self,
        address: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
    ) -> dict: ...

    async def get_entity_flow(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
        flow: Optional[str] = None,
    ) -> dict: ...

    async def get_entity_history(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        chains: Optional[str] = None,
    ) -> dict: ...

    # ── Counterparties (rate-limited) ───────────────────────────────────

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
    ) -> dict: ...

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
    ) -> dict: ...

    # ── Swaps / DEX (rate-limited) ──────────────────────────────────────

    async def get_swaps(
        self,
        address: Optional[str] = None,
        entity: Optional[str] = None,
        *,
        chains: Optional[str] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
    ) -> dict: ...

    # ── Loans / DeFi ────────────────────────────────────────────────────

    async def get_address_loans(self, address: str) -> dict: ...

    async def get_entity_loans(self, entity: str) -> dict: ...

    # ── Cluster ──────────────────────────────────────────────────────────

    async def get_cluster_summary(self, cluster_id: str) -> dict: ...

    # ── Network & Market ────────────────────────────────────────────────

    async def get_chains(self) -> list: ...

    async def get_entity_types(self) -> list: ...

    async def get_networks_status(self) -> dict: ...

    async def get_network_history(
        self,
        chain: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
    ) -> dict: ...

    async def get_altcoin_index(self) -> dict: ...

    async def get_arkm_circulating_supply(self) -> dict: ...

    # ── Transfers (rate-limited) ─────────────────────────────────────────

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
        time_gte: Optional[str] = None,
        time_lte: Optional[str] = None,
        value_gte: Optional[str] = None,
        value_lte: Optional[str] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> dict: ...

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
        time_gte: Optional[str] = None,
        time_lte: Optional[str] = None,
        value_gte: Optional[str] = None,
        value_lte: Optional[str] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
        granularity: Optional[str] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list: ...

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
        time_gte: Optional[str] = None,
        time_lte: Optional[str] = None,
        value_gte: Optional[str] = None,
        value_lte: Optional[str] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list: ...

    async def get_transfers_by_tx(
        self,
        tx_hash: str,
        *,
        chain: Optional[str] = None,
        transfer_type: Optional[str] = None,
    ) -> list: ...
