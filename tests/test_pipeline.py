"""Offline tests against the committed snapshots in data/raw/. Run: python -m unittest -v"""
import hashlib
import json
import unittest
from pathlib import Path

import statistics as st

from pipeline import clean, metrics, model, robustness
from pipeline.sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"


class TestSnapshots(unittest.TestCase):
    def test_every_source_snapshotted_with_matching_hash(self):
        man = json.loads((RAW / "manifest.json").read_text())
        for name in SOURCES:
            entry = man["sources"][name]
            body = (ROOT / entry["file"]).read_bytes()
            self.assertEqual(hashlib.sha256(body).hexdigest(), entry["sha256"], name)
            self.assertTrue(all(s == 200 for s in entry["http_status"]), name)

    def test_source_shapes(self):
        for name in ("intents_volume", "intents_fees", "intents_revenue", "intents_holders_revenue"):
            raw = clean.load(name)
            self.assertEqual(raw["name"], "NEAR Intents")
            self.assertGreater(len(raw["totalDataChart"]), 100, name)
        self.assertIn("chunks", clean.load("near_price"))
        self.assertIn("circulating_supply", clean.load("nearblocks_stats")["stats"][0])
        self.assertIn("tvl", clean.load("near_chain_tvl")[0])


class TestBuild(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.daily = clean.build()
        cls.metrics = metrics.build(cls.daily)
        cls.model = model.build(cls.metrics)

    def test_daily_dates_unique_and_sorted(self):
        dates = [r["date"] for r in self.daily["rows"]]
        self.assertEqual(dates, sorted(set(dates)))

    def test_take_rates_are_fractions(self):
        for label, t in self.metrics["take_rates"].items():
            self.assertGreater(t["fees_per_volume"], 0, label)
            self.assertLess(t["fees_per_volume"], 0.01, label)  # Intents fees are basis points of volume

    def test_supply_in_near_not_yocto(self):
        c = self.daily["current"]
        self.assertTrue(5e8 < c["circulating_supply_near"] < 5e9)

    def test_model_formula(self):
        b = self.model["baseline"]
        for name, s in self.model["scenarios"].items():
            i = s["inputs"]
            expect = (b["annual_volume_usd"] * (1 + i["volume_growth"]) * b["take_rate"]
                      * i["take_rate_multiplier"] * i["buyback_share_used"] * i["multiple"])
            self.assertAlmostEqual(s["value_supported_usd"], expect, delta=1e-6 * expect, msg=name)

    def test_scenarios_ordered(self):
        s = self.model["scenarios"]
        self.assertLess(s["bear"]["value_supported_usd"], s["base"]["value_supported_usd"])
        self.assertLess(s["base"]["value_supported_usd"], s["bull"]["value_supported_usd"])

    def test_comparables_present_and_sane(self):
        comps = self.metrics["comparables"]
        self.assertEqual(len(comps), 3)
        for c in comps:
            self.assertGreater(c["mcap_to_annual_buyback"], 1, c["token"])
            self.assertLess(c["mcap_to_annual_buyback"], 500, c["token"])

    def test_issuance_offset(self):
        iss = self.model["issuance"]
        c = self.daily["current"]
        expect = iss["annual_issuance_rate"] * c["total_supply_near"] * c["near_price_usd"]
        self.assertAlmostEqual(iss["annual_issuance_usd_at_current_price"], expect, delta=1e-6 * expect)

    def test_market_controls_loaded(self):
        rows = [r for r in self.daily["rows"] if r["date"] >= "2025-01-01"]
        self.assertTrue(all(r["btc"] and r["eth"] for r in rows[:-1]))
        self.assertTrue(10_000 < rows[0]["btc"] < 1_000_000)

    def test_robustness_samples(self):
        rb = self.metrics["robustness"]
        labels = [s["label"] for s in rb["samples"]]
        self.assertTrue(any("pre-buyback" in l for l in labels))
        self.assertTrue(any("post-buyback" in l for l in labels))
        for s in rb["samples"]:
            self.assertGreaterEqual(s["n_weeks"], 12, s["label"])
            self.assertIsNotNone(s["dvol_t_newey_west_controlled"], s["label"])
        self.assertGreater(len(rb["rolling"]), 10)


class TestOLS(unittest.TestCase):
    def test_single_regressor_matches_stdlib(self):
        x = [0.1, -0.2, 0.05, 0.3, -0.1, 0.2, 0.0, -0.05, 0.15, -0.3, 0.25, 0.12]
        y = [0.5 * v + 0.01 * ((i % 3) - 1) for i, v in enumerate(x)]
        res = robustness.ols(y, [[v] for v in x], ["x"])
        slope, intercept = st.linear_regression(x, y)
        self.assertAlmostEqual(res["coef"]["x"], slope, places=10)
        self.assertAlmostEqual(res["coef"]["intercept"], intercept, places=10)

    def test_recovers_two_coefficients(self):
        import random
        rnd = random.Random(7)
        X = [[rnd.gauss(0, 1), rnd.gauss(0, 1)] for _ in range(400)]
        y = [0.3 + 1.5 * a - 0.7 * b + rnd.gauss(0, 0.1) for a, b in X]
        res = robustness.ols(y, X, ["a", "b"])
        self.assertAlmostEqual(res["coef"]["a"], 1.5, delta=0.03)
        self.assertAlmostEqual(res["coef"]["b"], -0.7, delta=0.03)
        self.assertGreater(abs(res["t_newey_west"]["a"]), 50)


if __name__ == "__main__":
    unittest.main()
