"""Robustness checks for the volume -> NEAR price link (written into metrics.json["robustness"]).

The naive test (metrics.flow_vs_price) correlates weekly NEAR returns with weekly changes
in Intents volume. Two things can fake that link:

1. Market beta. When crypto rallies, NEAR rises AND people swap more. Both move with BTC/ETH.
   Control: regress NEAR weekly log return on a crypto market factor (mean of BTC and ETH weekly
   log returns; BTC+ETH as two factors is reported too) plus the volume
   change, and test the volume coefficient (OLS with Newey-West standard errors, lag 2).
   Also correlate the volume change with NEAR's *residual* (market-adjusted) return.
2. Tiny early weeks. Intents volume in Dec 2024 - Jan 2025 was ~$1M/week, so a $1M -> $3M
   week is a +110% log change that dominates the sample. Control: drop weeks below a volume
   floor and re-run.

Plus rolling 26-week windows, to show whether any link is stable or one regime.
Pure standard library; no numpy needed.
"""
import math

ROLL_WEEKS = 26
NW_LAG = 2
VOLUME_FLOORS = [0, 25e6, 100e6]  # USD per week
ETF_CUTOFF = "2026-09-14"  # Bitwise NEAR ETF: amended S-1 2026-09-16, Form 8-A 2026-09-24, listed late Sep 2026


# ---------- tiny linear algebra ----------
def _transpose(m):
    return [list(r) for r in zip(*m)]


def _matmul(a, b):
    bt = _transpose(b)
    return [[sum(x * y for x, y in zip(r, c)) for c in bt] for r in a]


def _inv(m):
    n = len(m)
    a = [list(r) + [1.0 if i == j else 0.0 for j in range(n)] for i, r in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        if abs(a[p][c]) < 1e-15:
            raise ValueError("singular matrix")
        a[c], a[p] = a[p], a[c]
        piv = a[c][c]
        a[c] = [v / piv for v in a[c]]
        for r in range(n):
            if r != c and a[r][c]:
                f = a[r][c]
                a[r] = [v - f * w for v, w in zip(a[r], a[c])]
    return [r[n:] for r in a]


def ols(y, X, names, nw_lag=NW_LAG):
    """OLS with an intercept. Returns coefficients, plain and Newey-West (HAC) t-stats, R^2."""
    n = len(y)
    Xc = [[1.0] + list(r) for r in X]
    k = len(Xc[0])
    if n <= k + 2:
        return None
    XtX_inv = _inv(_matmul(_transpose(Xc), Xc))
    Xty = [[sum(Xc[i][j] * y[i] for i in range(n))] for j in range(k)]
    beta = [b[0] for b in _matmul(XtX_inv, Xty)]
    resid = [y[i] - sum(beta[j] * Xc[i][j] for j in range(k)) for i in range(n)]
    ybar = sum(y) / n
    sst = sum((v - ybar) ** 2 for v in y)
    sse = sum(e * e for e in resid)
    s2 = sse / (n - k)
    se_plain = [math.sqrt(s2 * XtX_inv[j][j]) for j in range(k)]
    # Newey-West: S = sum_l w_l sum_t e_t e_{t-l} (x_t x_{t-l}' + x_{t-l} x_t')
    S = [[0.0] * k for _ in range(k)]
    for t in range(n):
        for a in range(k):
            for b in range(k):
                S[a][b] += resid[t] ** 2 * Xc[t][a] * Xc[t][b]
    for lag in range(1, nw_lag + 1):
        w = 1 - lag / (nw_lag + 1)
        for t in range(lag, n):
            e = resid[t] * resid[t - lag]
            for a in range(k):
                for b in range(k):
                    S[a][b] += w * e * (Xc[t][a] * Xc[t - lag][b] + Xc[t - lag][a] * Xc[t][b])
    V = _matmul(_matmul(XtX_inv, S), XtX_inv)
    se_nw = [math.sqrt(max(V[j][j], 0)) for j in range(k)]
    cols = ["intercept", *names]
    return {
        "n": n,
        "r2": 1 - sse / sst if sst else None,
        "coef": dict(zip(cols, beta)),
        "t_plain": {c: (b / s if s else None) for c, b, s in zip(cols, beta, se_plain)},
        "t_newey_west": {c: (b / s if s else None) for c, b, s in zip(cols, beta, se_nw)},
        "residuals": resid,
    }


def _corr(xs, ys):
    n = len(xs)
    if n < 8:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy) if sx and sy else None


