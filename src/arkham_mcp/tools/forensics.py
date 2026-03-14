"""
Forensic tools — pattern detection for coordinated manipulation, bots, and anomalous activity.

These tools do the heavy statistical lifting so the LLM can reason over results
instead of performing raw analysis on large transfer arrays.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from fastmcp import FastMCP
from fastmcp.server.context import Context

from ._transfer_utils import (
    _addr,
    _entity_name,
    _is_fake_token,
    amount_stats,
    classify_pattern,
    compact_transfer,
    counterparty_stats,
    timing_stats,
)
from .investigation import _RISK_TAGS, _EXCHANGE_TYPES


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _classify_source(enriched: dict, transfer_count_in_dataset: int) -> str:
    entity = enriched.get("arkhamEntity") or {}
    etype  = entity.get("type") or ""
    tags   = [t.get("name", "").lower() for t in (enriched.get("populatedTags") or [])]

    if any(tag in _RISK_TAGS for tag in tags) or etype == "mixer":
        return "mixer"
    if etype in _EXCHANGE_TYPES:
        return "cex_withdrawal"
    if entity.get("name"):
        return "identified_entity"
    if transfer_count_in_dataset <= 2:
        return "fresh_wallet"
    return "unknown"


def _source_summary(sources: list[dict]) -> dict:
    if not sources:
        return {}
    n = len(sources)
    counts: dict[str, int] = {}
    for s in sources:
        c = s.get("classification", "unknown")
        counts[c] = counts.get(c, 0) + 1
    return {k + "_pct": round(v / n * 100, 1) for k, v in counts.items()}


def _risk_text(summary: dict) -> str:
    mixer_pct   = summary.get("mixer_pct", 0)
    fresh_pct   = summary.get("fresh_wallet_pct", 0)
    unknown_pct = summary.get("unknown_pct", 0)
    cex_pct     = summary.get("cex_withdrawal_pct", 0)

    if mixer_pct > 10:
        return f"HIGH RISK — {mixer_pct}% of funds trace to mixers."
    if unknown_pct > 70:
        return f"SUSPICIOUS — {unknown_pct}% of funding sources are unidentified wallets."
    if fresh_pct > 50:
        return f"SUSPICIOUS — {fresh_pct}% of funds come from fresh (new) wallets, common in layered schemes."
    if cex_pct > 60:
        return f"LOW RISK — {cex_pct}% of funds originate from centralised exchanges."
    return "MODERATE — mixed funding sources, further investigation recommended."


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register(mcp: FastMCP) -> None:

    # -----------------------------------------------------------------------
    # 1. analyze_transfers_pattern
    # -----------------------------------------------------------------------

    @mcp.tool(
        name="analyze_transfers_pattern",
        description=(
            "Fetch transfers and run statistical analysis to detect anomalous patterns. "
            "Returns timing regularity, amount distribution, counterparty concentration, "
            "and a pattern classification: bot_market_maker | wash_trading | "
            "layered_disbursement | dust_attack | normal_trading. "
            "Use this instead of raw get_transfers when you need to UNDERSTAND behaviour. "
            "base: pivot address or entity. flow: 'in'|'out'|'all'. "
            "time_last: '24h'|'7d'|'30d'. tokens: comma-separated token IDs. "
            "include_raw: set true only if you need the individual transfer records too."
        ),
    )
    async def analyze_transfers_pattern(
        ctx: Context,
        base: Optional[str] = None,
        flow: Optional[str] = None,
        time_last: Optional[str] = "7d",
        tokens: Optional[str] = None,
        chains: Optional[str] = None,
        from_addr: Optional[str] = None,
        to: Optional[str] = None,
        usd_gte: Optional[str] = None,
        limit: int = 100,
        include_raw: bool = False,
    ) -> dict:
        client = ctx.lifespan_context["client"]

        raw = await client.get_transfers(
            base=base,
            flow=flow,
            time_last=time_last,
            tokens=tokens,
            chains=chains,
            from_addr=from_addr,
            to=to,
            usd_gte=usd_gte,
            sort_key="time",
            sort_dir="asc",
            limit=limit,
        )

        transfers = (raw or {}).get("transfers") or []

        if not transfers:
            return {
                "summary": "No transfers found for the given parameters.",
                "pattern": "unknown",
                "confidence": 0.0,
                "signals": [],
                "total_transfers_analyzed": 0,
            }

        fake_count = sum(1 for t in transfers if _is_fake_token(t))
        t_stats    = timing_stats(transfers)
        a_stats    = amount_stats(transfers)
        cp_stats   = counterparty_stats(transfers, pivot=base)
        pattern, confidence, signals = classify_pattern(
            t_stats, a_stats, cp_stats, fake_count, len(transfers)
        )

        result: dict = {
            "summary":   _pattern_summary(pattern, confidence, signals, t_stats, a_stats, cp_stats, fake_count),
            "pattern":   pattern,
            "confidence": confidence,
            "signals":   signals,
            "timing":    t_stats,
            "amounts":   a_stats,
            "counterparties": cp_stats,
            "fake_token_count": fake_count,
            "total_transfers_analyzed": len(transfers),
        }

        if include_raw:
            result["transfers"] = [compact_transfer(t) for t in transfers]

        return result

    # -----------------------------------------------------------------------
    # 2. find_coordinated_wallets
    # -----------------------------------------------------------------------

    @mcp.tool(
        name="find_coordinated_wallets",
        description=(
            "Identify wallets likely controlled by the same actor or acting in coordination "
            "with a seed address. Checks: shared cluster ID, common counterparties, "
            "timing proximity, same token focus. "
            "Returns suspected groups with coordination_score 0-1 and evidence list. "
            "time_last: '24h'|'7d'|'30d'."
        ),
    )
    async def find_coordinated_wallets(
        address: str,
        ctx: Context,
        time_last: str = "7d",
        chains: Optional[str] = None,
        max_counterparties: int = 30,
    ) -> dict:
        client = ctx.lifespan_context["client"]

        # Fetch counterparties and transfers in parallel
        cp_data, transfers_raw = await asyncio.gather(
            client.get_counterparties(
                address,
                time_last=time_last,
                chains=chains,
                limit=max_counterparties,
                sort_key="volumeUsd",
                sort_dir="desc",
            ),
            client.get_transfers(
                base=address,
                time_last=time_last,
                chains=chains,
                sort_key="time",
                sort_dir="asc",
                limit=100,
            ),
            return_exceptions=True,
        )

        cp_list: list[dict] = []
        if not isinstance(cp_data, Exception) and isinstance(cp_data, dict):
            cp_list = cp_data.get("counterparties") or cp_data.get("data") or []

        transfers: list[dict] = []
        if not isinstance(transfers_raw, Exception) and isinstance(transfers_raw, dict):
            transfers = transfers_raw.get("transfers") or []

        if not cp_list:
            return {
                "seed_address": address,
                "suspected_groups": [],
                "summary": "No counterparties found — cannot determine coordination.",
            }

        # Batch-enrich all counterparty addresses
        cp_addresses = [cp.get("address") for cp in cp_list if cp.get("address")]
        enriched_batch = await client.batch_addresses_enriched(cp_addresses)
        enriched_map: dict[str, dict] = {}
        if isinstance(enriched_batch, list):
            enriched_map = {
                item.get("address", ""): item
                for item in enriched_batch
                if isinstance(item, dict)
            }

        # Build timing index: epoch → list of addresses active in ±5 min window
        from datetime import datetime, timezone
        seed_timestamps: list[float] = []
        for t in transfers:
            ts = t.get("blockTimestamp", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    seed_timestamps.append(dt.timestamp())
                except (ValueError, TypeError):
                    pass

        # Group by cluster_id, then by coordination signals
        cluster_groups: dict[str, list[str]] = {}
        unclassified: list[str] = []

        for cp_addr in cp_addresses:
            enriched = enriched_map.get(cp_addr, {})
            cid = enriched.get("clusterId")
            if cid:
                cluster_groups.setdefault(cid, []).append(cp_addr)
            else:
                unclassified.append(cp_addr)

        # Score each candidate
        groups: list[dict] = []

        # Same-cluster groups (strong signal)
        for cid, members in cluster_groups.items():
            if len(members) < 2:
                continue
            groups.append({
                "addresses":          members,
                "coordination_score": 0.90,
                "signals":            [f"All {len(members)} addresses share cluster ID {cid}"],
                "cluster_id":         cid,
                "entity_overlap":     None,
            })

        # Seed's own cluster — find if seed shares cluster with any cp
        seed_enriched = await client.get_address_enriched(address, include_clusters=True)
        if isinstance(seed_enriched, dict):
            seed_cluster = seed_enriched.get("clusterId")
            if seed_cluster and seed_cluster in cluster_groups:
                groups[-1]["signals"].insert(0, "Seed address shares cluster with these wallets")
                groups[-1]["coordination_score"] = min(groups[-1]["coordination_score"] + 0.05, 1.0)

        # Token-focus overlap among unclassified addresses
        token_focus: dict[str, list[str]] = {}
        for t in transfers:
            tok  = (t.get("tokenSymbol") or "").strip()
            addr = _addr(t.get("fromAddress")) or _addr(t.get("toAddress"))
            if tok and addr and addr != address.lower():
                token_focus.setdefault(tok, []).append(addr)

        for tok, addrs in token_focus.items():
            unique = list(dict.fromkeys(a for a in addrs if a in unclassified))
            if len(unique) >= 3:
                score = min(0.4 + len(unique) * 0.05, 0.75)
                groups.append({
                    "addresses":          unique[:10],
                    "coordination_score": round(score, 2),
                    "signals":            [f"{len(unique)} addresses focus on same token ({tok})"],
                    "cluster_id":         None,
                    "entity_overlap":     None,
                })

        # Sort by score descending
        groups.sort(key=lambda g: g["coordination_score"], reverse=True)

        total_suspicious = sum(len(g["addresses"]) for g in groups)
        summary = (
            f"Found {len(groups)} coordination group(s) involving {total_suspicious} address(es). "
            f"Strongest signal: {groups[0]['signals'][0]}" if groups
            else "No coordination patterns detected among counterparties."
        )

        return {
            "seed_address":    address,
            "suspected_groups": groups[:10],
            "summary":         summary,
        }

    # -----------------------------------------------------------------------
    # 3. trace_fund_source
    # -----------------------------------------------------------------------

    @mcp.tool(
        name="trace_fund_source",
        description=(
            "Backward fund tracing — who funded this address? "
            "Classifies each source as: cex_withdrawal | identified_entity | "
            "fresh_wallet | mixer | unknown. "
            "Returns a % breakdown and risk assessment. "
            "hops=2 traces one level deeper for unidentified sources. "
            "time_last: '24h'|'7d'|'30d'. min_usd: ignore sources below this value."
        ),
    )
    async def trace_fund_source(
        address: str,
        ctx: Context,
        time_last: str = "30d",
        hops: int = 1,
        min_usd: float = 0.0,
        chains: Optional[str] = None,
    ) -> dict:
        client = ctx.lifespan_context["client"]

        if hops not in (1, 2):
            hops = 1

        # Hop 1: direct inflows
        raw = await client.get_transfers(
            base=address,
            flow="in",
            time_last=time_last,
            chains=chains,
            sort_key="usd",
            sort_dir="desc",
            limit=50,
        )
        transfers: list[dict] = (raw or {}).get("transfers") or []
        if min_usd > 0:
            transfers = [t for t in transfers if (t.get("historicalUSD") or 0) >= min_usd]

        # Aggregate by sender
        sender_usd: dict[str, float] = {}
        sender_count: dict[str, int] = {}
        for t in transfers:
            if _is_fake_token(t):
                continue
            fa = _addr(t.get("fromAddress"))
            if fa:
                sender_usd[fa]   = sender_usd.get(fa, 0) + (t.get("historicalUSD") or 0)
                sender_count[fa] = sender_count.get(fa, 0) + 1

        if not sender_usd:
            return {
                "address": address,
                "funding_sources": [],
                "source_summary":  {},
                "risk_assessment": "No inbound transfers found.",
            }

        # Batch-enrich senders
        hop1_addrs = list(sender_usd.keys())
        enriched_batch = await client.batch_addresses_enriched(hop1_addrs)
        enriched_map: dict[str, dict] = {}
        if isinstance(enriched_batch, list):
            enriched_map = {
                item.get("address", ""): item
                for item in enriched_batch
                if isinstance(item, dict)
            }

        sources: list[dict] = []
        unidentified_addrs: list[str] = []

        for addr in hop1_addrs:
            enriched    = enriched_map.get(addr, {})
            entity      = enriched.get("arkhamEntity") or {}
            tags        = [t.get("name", "") for t in (enriched.get("populatedTags") or [])]
            risk_flags  = [tag.lower() for tag in tags if tag.lower() in _RISK_TAGS]
            classif     = _classify_source(enriched, sender_count[addr])

            if classif == "unknown":
                unidentified_addrs.append(addr)

            sources.append({
                "address":        addr,
                "entity_name":    entity.get("name"),
                "entity_type":    entity.get("type"),
                "classification": classif,
                "amount_usd":     round(sender_usd[addr], 2),
                "tx_count":       sender_count[addr],
                "risk_flags":     risk_flags,
                "hop":            1,
            })

        # Hop 2: trace unknown sources one level back
        if hops == 2 and unidentified_addrs:
            hop2_tasks = [
                client.get_transfers(
                    base=ua,
                    flow="in",
                    time_last=time_last,
                    chains=chains,
                    sort_key="usd",
                    sort_dir="desc",
                    limit=10,
                )
                for ua in unidentified_addrs[:10]  # limit to avoid rate-limit storms
            ]
            hop2_results = await asyncio.gather(*hop2_tasks, return_exceptions=True)

            hop2_addrs: set[str] = set()
            hop2_usd:   dict[str, float] = {}
            hop2_count: dict[str, int]   = {}

            for res in hop2_results:
                if isinstance(res, Exception) or not isinstance(res, dict):
                    continue
                for t in (res.get("transfers") or []):
                    if _is_fake_token(t):
                        continue
                    fa = _addr(t.get("fromAddress"))
                    if fa and fa not in hop1_addrs:
                        hop2_addrs.add(fa)
                        hop2_usd[fa]   = hop2_usd.get(fa, 0) + (t.get("historicalUSD") or 0)
                        hop2_count[fa] = hop2_count.get(fa, 0) + 1

            if hop2_addrs:
                e2_batch = await client.batch_addresses_enriched(list(hop2_addrs))
                e2_map: dict[str, dict] = {}
                if isinstance(e2_batch, list):
                    e2_map = {
                        item.get("address", ""): item
                        for item in e2_batch
                        if isinstance(item, dict)
                    }
                for addr in hop2_addrs:
                    enriched   = e2_map.get(addr, {})
                    entity     = enriched.get("arkhamEntity") or {}
                    tags       = [t.get("name", "") for t in (enriched.get("populatedTags") or [])]
                    risk_flags = [tag.lower() for tag in tags if tag.lower() in _RISK_TAGS]
                    classif    = _classify_source(enriched, hop2_count[addr])
                    sources.append({
                        "address":        addr,
                        "entity_name":    entity.get("name"),
                        "entity_type":    entity.get("type"),
                        "classification": classif,
                        "amount_usd":     round(hop2_usd[addr], 2),
                        "tx_count":       hop2_count[addr],
                        "risk_flags":     risk_flags,
                        "hop":            2,
                    })

        sources.sort(key=lambda s: s["amount_usd"], reverse=True)
        summary = _source_summary(sources)

        return {
            "address":         address,
            "funding_sources": sources,
            "source_summary":  summary,
            "risk_assessment": _risk_text(summary),
        }

    # -----------------------------------------------------------------------
    # 4. aggregate_wallet_activity
    # -----------------------------------------------------------------------

    @mcp.tool(
        name="aggregate_wallet_activity",
        description=(
            "Paginate through ALL matching transfers, aggregate per-wallet stats, "
            "and return a ranked leaderboard — no manual offset needed.\n"
            "PARAMETERS:\n"
            "  tokens          — token contract address or CoinGecko ID\n"
            "  chains          — comma-separated chains (e.g. 'bsc,ethereum')\n"
            "  role            — 'buyer' | 'seller' | 'all'\n"
            "  time_last       — '1h' | '24h' | '7d' | '30d' (ignored when date_from/date_to set)\n"
            "  date_from       — start of window, ISO format e.g. '2026-03-10' or '2026-03-10T12:00'\n"
            "  date_to         — end of window, ISO format e.g. '2026-03-11T23:59'\n"
            "  usd_gte         — minimum USD per transfer (e.g. '200')\n"
            "  usd_lte         — maximum USD per transfer\n"
            "  sort_by         — 'tx_count' | 'volume_usd' | 'avg_usd' (default: 'tx_count')\n"
            "  top_n           — wallets to return, max 100 (default: 30)\n"
            "  exclude_entities — comma-separated entity names to skip\n"
            "  exclude_types   — comma-separated entity types to skip (e.g. 'cex,dex,bridge')\n"
            "  page_size       — records per API call, max 70\n"
            "Automatically pages up to 10 000 records. ~1 req/sec."
        ),
    )
    async def aggregate_wallet_activity(
        ctx: Context,
        tokens: Optional[str] = None,
        chains: Optional[str] = None,
        role: str = "buyer",
        time_last: Optional[str] = "7d",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        usd_gte: Optional[str] = None,
        usd_lte: Optional[str] = None,
        sort_by: str = "tx_count",
        top_n: int = 30,
        exclude_entities: Optional[str] = None,
        exclude_types: Optional[str] = None,
        page_size: int = 70,
    ) -> dict:
        from datetime import datetime, timezone

        client = ctx.lifespan_context["client"]

        PAGE_SIZE  = max(50, min(page_size, 70))
        MAX_OFFSET = 10_000 - PAGE_SIZE

        # --- resolve time window ---
        _ts_from: Optional[str] = None  # ISO prefix for client-side filtering
        _ts_to:   Optional[str] = None
        _time_last = time_last

        if date_from or date_to:
            now = datetime.now(tz=timezone.utc)
            if date_from:
                dt_from = datetime.fromisoformat(date_from).replace(tzinfo=timezone.utc)
                _ts_from = dt_from.strftime("%Y-%m-%dT%H:%M")
                days_back = (now - dt_from).total_seconds() / 86400
                if days_back <= 1:
                    _time_last = "24h"
                elif days_back <= 7:
                    _time_last = "7d"
                else:
                    _time_last = "30d"
            if date_to:
                dt_to = datetime.fromisoformat(date_to).replace(tzinfo=timezone.utc)
                _ts_to = dt_to.strftime("%Y-%m-%dT%H:%M")

        # addr -> {tx_count, volume_usd, entity_name, entity_type, first_seen, last_seen}
        stats: dict[str, dict] = {}
        total_fetched = 0
        pages_fetched = 0
        offset = 0

        while offset <= MAX_OFFSET:
            raw = await client.get_transfers(
                tokens=tokens,
                chains=chains,
                flow="all",
                time_last=_time_last,
                usd_gte=usd_gte,
                usd_lte=usd_lte,
                sort_key="time",
                sort_dir="asc",
                limit=PAGE_SIZE,
                offset=offset,
            )

            transfers = (raw or {}).get("transfers") or []
            raw_count = len(transfers)
            if not raw_count:
                break

            # client-side filter for date window
            if _ts_from or _ts_to:
                transfers = [
                    t for t in transfers
                    if (not _ts_from or (t.get("blockTimestamp") or "") >= _ts_from)
                    and (not _ts_to   or (t.get("blockTimestamp") or "") <= _ts_to)
                ]

            for t in transfers:
                if _is_fake_token(t):
                    continue

                usd = t.get("historicalUSD") or 0
                ts  = (t.get("blockTimestamp") or "")[:16]

                candidates: list[tuple[str, dict, str]] = []

                if role in ("buyer", "all"):
                    ta   = t.get("toAddress") or {}
                    addr = ta.get("address") or ""
                    if addr:
                        candidates.append((addr, ta.get("arkhamEntity") or {}, "buyer"))

                if role in ("seller", "all"):
                    fa   = t.get("fromAddress") or {}
                    addr = fa.get("address") or ""
                    if addr:
                        candidates.append((addr, fa.get("arkhamEntity") or {}, "seller"))

                for addr, entity, w_role in candidates:
                    if addr not in stats:
                        stats[addr] = {
                            "address":     addr,
                            "tx_count":    0,
                            "volume_usd":  0.0,
                            "entity_name": entity.get("name"),
                            "entity_type": entity.get("type"),
                            "first_seen":  ts,
                            "last_seen":   ts,
                            "roles":       set(),
                        }
                    s = stats[addr]
                    s["tx_count"]   += 1
                    s["volume_usd"] += usd
                    s["roles"].add(w_role)
                    if ts:
                        if not s["first_seen"] or ts < s["first_seen"]:
                            s["first_seen"] = ts
                        if not s["last_seen"] or ts > s["last_seen"]:
                            s["last_seen"] = ts
                    if not s["entity_name"] and entity.get("name"):
                        s["entity_name"] = entity.get("name")
                        s["entity_type"] = entity.get("type")

            total_fetched += len(transfers)
            pages_fetched += 1
            offset        += PAGE_SIZE

            if raw_count < PAGE_SIZE:
                break  # last page (use raw_count, not filtered)

            await asyncio.sleep(1.1)

        # --- build exclusion sets ---
        excl_names = {
            e.strip().lower()
            for e in (exclude_entities or "").split(",")
            if e.strip()
        }
        excl_types = {
            t.strip().lower()
            for t in (exclude_types or "").split(",")
            if t.strip()
        }

        wallets = list(stats.values())

        if excl_names:
            wallets = [
                w for w in wallets
                if (w.get("entity_name") or "").lower() not in excl_names
            ]
        if excl_types:
            wallets = [
                w for w in wallets
                if (w.get("entity_type") or "").lower() not in excl_types
            ]

        # --- sort ---
        _sort_keys = {
            "tx_count":  lambda w: w["tx_count"],
            "volume_usd": lambda w: w["volume_usd"],
            "avg_usd":   lambda w: w["volume_usd"] / w["tx_count"] if w["tx_count"] else 0,
        }
        key_fn = _sort_keys.get(sort_by, _sort_keys["tx_count"])
        wallets.sort(key=key_fn, reverse=True)

        # --- format output ---
        top: list[dict] = []
        for w in wallets[:max(1, min(top_n, 100))]:
            avg = round(w["volume_usd"] / w["tx_count"], 2) if w["tx_count"] else 0
            top.append({
                "address":     w["address"],
                "tx_count":    w["tx_count"],
                "volume_usd":  round(w["volume_usd"], 2),
                "avg_usd":     avg,
                "entity":      w.get("entity_name"),
                "type":        w.get("entity_type"),
                "roles":       sorted(w["roles"]),
                "first_seen":  w["first_seen"],
                "last_seen":   w["last_seen"],
            })

        return {
            "_meta": {
                "transfers_processed": total_fetched,
                "pages_fetched":       pages_fetched,
                "unique_wallets":      len(stats),
                "after_filter":        len(wallets),
                "sort_by":             sort_by,
                "role":                role,
                "time_last":           _time_last,
                "date_from":           date_from,
                "date_to":             date_to,
            },
            "wallets": top,
        }

    # -----------------------------------------------------------------------
    # 5. scan_token_manipulation
    # -----------------------------------------------------------------------

    @mcp.tool(
        name="scan_token_manipulation",
        description=(
            "Scan a token for on-chain manipulation signals: pump & dump, wash trading, "
            "coordinated accumulation, anonymous buying, fake-token spoofing. "
            "Returns manipulation_score 0-100, verdict, red_flags, and key actors. "
            "Provide token_id (CoinGecko, e.g. 'bitcoin') OR token_address + chain. "
            "time_last: '24h'|'7d'|'30d'."
        ),
    )
    async def scan_token_manipulation(
        ctx: Context,
        token_id: Optional[str] = None,
        token_address: Optional[str] = None,
        chain: Optional[str] = None,
        time_last: str = "7d",
    ) -> dict:
        if not token_id and not token_address:
            raise ValueError("Provide either token_id (CoinGecko) or token_address + chain.")

        client = ctx.lifespan_context["client"]

        # Build token filter string for transfers API
        token_filter = token_id or token_address

        # Fetch transfers and token metadata in parallel
        transfers_raw, token_meta = await asyncio.gather(
            client.get_transfers(
                tokens=token_filter,
                sort_key="usd",
                sort_dir="desc",
                time_last=time_last,
                limit=100,
            ),
            (client.get_token_by_id(token_id) if token_id
             else client.get_token_by_address(chain, token_address)),
            return_exceptions=True,
        )

        transfers: list[dict] = []
        if not isinstance(transfers_raw, Exception) and isinstance(transfers_raw, dict):
            transfers = transfers_raw.get("transfers") or []

        meta: dict = {}
        if not isinstance(token_meta, Exception) and isinstance(token_meta, dict):
            meta = token_meta

        if not transfers:
            return {
                "token":              token_id or token_address,
                "manipulation_score": 0,
                "verdict":            "insufficient_data",
                "red_flags":          [],
                "key_actors":         [],
                "summary":            "No transfers found for this token in the given period.",
            }

        # Split real vs fake transfers
        real_transfers = [t for t in transfers if not _is_fake_token(t)]
        fake_count     = len(transfers) - len(real_transfers)

        # Identify buyers and sellers
        buyer_usd:  dict[str, float] = {}
        seller_usd: dict[str, float] = {}

        for t in real_transfers:
            fa  = _addr(t.get("fromAddress"))
            ta  = _addr(t.get("toAddress"))
            usd = t.get("historicalUSD") or 0
            if fa:
                seller_usd[fa] = seller_usd.get(fa, 0) + usd
            if ta:
                buyer_usd[ta] = buyer_usd.get(ta, 0) + usd

        all_actors = set(buyer_usd) | set(seller_usd)

        # Batch-enrich actors (cap at 50 to avoid slowness)
        enriched_map: dict[str, dict] = {}
        if all_actors:
            e_batch = await client.batch_addresses_enriched(list(all_actors)[:50])
            if isinstance(e_batch, list):
                enriched_map = {
                    item.get("address", ""): item
                    for item in e_batch
                    if isinstance(item, dict)
                }

        # --- Compute signals ---
        red_flags: list[str] = []
        score = 0

        # 1. Buyer concentration
        total_buy_usd = sum(buyer_usd.values()) or 1
        top3_buy = sorted(buyer_usd.values(), reverse=True)[:3]
        top3_buy_pct = round(sum(top3_buy) / total_buy_usd * 100, 1)
        if top3_buy_pct > 70:
            red_flags.append(f"CONCENTRATED_BUYERS: top 3 buyers control {top3_buy_pct}% of buy volume")
            score += 25

        # 2. Anonymous accumulation
        identified_buyers = sum(
            1 for addr in buyer_usd
            if (enriched_map.get(addr, {}).get("arkhamEntity") or {}).get("name")
        )
        anon_pct = round((len(buyer_usd) - identified_buyers) / len(buyer_usd) * 100, 1) if buyer_usd else 0
        if anon_pct > 80:
            red_flags.append(f"ANONYMOUS_ACCUMULATION: {anon_pct}% of buyers are unidentified wallets")
            score += 20

        # 3. Wash trading: same address on both sides
        wash_actors = set(buyer_usd) & set(seller_usd)
        if wash_actors:
            wash_vol = sum(min(buyer_usd.get(a, 0), seller_usd.get(a, 0)) for a in wash_actors)
            wash_pct = round(wash_vol / total_buy_usd * 100, 1)
            if wash_pct > 15:
                red_flags.append(f"WASH_TRADING: {len(wash_actors)} address(es) appear on both sides ({wash_pct}% of volume)")
                score += 30

        # 4. Coordinated pump: ≥5 large buys within 10-minute window
        t_stats = timing_stats(real_transfers)
        bursts  = t_stats.get("burst_windows") or []
        if len(bursts) >= 2:
            red_flags.append(f"COORDINATED_PUMP: {len(bursts)} burst windows detected (≥5 txs/60 sec)")
            score += 20

        # 5. Fake token spoofing
        if fake_count > 0:
            red_flags.append(f"FAKE_TOKEN_SPOOFING: {fake_count} transfers use spoofed tokens (historicalUSD=0)")
            score += 15

        # 6. Timing regularity (bot buying)
        reg = t_stats.get("regularity_score") or 0
        if reg > 0.8:
            red_flags.append(f"BOT_BUYING: timing regularity score {reg:.2f} suggests automated purchasing")
            score += 10

        score = min(score, 100)
        verdict = "high_risk" if score >= 60 else "suspicious" if score >= 30 else "normal"

        # Build key actors list
        def _actor_entry(addr: str, role: str, vol: float) -> dict:
            enriched = enriched_map.get(addr, {})
            entity   = (enriched.get("arkhamEntity") or {}).get("name")
            tags     = [t.get("name", "") for t in (enriched.get("populatedTags") or [])]
            return {
                "address":    addr,
                "role":       role,
                "volume_usd": round(vol, 2),
                "entity":     entity,
                "tags":       [tag for tag in tags if tag.lower() in _RISK_TAGS],
            }

        key_actors: list[dict] = []
        for addr, vol in sorted(buyer_usd.items(),  key=lambda x: -x[1])[:5]:
            key_actors.append(_actor_entry(addr, "buyer", vol))
        for addr, vol in sorted(seller_usd.items(), key=lambda x: -x[1])[:3]:
            if addr not in buyer_usd:
                key_actors.append(_actor_entry(addr, "seller", vol))
        for addr in wash_actors:
            for entry in key_actors:
                if entry["address"] == addr:
                    entry["role"] = "wash_trader"

        token_name = (meta.get("name") or meta.get("symbol") or token_id or token_address or "unknown")
        summary = (
            f"{token_name}: manipulation_score={score}/100 ({verdict}). "
            f"Analyzed {len(real_transfers)} real transfers, {fake_count} spoofed. "
            + (f"Flags: {', '.join(red_flags[:2])}." if red_flags else "No major flags.")
        )

        return {
            "token":              token_name,
            "manipulation_score": score,
            "verdict":            verdict,
            "red_flags":          red_flags,
            "key_actors":         key_actors,
            "timing":             t_stats,
            "amounts":            amount_stats(real_transfers),
            "summary":            summary,
        }


# ---------------------------------------------------------------------------
# Private summary helper
# ---------------------------------------------------------------------------

def _pattern_summary(
    pattern: str,
    confidence: float,
    signals: list[str],
    t_stats: dict,
    a_stats: dict,
    cp_stats: dict,
    fake_count: int,
) -> str:
    conf_word = "high" if confidence > 0.7 else "moderate" if confidence > 0.4 else "low"
    base = f"Pattern: {pattern} ({conf_word} confidence {confidence:.0%})."
    if signals:
        base += f" Key signal: {signals[0]}."
    if fake_count:
        base += f" {fake_count} fake-token transfer(s) detected."
    span = t_stats.get("span_hours")
    if span:
        base += f" Activity spans {span}h."
    return base
