"""Every external data source the pipeline uses. All are public and keyless."""

SOURCES = {
    "intents_volume": {
        "url": "https://api.llama.fi/summary/dexs/near-intents",
        "provider": "DefiLlama",
        "what": "NEAR Intents daily swap volume (USD)",
    },
    "intents_fees": {
        "url": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyFees",
        "provider": "DefiLlama",
        "what": "NEAR Intents gross daily fees: protocol + affiliate fees (USD)",
    },
    "intents_revenue": {
        "url": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue",
        "provider": "DefiLlama",
        "what": "NEAR's net captured Intents revenue, swept into NEAR revenue wallets (USD)",
    },
    "intents_holders_revenue": {
        "url": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyHoldersRevenue",
        "provider": "DefiLlama",
        "what": "Captured revenue used to buy back $NEAR on the open market since 2026-02-23 (USD)",
    },
    "near_price": {
        # coins.llama.fi caps a request at 500 points, so fetch.py walks 500-day
        # windows from 2024-12-01 (Intents data begins 2024-12-10) up to today.
        "url_template": "https://coins.llama.fi/chart/coingecko:near?start={start}&span=500&period=1d",
        "chunk_start": 1733011200,
        "chunk_days": 500,
        "provider": "DefiLlama coins (CoinGecko id 'near')",
        "what": "NEAR daily price (USD)",
    },
    "nearblocks_stats": {
        "url": "https://api.nearblocks.io/v1/stats",
        "provider": "NearBlocks",
        "what": "Current NEAR supply, market cap, price, total transactions",
    },
    "near_chain_tvl": {
        "url": "https://api.llama.fi/v2/historicalChainTvl/Near",
        "provider": "DefiLlama",
        "what": "Total value locked on the NEAR chain, daily (USD)",
    },
}
