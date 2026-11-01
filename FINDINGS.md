# Findings: does NEAR Intents' cross-chain volume accrue value to the NEAR token?

Snapshot: data fetched 2026-11-01 06:16 UTC, Intents data through 2026-10-31 (UTC).
Every number below is reproduced by `python3 -m pipeline build` from the files in `data/raw/`.

## Verdict

**Yes, through a real mechanism, but so far too small to matter for the token's value, and the price
link is not statistically robust.**

1. **The mechanism is real.** Since 2026-02-23, 100% of the revenue NEAR captures from Intents buys
   $NEAR on the open market (DefiLlama methodology; NEAR Foundation tokenomics post). $7.52M has been
   spent, roughly 3.15M NEAR (~0.25% of circulating supply, valued at each day's price).
2. **The leak is large.** Of each $1,000 of Intents volume, about $1.49 is paid in fees and about $0.55
   reaches NEAR (30-day figures: $3.86B volume, $5.75M fees, $2.12M captured = 36.9% of fees).
3. **The cash flow is small next to the token.** Annualized, buybacks are $25.8M a year: 0.45% of NEAR's
   $5.77B market cap. NEAR trades at ~224x its annual buyback; comparable buyback tokens trade at 6x
   (pump.fun), 26x (Hyperliquid) and 37x (Jupiter).
4. **Buybacks do not offset new supply.** At the 2.5% maximum issuance rate, new NEAR is worth ~$144M a
   year at today's price, so buybacks cover ~0.18x of it (issuance ≈ 5.6x buybacks). Bought NEAR is held,
   not burned. This matches the "issuance runs six times higher" figure SVRN's CEO gave in Oct 2026.
5. **The price link appeared after the fee switch, but does not survive the controls at 5%.**

## The price link, step by step

Test: weekly log change in Intents volume vs NEAR's weekly log return. Controlled regression:
`NEAR = a + b1·MKT + b2·ΔVolume`, MKT = mean of BTC and ETH weekly log returns, Newey-West (lag 2) t-stats.

| Sample | Weeks | Raw corr | Market-adjusted corr | Volume coef | t (NW) |
| --- | --- | --- | --- | --- | --- |
| All weeks | 96 | −0.05 | 0.04 | 0.009 | 0.45 |
| All weeks, volume ≥ $25M/week | 70 | 0.17 | 0.20 | 0.074 | 1.75 |
| All weeks, volume ≥ $100M/week | 58 | 0.21 | 0.23 | 0.100 | 1.70 |
| Pre-buyback (< 2026-02-23), ≥ $25M/week | 36 | 0.09 | 0.16 | 0.035 | 1.02 |
| Post-buyback (≥ 2026-02-23) | 35 | 0.36 | 0.32 | 0.215 | 1.73 |
| Post-buyback, before NEAR ETF listing (to 2026-09-14) | 29 | 0.25 | 0.21 | 0.122 | 1.06 |

Reading:

- The tiny launch weeks (~$1M/week in Dec 2024 - Jan 2025) hide the link; with them dropped the sign is
  consistently positive.
- The link is stronger after the buyback started (coefficient 0.215: a week with 10% more volume goes
  with ~2.1% more NEAR return, net of the market), but t = 1.73 is below the usual 2.0 bar.
- About half of the post-buyback effect comes from Sep-Oct 2026, when the first US spot NEAR ETF listed,
  NEAR more than doubled and Intents volume also hit records. Without those weeks, t falls to 1.06. A
  common cause (attention, ETF flows) explains that period at least as well as buybacks.
- Rolling 26-week windows: market-adjusted correlation was negative in 21 of 24 windows ending before
  Dec 2025 and has stayed between +0.15 and +0.34 since, with t peaking just under 2.0.
- A naive test without the market control and with plain t-stats gives t = 2.15 since the buyback.
  That is the number a quick analysis would report; it does not hold up.

## Bear / base / bull

`value_supported = annual_volume × (1+growth) × take_rate × multiplier × buyback_share × multiple`.
Baseline from data: $47.0B annual volume (30-day run-rate), 4.13 bps take rate (90-day captured/volume),
100% buyback share. Every knob's source is in `model/assumptions.yaml`.

| | Bear | Base | Bull |
| --- | --- | --- | --- |
| Volume growth | −50% | 0% | +100% |
| Take-rate multiplier | 0.75 | 1.0 | 1.35 |
| Buyback share | 50% | 100% | 100% |
| Multiple on buyback | 6x | 26x | 37x |
| Annual buyback | $3.6M | $19.4M | $52.3M |
| Value supported | $22M | $504M | $1.94B |
| Per NEAR (price $4.41) | $0.017 | $0.40 | $1.55 |
| Share of today's market cap | 0.4% | 8.7% | 33.5% |
| Buyback ÷ issuance | 0.03x | 0.13x | 0.36x |

Even the bull case, with volume doubling, a higher take rate and the richest comparable multiple, justifies
about a third of today's price. The rest of NEAR's value rests on other things (L1 usage, AI/agent
narrative, ETF and treasury demand), not on Intents cash flow.

## What would change the verdict

- Captured revenue reaching ~$145M a year (≈5.6x today) would make buybacks cover issuance. At today's
  take rate that needs ~$350B of annual volume; at a 1.35x take rate, ~$260B.
- Burning bought NEAR instead of holding it would make the supply effect permanent.
- The issuance cut to 1.6% proposed in Oct 2026 would lower the bar by about a third.
- More weeks: if the post-buyback effect holds at its current size, about 47 post-buyback weeks
  (mid-January 2027) would push t above 2.

## Caveats

- Correlation is not causation; only BTC/ETH market beta is controlled for.
- DefiLlama's adapter is the single source for volume, fees and revenue; we do not re-derive them on chain.
- Revenue is booked when swept to NEAR wallets, so daily revenue can exceed daily fees.
- Market cap and supply are one NearBlocks snapshot; comparable multiples are one 30-day window.
