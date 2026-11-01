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

> Status: work in progress (built 2026-11-01 → 2026-11-15). Numbers below are from the committed
> snapshot fetched 2026-11-01T00:17:47+00:00, data through 2026-10-30.

## Preliminary findings (snapshot of 2026-11-01)

| Step | Last 30 days | Ratio |
| --- | --- | --- |
| Intents swap volume | $3.91B | — |
| Fees (protocol + affiliate) | $5.94M | 0.152% of volume |
| NEAR captured revenue | $2.15M | 36% of fees, 0.055% of volume |
| $NEAR buyback | $2.15M | 100% of captured revenue |
| Annualized buyback vs NEAR market cap ($5.79B) | $26.1M / yr | **0.45% of market cap per year** |

- Since the buyback started (2026-02-23): ≈$7.47M spent, ≈2.92M NEAR bought (≈0.23% of circulating supply;
  approximate, valued at each day's price).
- Weekly volume growth vs NEAR weekly return: correlation **0.04** over all 96 weeks (t = 0.35, no signal);
  **−0.03** before the buyback (61 weeks) but **0.41** since it began (34 weeks, t = 2.56). Not yet controlled
  for BTC/ETH market moves, so this is a lead, not a conclusion.
- Model: at today's run-rate, Intents buybacks alone justify ≈0.6% (bear), 8.4% (base) and 44% (bull) of
  NEAR's current market cap.

Preliminary reading: value now **does** flow from Intents to the token through a real mechanism (buybacks),
but at today's scale it is small relative to market cap. A final verdict will be written once the
market-beta control and robustness checks are in.

## Run it — "do X, see Y"

Requires Python 3.10+ and PyYAML (`pip install -r requirements.txt`). No API keys.

| Do | See |
| --- | --- |
| `python3 -m pipeline build` | Rebuilds every number **offline** from the committed snapshots in `data/raw/`. Prints days covered, weeks analysed and the three model scenarios (bear ≈ $0.03, base ≈ $0.39, bull ≈ $2.05 of value per NEAR). |
| `python3 -m unittest discover -s tests -v` | 7 tests pass: snapshot hashes match the manifest, source shapes, units (yocto→NEAR), take rates are fractions, model formula, scenario order. |
| `cd docs && python3 -m http.server 8000`, open http://localhost:8000 | The dashboard: headline tiles, the value-capture chain, volume vs price, fees/revenue/buyback, lag correlations, an **editable** bear/base/bull table, caveats, provenance. Opening `docs/index.html` directly also works (data is bundled in `docs/data.js`; charts need internet for the Chart.js CDN). |
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
- Model: `value_supported = annual_volume × (1 + growth) × take_rate × take_rate_multiplier × buyback_share × multiple`,
  baseline from data (30-day volume run-rate, 90-day captured/volume take rate, 90-day buyback share).

## Limitations

- No control yet for crypto-wide market moves (BTC/ETH beta); planned.
- Short sample: 34 weekly observations since the buyback; t ≈ 2.5 is suggestive, not conclusive.
- Revenue is recorded when swept, so a single day's revenue can exceed that day's fees.
- Market cap and supply are a single snapshot at fetch time.
- Data quality depends on DefiLlama's adapter; we do not re-derive volume from chain data.

## Built with

Python standard library (urllib, json, statistics), PyYAML, Chart.js 4 (CDN). Code written with an AI
assistant (Hark) during the hackathon window. No pre-hackathon code. License: MIT (see `LICENSE`).
