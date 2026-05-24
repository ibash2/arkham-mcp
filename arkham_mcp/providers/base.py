"""
DataProvider protocol — the interface all providers must implement.

Structural subtyping: no inheritance needed, just implement the methods.

To add a new provider:
  1. Create providers/<name>.py with a create_provider(settings) async context manager
  2. Register it in providers/__init__.py
  3. Set ARKHAM_PROVIDER=<name> in .env
"""

from typing import Optional, Protocol, runtime_checkable


@runtime_checkable
class DataProvider(Protocol):

    # address

    async def get_address(self, address: str) -> dict: ...

    async def get_address_enriched(
        self,
        address: str,
        *,
        include_tags: Optional[bool] = None,
        include_clusters: Optional[bool] = None,
        include_entity_predictions: Optional[bool] = None,
    ) -> dict: ...

    async def batch_addresses(self, addresses: list[str]) -> list[dict]: ...

    async def batch_addresses_enriched(self, addresses: list[str]) -> list[dict]: ...

    # entity

    async def get_entity(self, entity: str) -> dict: ...

    async def get_entity_summary(self, entity: str) -> dict: ...

    async def get_entity_predictions(self, entity: str) -> dict: ...

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
        pricing_ids: Optional[str] = None,
        balance_min: Optional[float] = None,
        interval: Optional[str] = None,
        order_by: Optional[str] = None,
        order_dir: Optional[str] = None,
    ) -> dict: ...

    # token & contract

    async def get_token_by_id(self, coingecko_id: str) -> dict: ...

    async def get_token_by_address(self, chain: str, address: str) -> dict: ...

    async def get_contract(self, chain: str, address: str) -> dict: ...

    async def search(self, query: str) -> dict: ...

    # balances

    async def get_address_balances(self, address: str, *, chains: Optional[str] = None) -> dict: ...

    async def get_entity_balances(self, entity: str, *, chains: Optional[str] = None) -> dict: ...

    # portfolio

    async def get_portfolio(self, address: str, *, time: Optional[int] = None) -> dict: ...

    async def get_portfolio_timeseries(
        self,
        address: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        chains: Optional[str] = None,
    ) -> dict: ...

    async def get_entity_portfolio_timeseries(
        self,
        entity: str,
        *,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        chains: Optional[str] = None,
    ) -> dict: ...

    # history & flow

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

    # counterparties (rate-limited: 1 req/sec)

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

    # swaps / DEX (rate-limited: 1 req/sec)

    async def get_swaps(
        self,
        base: Optional[str] = None,
        entity: Optional[str] = None,
        *,
        chains: Optional[str] = None,
        token_from: Optional[str] = None,
        token_to: Optional[str] = None,
        protocols: Optional[str] = None,
        usd_gte: Optional[float] = None,
        usd_lte: Optional[float] = None,
        time_gte: Optional[int] = None,
        time_lte: Optional[int] = None,
        time_last: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        sort_key: Optional[str] = None,
        sort_dir: Optional[str] = None,
    ) -> dict: ...

    # loans / DeFi

    async def get_address_loans(self, address: str) -> dict: ...

    async def get_entity_loans(self, entity: str) -> dict: ...

    async def get_cluster_summary(self, cluster_id: str) -> dict: ...

    # network & market

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

    async def get_token_holders(self, token: str, *, group_by_entity: bool = False) -> dict: ...

    async def get_token_market(self, token: str) -> dict: ...

    async def get_token_top_flow(self, token: str, *, time_last: Optional[str] = None, chains: Optional[str] = None) -> dict: ...

    async def get_open_interest(self, base_token: str, *, exchanges: Optional[str] = None, instrument_type: Optional[str] = None, time_period: Optional[str] = None) -> dict: ...

    async def get_volume_timeseries(self, base_token: str, *, exchanges: Optional[str] = None, instrument_type: Optional[str] = None, time_period: Optional[str] = None) -> dict: ...

    # transfers (rate-limited: 1 req/sec)

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
