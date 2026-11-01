# Does NEAR Intents' cross-chain volume accrue value to the NEAR token?

An investment-thesis project for the NEAR HACKATHON 2026, **Investment Thesis** track (`thesis`).
Track hints used: ONCHAIN DATA, DASHBOARDS, RESEARCH, NEAR INTENTS.

**What it is:** a reproducible data pipeline, a static dashboard and an editable bear/base/bull model
that follow every dollar of NEAR Intents swap volume down the value-capture chain and measure how much
of it reaches $NEAR holders.

**The problem:** "Intents volume is booming, so NEAR should go up" is the common claim. It is rarely
checked. Volume only matters to the token if it turns into fees, the fees are captured by NEAR, and the
captured money reaches holders (since 2026-02-23 it buys back $NEAR on the open market). This project
measures each step and lets anyone re-run it.

```
Intents volume ──► fees ──► NEAR captured revenue ──► $NEAR buyback ──► NEAR price / market cap
```

> Snapshot: data fetched 2026-11-01 06:16 UTC, Intents data through 2026-10-31. Full write-up with every
> table: [`FINDINGS.md`](FINDINGS.md).

## Answer (for a reader in a hurry)

**Yes, value accrues through a real mechanism, but it is too small to explain NEAR's price, and the
price link is not statistically robust once crypto-market moves are controlled for.**

| Step | Last 30 days | Ratio |
| --- | --- | --- |
| Intents swap volume | $3.86B | — |
| Fees (protocol + affiliate) | $5.75M | 0.149% of volume |
| NEAR captured revenue | $2.12M | 36.9% of fees, 0.055% of volume |
| $NEAR buyback | $2.12M | 100% of captured revenue |
| Annualized buyback vs NEAR market cap ($5.77B) | $25.8M / yr | **0.45% of market cap per year** |

- Buybacks since 2026-02-23: $7.52M, ≈3.15M NEAR (≈0.25% of circulating supply). Bought NEAR is held, not burned.
- New supply: at the 2.5% max issuance rate ≈ $144M/yr of new NEAR, so buybacks offset ≈ **0.18x** of issuance.
- Valuation: NEAR trades at ≈ **224x** its annual buyback; Hyperliquid 26x, Jupiter 37x, pump.fun 6x (computed live).
- Price link (weekly, controlled for a BTC/ETH market factor, Newey-West t): none before the buyback
  (t = 1.02), positive after it (coefficient 0.215, **t = 1.73**, 35 weeks), weaker again without the
  Sep-Oct 2026 ETF rally (t = 1.06). A naive uncontrolled test shows t = 2.15; it does not hold up.
- Model: Intents buybacks justify **0.4% (bear), 8.7% (base), 33.5% (bull)** of today's market cap.

## Run it — "do X, see Y"

Requires Python 3.10+ and PyYAML (`pip install -r requirements.txt`). No API keys.

| Do | See |
| --- | --- |
| `python3 -m pipeline build` | Rebuilds every number **offline** from the committed snapshots in `data/raw/`. Prints `692 days`, `97 full weeks` and the three scenarios: bear $0.017, base $0.403, bull $1.549 of value per NEAR, with buyback ÷ issuance 0.03x / 0.13x / 0.36x. |
| `python3 -m unittest discover -s tests -v` | 13 tests pass: snapshot hashes, source shapes, units (yocto→NEAR), BTC/ETH controls loaded, take rates, model formula, scenario order, issuance math, comparables, robustness samples, and the OLS / Newey-West code checked against `statistics.linear_regression` and a simulated regression. |
| `cd docs && python3 -m http.server 8000`, open http://localhost:8000 | The dashboard: headline tiles, value-capture chain, volume vs price, fees/revenue/buyback, lag correlations, the **robustness table and rolling 26-week chart**, buybacks vs issuance and comparables, an **editable** bear/base/bull table, caveats, provenance. Opening `docs/index.html` directly also works (data is bundled in `docs/data.js`; charts need internet for the Chart.js CDN). |
| Open `data/processed/metrics.json`, key `robustness.samples` | One entry per sample: weeks, raw and market-adjusted correlation, controlled volume coefficient, Newey-West t, plus full regressions. |
| Edit `model/assumptions.yaml`, then `python3 -m pipeline model` | New scenario values in the terminal, `data/processed/model.json` and the dashboard. |
| `python3 -m pipeline all` | Fetches fresh data from the live APIs (needs internet), re-snapshots `data/raw/`, rebuilds everything. Numbers will differ from the snapshot above. |

`make build`, `make test`, `make serve`, `make all` are shortcuts.

## Repository map

