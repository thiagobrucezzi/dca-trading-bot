"""Tests de la lógica DCA (stdlib unittest, sin red ni keys).

Corré: .venv/bin/python tests/test_dca.py
"""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import exchange
from src.dca import period_key, run_once
from src.portfolio import DATA_DIR, Portfolio

TEST_MODE = "unittest_tmp"


def _cleanup():
    p = DATA_DIR / f"portfolio_{TEST_MODE}.json"
    if p.exists():
        p.unlink()


class PeriodKeyTest(unittest.TestCase):
    def test_monthly(self):
        self.assertEqual(period_key(datetime(2026, 6, 15, tzinfo=timezone.utc), "monthly"), "2026-06")

    def test_daily(self):
        self.assertEqual(period_key(datetime(2026, 6, 15, tzinfo=timezone.utc), "daily"), "2026-06-15")

    def test_weekly(self):
        self.assertTrue(period_key(datetime(2026, 6, 15, tzinfo=timezone.utc), "weekly").startswith("2026-W"))


class PortfolioTest(unittest.TestCase):
    def setUp(self):
        _cleanup()

    def tearDown(self):
        _cleanup()

    def test_add_persist_and_idempotency(self):
        pf = Portfolio(TEST_MODE)
        self.assertFalse(pf.bought_in_period("2026-06"))
        pf.add_buy({"symbol": "BTC/USDT", "price": 60000.0, "units": 0.001,
                    "quote_spent": 60.0, "fee": 0.06, "mode": TEST_MODE},
                   "2026-06-01T00:00:00+00:00", "2026-06")
        self.assertTrue(pf.bought_in_period("2026-06"))
        # se relee desde disco (persistencia)
        pf2 = Portfolio(TEST_MODE)
        self.assertEqual(len(pf2.buys), 1)
        self.assertTrue(pf2.bought_in_period("2026-06"))

    def test_summary_math(self):
        pf = Portfolio(TEST_MODE)
        pf.add_buy({"symbol": "BTC/USDT", "price": 50000.0, "units": 0.001,
                    "quote_spent": 50.0, "fee": 0.05, "mode": TEST_MODE}, "t1", "2026-01")
        pf.add_buy({"symbol": "BTC/USDT", "price": 100000.0, "units": 0.0005,
                    "quote_spent": 50.0, "fee": 0.05, "mode": TEST_MODE}, "t2", "2026-02")
        s = pf.summary({"BTC/USDT": 80000.0})
        self.assertAlmostEqual(s["invested"], 100.0)
        self.assertAlmostEqual(s["positions"]["BTC/USDT"]["units"], 0.0015)
        self.assertAlmostEqual(s["value"], 120.0)        # 0.0015 * 80000
        self.assertAlmostEqual(s["pnl"], 20.0)
        self.assertAlmostEqual(s["pnl_pct"], 0.20)
        self.assertAlmostEqual(s["positions"]["BTC/USDT"]["avg_cost"], 100 / 0.0015, places=2)


class SimulateBuyTest(unittest.TestCase):
    @mock.patch("src.exchange.get_price", return_value=50000.0)
    def test_simulate_fill_math(self, _):
        with mock.patch.dict("os.environ", {"BOT_MODE": "simulate"}):
            fill = exchange.execute_buy("BTC/USDT", 50.0)
        self.assertEqual(fill["mode"], "simulate")
        self.assertAlmostEqual(fill["fee"], 0.05)                      # 50 * 0.001
        self.assertAlmostEqual(fill["units"], (50 - 0.05) / 50000.0)   # (gastado - fee)/precio
        self.assertAlmostEqual(fill["quote_spent"], 50.0)


class RunOnceTest(unittest.TestCase):
    def setUp(self):
        _cleanup()

    def tearDown(self):
        _cleanup()

    def test_run_once_is_idempotent_per_period(self):
        fake = {"symbol": "BTC/USDT", "price": 50000.0, "units": 0.001,
                "quote_spent": 50.0, "fee": 0.05, "mode": TEST_MODE}
        with mock.patch.dict("os.environ", {"BOT_MODE": TEST_MODE}), \
             mock.patch("src.dca.execute_buy", return_value=fake):
            now = datetime(2026, 6, 15, tzinfo=timezone.utc)
            r1 = run_once(now=now, notify=False)
            r2 = run_once(now=now, notify=False)  # mismo mes -> no debe re-comprar
        self.assertIsNotNone(r1)
        self.assertIsNone(r2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
