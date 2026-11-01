"""Core metrics for the value-capture chain (data/processed/metrics.json).

Chain under test:
  Intents volume -> fees -> NEAR captured revenue -> $NEAR buyback -> NEAR price / market cap

Everything here is descriptive. Correlations are computed on weekly log changes
(not levels) to avoid the spurious correlation two trending series always show;
level correlations are reported too, but flagged.
"""
import json
import math
import statistics as st
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"
BUYBACK_START = "2026-02-23"  # per DefiLlama near-intents fees adapter methodology
LAGS = range(-4, 5)  # weeks; positive lag = Intents metric leads price


def _sum(rows, key):
    vals = [r[key] for r in rows if r.get(key) is not None]
    return sum(vals) if vals else None


def _div(a, b):
    return a / b if (a is not None and b) else None


def window(rows, end, days):
    start = (date.fromisoformat(end) - timedelta(days=days - 1)).isoformat()
    return [r for r in rows if start <= r["date"] <= end]


def weekly(rows):
    """Sum flows and take the last price/TVL per ISO week (Mon-Sun). Only full weeks."""
    weeks = {}
    for r in rows:
        d = date.fromisoformat(r["date"])
        wk = (d - timedelta(days=d.weekday())).isoformat()
        weeks.setdefault(wk, []).append(r)
    out = []
    for wk, rs in sorted(weeks.items()):
        if len(rs) < 7 or any(r.get("volume") is None for r in rs):
            continue
        out.append({
            "week": wk,
            "volume": _sum(rs, "volume"),
            "fees": _sum(rs, "fees"),
            "revenue": _sum(rs, "revenue"),
            "holders_revenue": _sum(rs, "holders_revenue"),
            "price": next((r["price"] for r in reversed(rs) if r.get("price")), None),
            "tvl": next((r["tvl"] for r in reversed(rs) if r.get("tvl")), None),
        })
    return out


def monthly(rows):
    m = {}
    for r in rows:
        m.setdefault(r["date"][:7], []).append(r)
    out = []
    for k, rs in sorted(m.items()):
        out.append({
            "month": k, "days": len(rs),
            "volume": _sum(rs, "volume"), "fees": _sum(rs, "fees"),
            "revenue": _sum(rs, "revenue"), "holders_revenue": _sum(rs, "holders_revenue"),
            "avg_price": _div(_sum(rs, "price"), len([r for r in rs if r.get("price")])),
        })
    return out


def logdiff(xs):
    out = []
    for a, b in zip(xs, xs[1:]):
        out.append(math.log(b / a) if (a and b and a > 0 and b > 0) else None)
    return out


