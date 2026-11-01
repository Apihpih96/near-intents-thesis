"""Offline tests against the committed snapshots in data/raw/. Run: python -m unittest -v"""
import hashlib
import json
import unittest
from pathlib import Path

from pipeline import clean, metrics, model
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


if __name__ == "__main__":
    unittest.main()