| Path | What |
| --- | --- |
| `pipeline/sources.py` | Every endpoint used, with provider and meaning |
| `pipeline/fetch.py` | Downloads raw responses → `data/raw/*.json` + `manifest.json` (URL, UTC time, HTTP status, SHA-256) |
| `pipeline/clean.py` | Merges all series into one UTC-daily table → `data/processed/daily.json` |
| `pipeline/metrics.py` | Windows, take rates, buyback yield, weekly correlations, lags, regression → `metrics.json` |
| `pipeline/robustness.py` | Market-factor control, Newey-West OLS (pure stdlib), volume floors, pre/post buyback and pre-ETF samples, rolling 26-week windows |
| `FINDINGS.md` | The full write-up: verdict, robustness table, scenarios, what would change the verdict |
| `pipeline/model.py` + `model/assumptions.yaml` | Bear/base/bull model → `model.json` |
| `docs/index.html` + `docs/data.js` | Static dashboard (GitHub Pages ready) |
| `tests/` | Offline tests |

## Data provenance

All sources are public and keyless. Raw responses are committed unmodified (re-serialized as compact
sorted JSON) with SHA-256 hashes in `data/raw/manifest.json`.

| Series | Endpoint | Provider |
| --- | --- | --- |
| Intents daily volume | https://api.llama.fi/summary/dexs/near-intents | DefiLlama |
| Intents daily fees | https://api.llama.fi/summary/fees/near-intents?dataType=dailyFees | DefiLlama |
| NEAR captured revenue | https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue | DefiLlama |
| $NEAR buyback ("holders revenue") | https://api.llama.fi/summary/fees/near-intents?dataType=dailyHoldersRevenue | DefiLlama |
| NEAR price, daily | https://coins.llama.fi/chart/coingecko:near (500-day windows from 2024-12-01) | DefiLlama coins / CoinGecko |
| NEAR supply, market cap, txns | https://api.nearblocks.io/v1/stats | NearBlocks |
| NEAR chain TVL | https://api.llama.fi/v2/historicalChainTvl/Near | DefiLlama |
| BTC, ETH price, daily (market control) | https://coins.llama.fi/chart/coingecko:bitcoin , …/coingecko:ethereum | DefiLlama coins / CoinGecko |
| Comparable market caps | POST https://coins.llama.fi/mcaps (hyperliquid, pump-fun, jupiter-exchange-solana) | DefiLlama coins |
| Comparable buybacks | https://api.llama.fi/summary/fees/{hyperliquid,pump.fun,jupiter}?dataType=dailyHoldersRevenue | DefiLlama |

Scenario assumptions cite their sources inline in `model/assumptions.yaml` (NEAR Foundation tokenomics
and Q2 2026 posts, the NEAR Intents fee schedule, issuance figures reported in Oct 2026, and the live
comparables above).

Definitions come from the DefiLlama adapter methodology
(https://github.com/DefiLlama/dimension-adapters/blob/master/fees/near-intents):
*Fees* are gross protocol + affiliate fees; *Revenue* is NEAR/wNEAR swept into NEAR's revenue wallets
(reconciles with revenue.near.org); *Holders revenue* is captured revenue used since 2026-02-23 to buy
back $NEAR on the open market (not burned).

## Method

- All series keyed by UTC date; nothing interpolated. Analysis starts with the first Intents data (2024-12-10).
- Windows (7/30/90/365 days, all-time) end on the last day with volume data.
- Correlations use **weekly log changes**, not levels (two trending series always correlate in levels; the
  level correlation is reported but labelled `SPURIOUS_RISK`). Lags −4…+4 weeks; positive = volume leads price.
- Robustness: `NEAR = a + b1·MKT + b2·ΔVolume` with MKT = mean of BTC and ETH weekly log returns (BTC and ETH
  as two separate factors is reported too); Newey-West HAC standard errors, lag 2. Samples: all weeks,
  weeks with ≥ $25M and ≥ $100M volume, pre-buyback, post-buyback, post-buyback before the NEAR ETF
  listing (cut 2026-09-14). Rolling 26-week windows.
- Prices are snapped to the nearest UTC midnight (coins.llama.fi stamps land a few seconds either side).
- Issuance: max annual rate (2.5%) × total supply × price, an upper bound on new supply.
- Model: `value_supported = annual_volume × (1 + growth) × take_rate × take_rate_multiplier × buyback_share × multiple`,
  baseline from data (30-day volume run-rate, 90-day captured/volume take rate, 90-day buyback share).

## Limitations

- Correlation is not causation. Only BTC/ETH market beta is controlled; the AI-token narrative, ETF
  flows and treasury-company buying are not.
- Short sample: 35 weekly observations since the buyback.
- Revenue is recorded when swept, so a single day's revenue can exceed that day's fees.
- Market cap, supply and comparable multiples are single snapshots at fetch time.
- Data quality depends on DefiLlama's adapters; volume is not re-derived from chain data.

## Built with

Python standard library (urllib, json, statistics), PyYAML, Chart.js 4 (CDN). Code written with an AI
assistant (Hark) during the hackathon window. No pre-hackathon code. License: MIT (see `LICENSE`).