def corr(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 8:
        return None, len(pairs)
    a, b = zip(*pairs)
    try:
        return st.correlation(a, b), len(pairs)
    except st.StatisticsError:
        return None, len(pairs)


def lagged(xs, ys, lag):
    """corr(x[t], y[t+lag]): positive lag means x leads y."""
    if lag >= 0:
        return corr(xs[: len(xs) - lag] if lag else xs, ys[lag:])
    return corr(xs[-lag:], ys[: len(ys) + lag])


def regression(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 8:
        return None
    a, b = zip(*pairs)
    slope, intercept = st.linear_regression(a, b)
    r = st.correlation(a, b)
    # t-stat for the slope under OLS assumptions (weekly returns are not iid: treat as indicative)
    n = len(pairs)
    t = r * math.sqrt((n - 2) / (1 - r * r)) if abs(r) < 1 else None
    return {"slope": slope, "intercept": intercept, "r": r, "r2": r * r, "n": n, "t_stat": t}


def flow_vs_price(weeks, key):
    x = logdiff([w[key] for w in weeks])
    y = logdiff([w["price"] for w in weeks])
    lc, ln = corr([math.log(w[key]) if w[key] else None for w in weeks],
                  [math.log(w["price"]) if w["price"] else None for w in weeks])
    return {
        "weekly_logchange_corr": corr(x, y)[0],
        "n_weeks": corr(x, y)[1],
        "lagged_corr": {str(l): lagged(x, y, l)[0] for l in LAGS},
        "regression_price_on_flow": regression(x, y),
        "log_level_corr_SPURIOUS_RISK": lc,
    }


def build(daily):
    rows = daily["rows"]
    cur = daily["current"]
    end = max(r["date"] for r in rows if r.get("volume") is not None)
    rows_to_end = [r for r in rows if r["date"] <= end]

    windows = {}
    for label, n in [("7d", 7), ("30d", 30), ("90d", 90), ("365d", 365)]:
        w = window(rows_to_end, end, n)
        windows[label] = {k: _sum(w, k) for k in ("volume", "fees", "revenue", "holders_revenue")}
    windows["all_time"] = {k: _sum(rows_to_end, k) for k in ("volume", "fees", "revenue", "holders_revenue")}

    take = {}
    for label, w in windows.items():
        take[label] = {
            "fees_per_volume": _div(w["fees"], w["volume"]),
            "revenue_per_volume": _div(w["revenue"], w["volume"]),
            "revenue_per_fees": _div(w["revenue"], w["fees"]),
            "buyback_per_revenue": _div(w["holders_revenue"], w["revenue"]),
        }

    mcap = cur["market_cap_usd"]
    circ = cur["circulating_supply_near"]
    w30 = windows["30d"]
    ann = lambda v: v * 365 / 30 if v is not None else None  # noqa: E731
    bb_rows = [r for r in rows_to_end if r["date"] >= BUYBACK_START]
    near_bought = sum(r["holders_revenue"] / r["price"] for r in bb_rows
                      if r.get("holders_revenue") and r.get("price"))
    value_capture = {
        "market_cap_usd": mcap,
        "circulating_supply_near": circ,
        "annualized_volume_usd_from_30d": ann(w30["volume"]),
        "annualized_fees_usd_from_30d": ann(w30["fees"]),
        "annualized_revenue_usd_from_30d": ann(w30["revenue"]),
        "annualized_buyback_usd_from_30d": ann(w30["holders_revenue"]),
        "buyback_yield_on_mcap": _div(ann(w30["holders_revenue"]), mcap),
        "price_to_annualized_revenue": _div(mcap, ann(w30["revenue"])),
        "annualized_volume_per_usd_mcap": _div(ann(w30["volume"]), mcap),
        "buyback_since": BUYBACK_START,
        "buyback_usd_since_start": _sum(bb_rows, "holders_revenue"),
        "approx_near_bought_since_start": near_bought,
        "approx_near_bought_pct_circulating": _div(near_bought, circ),
        "note": "approx_near_bought assumes each day's buyback USD was spent at that day's price; "
                "DefiLlama reports USD, not tokens.",
    }

    weeks = weekly(rows_to_end)
    pre = [w for w in weeks if w["week"] < BUYBACK_START]
    post = [w for w in weeks if w["week"] >= BUYBACK_START]
    relations = {
        "volume_vs_price": flow_vs_price(weeks, "volume"),
        "revenue_vs_price": flow_vs_price([w for w in weeks if w["revenue"]], "revenue"),
        "volume_vs_price_pre_buyback": flow_vs_price(pre, "volume"),
        "volume_vs_price_post_buyback": flow_vs_price(post, "volume"),
    }

    out = {
        "as_of_last_full_day": end,
        "fetched_at_utc": daily["fetched_at_utc"],
        "current": cur,
        "windows": windows,
        "take_rates": take,
        "value_capture": value_capture,
        "relations": relations,
        "weekly": weeks,
        "monthly": monthly(rows_to_end),
        "caveats": [
            "Correlation is not causation; NEAR price is dominated by crypto-wide beta (BTC/ETH), which is not controlled for yet.",
            "Weekly sample is short (tens of observations); a t-stat near 2 is weak evidence.",
            "DefiLlama 'revenue' is NEAR/wNEAR swept into NEAR revenue wallets; sweep timing means a day's revenue can exceed that day's fees.",
            "The buyback program began 2026-02-23; earlier captured revenue stayed in the treasury.",
            "Market cap and supply are a single NearBlocks snapshot at fetch time.",
        ],
    }
    (OUT / "metrics.json").write_text(json.dumps(out, indent=1))
    print(f"  metrics.json: as of {end}, {len(weeks)} full weeks")
    return out
