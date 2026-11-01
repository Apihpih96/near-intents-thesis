"""Bear / base / bull value-capture model (data/processed/model.json).

value_supported = annual_volume*(1+g) * take_rate*m * buyback_share * multiple
The output answers: how much of NEAR's market cap could Intents buybacks alone justify?
"""
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "processed"
ASSUMPTIONS = ROOT / "model" / "assumptions.yaml"


def baseline(metrics):
    w30, w90 = metrics["windows"]["30d"], metrics["windows"]["90d"]
    vc = metrics["value_capture"]
    return {
        "annual_volume_usd": w30["volume"] * 365 / 30,
        "take_rate": w90["revenue"] / w90["volume"],
        "buyback_share": (w90["holders_revenue"] or 0) / w90["revenue"],
        "market_cap_usd": vc["market_cap_usd"],
        "circulating_supply_near": vc["circulating_supply_near"],
        "near_price_usd": metrics["current"]["near_price_usd"],
        "total_supply_near": metrics["current"]["total_supply_near"],
        "annual_buyback_usd_now": vc["annualized_buyback_usd_from_30d"],
        "market_implied_buyback_multiple": vc["market_cap_usd"] / vc["annualized_buyback_usd_from_30d"]
        if vc["annualized_buyback_usd_from_30d"] else None,
    }


def run_scenario(base, s, issuance_usd):
    share = base["buyback_share"] if s["buyback_share"] == "observed" else float(s["buyback_share"])
    vol = base["annual_volume_usd"] * (1 + float(s["volume_growth"]))
    rev = vol * base["take_rate"] * float(s["take_rate_multiplier"])
    bb = rev * share
    value = bb * float(s["multiple"])
    return {
        "inputs": {**s, "buyback_share_used": share},
        "annual_volume_usd": vol,
        "annual_captured_revenue_usd": rev,
        "annual_buyback_usd": bb,
        "annual_buyback_pct_of_mcap": bb / base["market_cap_usd"],
        "annual_near_bought_at_current_price": bb / base["near_price_usd"],
        "value_supported_usd": value,
        "value_supported_per_near_usd": value / base["circulating_supply_near"],
        "share_of_current_mcap_supported": value / base["market_cap_usd"],
        "buyback_vs_issuance": bb / issuance_usd if issuance_usd else None,
    }


def build(metrics, path=ASSUMPTIONS):
    cfg = yaml.safe_load(Path(path).read_text())
    base = baseline(metrics)
    rate = float(cfg.get("annual_issuance_rate", 0.025))
    issuance_usd = rate * base["total_supply_near"] * base["near_price_usd"]
    comps = metrics.get("comparables", [])
    out = {
        "formula": "value_supported = annual_volume*(1+volume_growth) * take_rate*take_rate_multiplier * buyback_share * multiple",
        "baseline": base,
        "assumptions_file": "model/assumptions.yaml",
        "issuance": {
            "annual_issuance_rate": rate,
            "annual_issuance_usd_at_current_price": issuance_usd,
            "buyback_vs_issuance_now": base["annual_buyback_usd_now"] / issuance_usd if issuance_usd else None,
            "note": "Max-issuance upper bound (rate x total supply x price). Bought-back NEAR is held, not burned [S1][S5].",
        },
        "comparables": comps,
        "scenarios": {k: run_scenario(base, v, issuance_usd) for k, v in cfg["scenarios"].items()},
    }
    (OUT / "model.json").write_text(json.dumps(out, indent=1))
    for k, v in out["scenarios"].items():
        print(f"  model {k:<5} value supported ${v['value_supported_usd']/1e6:,.0f}M "
              f"= ${v['value_supported_per_near_usd']:.3f}/NEAR "
              f"({v['share_of_current_mcap_supported']:.1%} of mcap, buyback {v['buyback_vs_issuance']:.2f}x issuance)")
    return out