def returns_table(weeks):
    """Weekly log changes for NEAR, BTC, ETH and Intents volume, keyed by the later week."""
    out = []
    for a, b in zip(weeks, weeks[1:]):
        vals = {}
        ok = True
        for k in ("price", "btc", "eth", "volume"):
            if not (a.get(k) and b.get(k) and a[k] > 0 and b[k] > 0):
                ok = False
                break
            vals[k] = math.log(b[k] / a[k])
        if ok:
            out.append({"week": b["week"], "prev_volume": a["volume"], "volume_level": b["volume"],
                        "near": vals["price"], "btc": vals["btc"], "eth": vals["eth"], "dvol": vals["volume"],
                        "mkt": (vals["btc"] + vals["eth"]) / 2})
    return out


def test_sample(rows, label):
    """Primary control: one equal-weight crypto factor mkt = (BTC + ETH)/2 (BTC and ETH weekly returns
    are ~0.8 correlated, so putting both in one regression makes their individual betas unstable).
    The BTC+ETH two-factor version is reported alongside."""
    if len(rows) < 12:
        return {"label": label, "n_weeks": len(rows), "note": "too few weeks"}
    y = [r["near"] for r in rows]
    naive = ols(y, [[r["dvol"]] for r in rows], ["dvol"])
    market = ols(y, [[r["mkt"]] for r in rows], ["mkt"])
    full = ols(y, [[r["mkt"], r["dvol"]] for r in rows], ["mkt", "dvol"])
    two = ols(y, [[r["btc"], r["eth"], r["dvol"]] for r in rows], ["btc", "eth", "dvol"])
    resid_corr = _corr([r["dvol"] for r in rows], market["residuals"]) if market else None
    strip = lambda m: {k: v for k, v in m.items() if k != "residuals"} if m else None  # noqa: E731
    return {
        "label": label,
        "first_week": rows[0]["week"],
        "last_week": rows[-1]["week"],
        "n_weeks": len(rows),
        "naive_corr_dvol_near": _corr([r["dvol"] for r in rows], y),
        "market_beta": market["coef"]["mkt"] if market else None,
        "market_model_r2": market["r2"] if market else None,
        "corr_dvol_vs_market_adjusted_near": resid_corr,
        "dvol_coef_controlled": full["coef"]["dvol"] if full else None,
        "dvol_t_newey_west_controlled": full["t_newey_west"]["dvol"] if full else None,
        "dvol_t_newey_west_btc_eth": two["t_newey_west"]["dvol"] if two else None,
        "corr_dvol_vs_market": _corr([r["dvol"] for r in rows], [r["mkt"] for r in rows]),
        "naive_regression": strip(naive),
        "controlled_regression": strip(full),
        "controlled_regression_btc_eth": strip(two),
    }


def rolling(rows, window=ROLL_WEEKS):
    out = []
    for i in range(window, len(rows) + 1):
        w = rows[i - window:i]
        y = [r["near"] for r in w]
        market = ols(y, [[r["mkt"]] for r in w], ["mkt"])
        full = ols(y, [[r["mkt"], r["dvol"]] for r in w], ["mkt", "dvol"])
        out.append({
            "week_end": w[-1]["week"],
            "naive_corr": _corr([r["dvol"] for r in w], y),
            "market_adjusted_corr": _corr([r["dvol"] for r in w], market["residuals"]) if market else None,
            "dvol_t_nw": full["t_newey_west"]["dvol"] if full else None,
            "market_beta": market["coef"]["mkt"] if market else None,
        })
    return out


def build(weeks, buyback_start):
    rows = returns_table(weeks)
    samples = []
    for floor in VOLUME_FLOORS:
        kept = [r for r in rows if r["prev_volume"] >= floor and r["volume_level"] >= floor]
        samples.append(test_sample(kept, f"all weeks, volume >= ${floor/1e6:,.0f}M/week"))
    post = [r for r in rows if r["week"] >= buyback_start]
    pre = [r for r in rows if r["week"] < buyback_start and r["prev_volume"] >= VOLUME_FLOORS[1]]
    samples.append(test_sample(pre, f"pre-buyback (< {buyback_start}), volume >= $25M/week"))
    samples.append(test_sample(post, f"post-buyback (>= {buyback_start})"))
    pre_etf = [r for r in post if r["week"] < ETF_CUTOFF]
    samples.append(test_sample(pre_etf, f"post-buyback, before NEAR ETF listing ({buyback_start} .. {ETF_CUTOFF})"))
    return {
        "method": "Weekly log returns. controlled_regression: NEAR = a + b1*MKT + b2*dVolume with MKT = (BTC+ETH)/2; "
                  f"t-stats with Newey-West HAC errors (lag {NW_LAG}). market-adjusted corr = corr(dVolume, "
                  "residual of NEAR on MKT). controlled_regression_btc_eth uses BTC and ETH separately.",
        "samples": samples,
        "rolling_window_weeks": ROLL_WEEKS,
        "rolling": rolling(rows),
    }
