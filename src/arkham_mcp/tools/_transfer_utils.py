"""
Shared helpers for transfer analysis — used by atomic.py and forensics.py.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _is_fake_token(t: dict) -> bool:
    """Heuristic: zero USD value but large nominal amount → likely fake/spoofed token."""
    return (t.get("historicalUSD") or 0) == 0 and (t.get("unitValue") or 0) > 100


def _addr(obj: Optional[dict]) -> str:
    return (obj or {}).get("address") or ""


def _entity_name(obj: Optional[dict]) -> Optional[str]:
    return ((obj or {}).get("arkhamEntity") or {}).get("name")


# ---------------------------------------------------------------------------
# Compact transfer format  (~65% token reduction vs raw)
# ---------------------------------------------------------------------------

def compact_transfer(t: dict) -> dict:
    tx = t.get("transactionHash") or ""
    short_tx = (tx[:10] + "…" + tx[-6:]) if len(tx) > 16 else tx
    return {
        "time":        t.get("blockTimestamp", "")[:16],
        "from":        _addr(t.get("fromAddress")),
        "from_entity": _entity_name(t.get("fromAddress")),
        "to":          _addr(t.get("toAddress")),
        "to_entity":   _entity_name(t.get("toAddress")),
        "token":       (t.get("tokenSymbol") or "").strip(),
        "amount":      t.get("unitValue", 0),
        "usd":         t.get("historicalUSD", 0),
        "fake":        _is_fake_token(t),
        "chain":       t.get("chain"),
        "tx":          short_tx,
    }


def meta_from_transfers(transfers: list[dict]) -> dict:
    """Compute _meta summary from raw transfer records."""
    if not transfers:
        return {"returned": 0}

    fake_count = sum(1 for t in transfers if _is_fake_token(t))

    senders:   set[str] = set()
    receivers: set[str] = set()
    identified = 0
    total_sides = 0
    token_counts: Counter = Counter()

    for t in transfers:
        fa = t.get("fromAddress") or {}
        ta = t.get("toAddress") or {}
        for side in (fa, ta):
            addr = side.get("address")
            if addr:
                total_sides += 1
                if (side.get("arkhamEntity") or {}).get("name"):
                    identified += 1
        if fa.get("address"):
            senders.add(fa["address"])
        if ta.get("address"):
            receivers.add(ta["address"])
        tok = (t.get("tokenSymbol") or "").strip()
        if tok:
            token_counts[tok] += 1

    timestamps = _parse_timestamps(transfers)
    span = round((max(timestamps) - min(timestamps)) / 3600, 2) if len(timestamps) >= 2 else 0

    return {
        "returned":          len(transfers),
        "fake_token_count":  fake_count,
        "identified_pct":    round(identified / total_sides * 100, 1) if total_sides else 0,
        "time_span_hours":   span,
        "unique_senders":    len(senders),
        "unique_receivers":  len(receivers),
        "top_token":         token_counts.most_common(1)[0][0] if token_counts else None,
    }


# ---------------------------------------------------------------------------
# Statistical helpers for pattern analysis
# ---------------------------------------------------------------------------

def _parse_timestamps(transfers: list[dict]) -> list[float]:
    """Parse blockTimestamp ISO strings to Unix epoch seconds."""
    result = []
    for t in transfers:
        ts = t.get("blockTimestamp") or ""
        if ts:
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                result.append(dt.timestamp())
            except (ValueError, TypeError):
                pass
    return sorted(result)


def timing_stats(transfers: list[dict]) -> dict:
    timestamps = _parse_timestamps(transfers)
    if len(timestamps) < 2:
        return {
            "count": len(timestamps),
            "span_hours": 0,
            "mean_interval_sec": None,
            "regularity_score": None,
            "burst_windows": [],
            "peak_hours_utc": [],
        }

    intervals = [timestamps[i + 1] - timestamps[i] for i in range(len(timestamps) - 1)]
    mean_iv = sum(intervals) / len(intervals)
    std_iv = (sum((x - mean_iv) ** 2 for x in intervals) / len(intervals)) ** 0.5
    cv = std_iv / mean_iv if mean_iv > 0 else 0
    # Low CV → regular timing → bot-like → high regularity_score
    regularity = round(max(0.0, 1.0 - min(cv, 2.0) / 2.0), 3)

    # Burst detection: ≥5 txs within 60 sec
    bursts: list[dict] = []
    for i, ts in enumerate(timestamps):
        count = sum(1 for t2 in timestamps if ts <= t2 <= ts + 60)
        if count >= 5:
            if not bursts or ts > bursts[-1]["start_epoch"] + 60:
                bursts.append({"start_epoch": ts, "tx_count": count})
    burst_out = [
        {"start": datetime.fromtimestamp(b["start_epoch"], tz=timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
         "tx_count": b["tx_count"]}
        for b in bursts[:5]
    ]

    # Peak hours
    hour_counts: Counter = Counter(
        datetime.fromtimestamp(ts, tz=timezone.utc).hour for ts in timestamps
    )
    peak_hours = [h for h, _ in hour_counts.most_common(3)]

    return {
        "count":            len(timestamps),
        "span_hours":       round((timestamps[-1] - timestamps[0]) / 3600, 2),
        "mean_interval_sec": round(mean_iv, 1),
        "regularity_score": regularity,
        "burst_windows":    burst_out,
        "peak_hours_utc":   peak_hours,
    }


def amount_stats(transfers: list[dict]) -> dict:
    values = [t.get("historicalUSD") or 0 for t in transfers]
    non_zero = [v for v in values if v > 0]
    if not non_zero:
        return {"all_zero_usd": True, "count": len(values)}

    n = len(non_zero)
    s = sorted(non_zero)
    mean = sum(s) / n
    std = (sum((x - mean) ** 2 for x in s) / n) ** 0.5
    median = s[n // 2]

    # Round-number heuristic: ≤1% deviation from a round multiple
    round_thresholds = [100, 500, 1000, 5000, 10000]
    round_count = sum(
        1 for v in non_zero
        if any(t > 0 and abs(v % t) / t < 0.01 for t in round_thresholds)
    )

    # Identical-amount cluster: bin to nearest 1% of mean
    bin_size = max(mean * 0.01, 1)
    bins: Counter = Counter(round(v / bin_size) for v in non_zero)
    top_bin_count = bins.most_common(1)[0][1]

    return {
        "count":                n,
        "min_usd":              round(min(s), 2),
        "max_usd":              round(max(s), 2),
        "mean_usd":             round(mean, 2),
        "median_usd":           round(median, 2),
        "std_usd":              round(std, 2),
        "round_number_pct":     round(round_count / n * 100, 1),
        "identical_amount_pct": round(top_bin_count / n * 100, 1),
    }


def counterparty_stats(transfers: list[dict], pivot: Optional[str] = None) -> dict:
    pivot_lower = (pivot or "").lower()

    senders:   Counter = Counter()
    receivers: Counter = Counter()
    sender_usd:   dict[str, float] = {}
    receiver_usd: dict[str, float] = {}

    for t in transfers:
        fa   = _addr(t.get("fromAddress"))
        ta   = _addr(t.get("toAddress"))
        usd  = t.get("historicalUSD") or 0

        if fa:
            senders[fa] += 1
            sender_usd[fa] = sender_usd.get(fa, 0) + usd
        if ta:
            receivers[ta] += 1
            receiver_usd[ta] = receiver_usd.get(ta, 0) + usd

    total_usd = sum(t.get("historicalUSD") or 0 for t in transfers)
    overlap   = set(senders) & set(receivers)

    top_s = senders.most_common(1)[0] if senders else (None, 0)
    top_r = receivers.most_common(1)[0] if receivers else (None, 0)
    top_s_usd = sender_usd.get(top_s[0], 0) if top_s[0] else 0

    # Net-flow ratio if pivot given
    net_flow_pct = None
    if pivot_lower:
        inflow  = sum(t.get("historicalUSD") or 0 for t in transfers if _addr(t.get("toAddress")).lower()   == pivot_lower)
        outflow = sum(t.get("historicalUSD") or 0 for t in transfers if _addr(t.get("fromAddress")).lower() == pivot_lower)
        total_pv = inflow + outflow
        net_flow_pct = round(abs(inflow - outflow) / total_pv * 100, 1) if total_pv else None

    total_addrs = len(set(senders) | set(receivers))
    return {
        "unique_senders":               len(senders),
        "unique_receivers":             len(receivers),
        "sender_receiver_overlap_pct":  round(len(overlap) / total_addrs * 100, 1) if total_addrs else 0,
        "top_sender":                   top_s[0],
        "top_sender_concentration_pct": round(top_s_usd / total_usd * 100, 1) if total_usd else 0,
        "top_receiver":                 top_r[0],
        "net_flow_pct":                 net_flow_pct,
    }


def classify_pattern(
    timing:  dict,
    amounts: dict,
    cp:      dict,
    fake_count: int,
    total:   int,
) -> tuple[str, float, list[str]]:
    """Return (pattern_name, confidence 0-1, signals list)."""
    scores:  dict[str, float] = {}
    signals: list[str] = []

    reg = timing.get("regularity_score") or 0.0
    if reg > 0.75:
        signals.append(f"Timing regularity score {reg:.2f} (>0.75 = bot-like intervals)")
        scores["bot_market_maker"] = scores.get("bot_market_maker", 0) + 0.40

    bursts = len(timing.get("burst_windows") or [])
    if bursts >= 3:
        signals.append(f"{bursts} burst windows detected (≥5 txs/60 sec)")
        scores["bot_market_maker"] = scores.get("bot_market_maker", 0) + 0.20

    ident_pct = amounts.get("identical_amount_pct") or 0
    if ident_pct > 60:
        signals.append(f"{ident_pct}% of transfers share the same amount (bot pattern)")
        scores["bot_market_maker"] = scores.get("bot_market_maker", 0) + 0.25

    overlap = cp.get("sender_receiver_overlap_pct") or 0
    if overlap > 30:
        signals.append(f"{overlap}% of addresses appear on both sides of trades (wash trading)")
        scores["wash_trading"] = scores.get("wash_trading", 0) + 0.50

    nfp = cp.get("net_flow_pct")
    if nfp is not None and nfp < 10:
        signals.append("Net flow near zero — funds cycling back (wash trading)")
        scores["wash_trading"] = scores.get("wash_trading", 0) + 0.30

    ur = cp.get("unique_receivers") or 0
    if ur > 20 and ident_pct > 35:
        signals.append(f"Fan-out to {ur} receivers with similar amounts (layered disbursement)")
        scores["layered_disbursement"] = scores.get("layered_disbursement", 0) + 0.55

    if fake_count > 3:
        signals.append(f"{fake_count} fake-token transfers (historicalUSD=0, large nominal value)")
        scores["dust_attack"] = scores.get("dust_attack", 0) + 0.60

    rnd = amounts.get("round_number_pct") or 0
    if rnd > 70:
        signals.append(f"{rnd}% of transfers are round numbers")

    top_conc = cp.get("top_sender_concentration_pct") or 0
    if top_conc > 70:
        signals.append(f"Single sender controls {top_conc}% of volume")

    if not scores:
        return "normal_trading", 0.5, signals or ["No significant anomalies detected"]

    top = max(scores, key=lambda k: scores[k])
    return top, round(min(scores[top], 1.0), 2), signals
