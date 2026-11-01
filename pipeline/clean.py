"""Turn raw snapshots into one merged daily dataset (data/processed/daily.json).

Rules:
- Every series is keyed by UTC calendar date (YYYY-MM-DD).
- DefiLlama dimension charts are [unix_ts, value] pairs at 00:00 UTC.
- coins.llama.fi prices carry a timestamp a few seconds before or after midnight; they
  are snapped to the nearest UTC midnight (flooring would merge two days and leave gaps).
- NearBlocks supplies are in yoctoNEAR (1 NEAR = 1e24 yocto) and are converted to NEAR.
- Nothing is interpolated. A missing value stays null.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

DIMENSION_SERIES = {
    "volume": "intents_volume",
    "fees": "intents_fees",
    "revenue": "intents_revenue",
    "holders_revenue": "intents_holders_revenue",
}
YOCTO = 10 ** 24


def day(ts):
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d")


def load(name):
    return json.loads((RAW / f"{name}.json").read_text())


def dimension_series(raw):
    return {day(ts): float(v) for ts, v in raw.get("totalDataChart", [])}


def price_series(raw, coin="coingecko:near"):
    chunks = raw["chunks"] if "chunks" in raw else [raw]
    out = {}
    for c in chunks:
        for p in c.get("coins", {}).get(coin, {}).get("prices", []):
            # snap to the NEAREST UTC midnight: points land a few seconds either side of 00:00
            out[day(int(p["timestamp"]) + 43200)] = float(p["price"])
    return out


def tvl_series(raw):
    return {day(r["date"]): float(r["tvl"]) for r in raw}


def current_stats(raw):
    s = raw["stats"][0]
    return {
        "near_price_usd": float(s["near_price"]),
        "market_cap_usd": float(s["market_cap"]),
        "total_supply_near": int(s["total_supply"]) / YOCTO,
        "circulating_supply_near": int(s["circulating_supply"]) / YOCTO,
        "total_txns": int(s["total_txns"]),
        "tps": s.get("tps"),
        "nodes_online": s.get("nodes_online"),
        "volume_24h_usd": float(s["volume"]),
        "change_24h_pct": float(s["change_24"]),
    }


def comparables():
    """Market cap / annualized (30d x 365/30) holders revenue for tokens with fee-funded buybacks."""
    from .sources import SOURCES
    mcaps = load("comparables_mcap")
    fetched_day = json.loads((RAW / "manifest.json").read_text())["fetched_at_utc"][:10]
    out = []
    for name, src in SOURCES.items():
        if not name.startswith("comp_"):
            continue
        raw = load(name)
        # drop the fetch day itself: it is a partial day
        chart = [p for p in sorted(raw.get("totalDataChart", [])) if day(p[0]) < fetched_day]
        last30 = sum(float(v) for _, v in chart[-30:])
        mcap = float(mcaps[src["gecko"]]["mcap"])
        ann = last30 * 365 / 30
        out.append({
            "token": raw.get("name"),
            "gecko_id": src["gecko"],
            "market_cap_usd": mcap,
            "holders_revenue_30d_usd": last30,
            "annualized_holders_revenue_usd": ann,
            "mcap_to_annual_buyback": mcap / ann if ann else None,
            "last_day": day(chart[-1][0]) if chart else None,
        })
    return out


def build():
    series = {k: dimension_series(load(v)) for k, v in DIMENSION_SERIES.items()}
    series["price"] = price_series(load("near_price"))
    series["tvl"] = tvl_series(load("near_chain_tvl"))
    series["btc"] = price_series(load("btc_price"), "coingecko:bitcoin")
    series["eth"] = price_series(load("eth_price"), "coingecko:ethereum")

    start = min(series["volume"])  # analysis window starts with Intents data
    dates = sorted(d for d in set().union(*[set(s) for s in series.values()]) if d >= start)
    rows = [{"date": d, **{k: series[k].get(d) for k in series}} for d in dates]

    manifest = json.loads((RAW / "manifest.json").read_text())
    out = {
        "fetched_at_utc": manifest["fetched_at_utc"],
        "columns": ["date", *series.keys()],
        "units": {
            "volume": "USD/day", "fees": "USD/day", "revenue": "USD/day",
            "holders_revenue": "USD/day", "price": "USD", "tvl": "USD",
            "btc": "USD", "eth": "USD",
        },
        "rows": rows,
        "current": current_stats(load("nearblocks_stats")),
        "comparables": comparables(),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "daily.json").write_text(json.dumps(out, indent=1))
    print(f"  daily.json: {len(rows)} days, {rows[0]['date']} .. {rows[-1]['date']}")
    return out
