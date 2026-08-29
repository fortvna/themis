"""§18 metrics and fill policies. No 252. Bar equity, not trade equity."""
from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from themis.metrics import (
    equity_on_bars,
    max_drawdown_pct,
    periods_per_year,
    strategy_metrics,
)
from themis.fill import simulate_exit


def _bars(rows: list[tuple[float, float, float, float]], start: str = "2026-01-01") -> pd.DataFrame:
    idx = pd.date_range(start, periods=len(rows), freq="4h", tz="UTC")
    o, h, l, c = zip(*rows)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)


class TestAtrCompletePythonOwnsLogic(unittest.TestCase):
    def test_rivals_come_from_python_not_notebook_math(self):
        from themis.ask import ATR_COMPLETE_RIVALS, atr_complete_rivals, atr_path_days

        idx = pd.date_range("2026-06-01", periods=80, freq="4h", tz="UTC")
        close = 2000.0 + np.arange(len(idx)) * 0.1
        df = pd.DataFrame(
            {"open": close, "high": close + 30, "low": close - 10, "close": close},
            index=idx,
        )
        path = atr_path_days(df, atr_n=14)
        self.assertIn("prior_atr", path.columns)
        self.assertIn("from_open", path.columns)
        summary, tables = atr_complete_rivals(df)
        self.assertEqual(len(summary), len(ATR_COMPLETE_RIVALS))
        self.assertEqual(set(tables), {(r["atr_n"], r["complete"]) for r in ATR_COMPLETE_RIVALS})
        self.assertTrue((path["from_open"] <= path["day_range"] + 1e-9).all())


class TestPeriods(unittest.TestCase):
    def test_crypto_year_not_252(self):
        self.assertEqual(periods_per_year("1h"), 8760)
        self.assertEqual(periods_per_year("4h"), 2190)
        self.assertEqual(periods_per_year("1d"), 365)
        self.assertEqual(periods_per_year("15m"), 365 * 24 / 0.25)
        self.assertNotEqual(periods_per_year("1d"), 252)


class TestFills(unittest.TestCase):
    def test_gap_through_stop_fills_at_open(self):
        df = _bars(
            [
                (100, 101, 99, 100),
                (100, 101, 99, 100),
                (90, 91, 89, 90),
            ]
        )
        row = simulate_exit(
            "long",
            1,
            95,
            110,
            df.open.to_numpy(),
            df.high.to_numpy(),
            df.low.to_numpy(),
            df.close.to_numpy(),
        )
        assert row is not None
        self.assertEqual(row["why"], "stop_gap")
        self.assertTrue(row["gap"])
        self.assertEqual(row["exit_i"], 2)
        self.assertEqual(row["exit_level"], 90.0)

    def test_same_bar_stop_and_target_fills_stop_and_tags(self):
        df = _bars([(100, 120, 80, 100)])
        row = simulate_exit(
            "long",
            0,
            90,
            110,
            df.open.to_numpy(),
            df.high.to_numpy(),
            df.low.to_numpy(),
            df.close.to_numpy(),
        )
        assert row is not None
        self.assertEqual(row["why"], "ambiguous_same_bar")
        self.assertTrue(row["ambiguous"])
        self.assertEqual(row["exit_level"], 90.0)
        self.assertLess(row["pnl"], 0)

    def test_slippage_is_adverse_on_entry_and_exit(self):
        df = _bars(
            [
                (100, 101, 99, 100),
                (100, 120, 99, 110),
            ]
        )
        raw = simulate_exit(
            "long",
            0,
            90,
            110,
            df.open.to_numpy(),
            df.high.to_numpy(),
            df.low.to_numpy(),
            df.close.to_numpy(),
            slip=0.0,
            commission=0.0,
        )
        slipped = simulate_exit(
            "long",
            0,
            90,
            110,
            df.open.to_numpy(),
            df.high.to_numpy(),
            df.low.to_numpy(),
            df.close.to_numpy(),
            slip=0.5,
            commission=0.0,
        )
        assert raw is not None and slipped is not None
        self.assertEqual(raw["why"], "target")
        self.assertEqual(slipped["why"], "target")
        self.assertAlmostEqual(raw["entry"], 100.0)
        self.assertAlmostEqual(slipped["entry"], 100.5)
        self.assertAlmostEqual(slipped["exit"], raw["exit"] - 0.5)
        self.assertLess(slipped["pnl"], raw["pnl"])


class TestEquityAndRatios(unittest.TestCase):
    def test_equity_is_bar_indexed_not_trade_indexed(self):
        e0 = 100.0
        eq = equity_on_bars(5, e0, [2], [2.0])
        self.assertEqual(len(eq), 5)
        np.testing.assert_allclose(eq, [100, 100, 102, 102, 102])

    def test_max_dd_uses_running_peak(self):
        eq = np.array([100.0, 110.0, 99.0, 105.0])
        dd = max_drawdown_pct(eq, e0=100.0)
        assert dd is not None
        self.assertAlmostEqual(dd, (110 - 99) / 110 * 100.0, places=6)

    def test_sharpe_from_bar_returns_sortino_keeps_zeros(self):
        idx = pd.date_range("2026-01-01", periods=5, freq="4h", tz="UTC")
        e0 = 100.0
        eq = equity_on_bars(5, e0, [2, 4], [2.0, -1.0])
        trades = pd.DataFrame({"pnl": [2.0, -1.0]})
        m = strategy_metrics(
            trades=trades,
            equity=eq,
            e0=e0,
            index=idx,
            timeframe="4h",
            kill={"min_trades": 1, "max_drawdown_pct": 40, "min_net_return": -1},
        )
        self.assertEqual(m["n_trades"], 2)
        self.assertEqual(m["periods_per_year"], 2190)
        self.assertNotEqual(m["periods_per_year"], 252)
        self.assertIn("sharpe", m)
        self.assertNotIn("sharpe", m["not_computed"])
        path = np.concatenate(([e0], eq))
        r = path[1:] / path[:-1] - 1.0
        mu = r.mean()
        sig = r.std(ddof=1)
        want = ((mu) / sig) * math.sqrt(2190)
        self.assertAlmostEqual(m["sharpe"], want, places=5)
        # Sortino: zeros stay in the denominator (full sample).
        dd_dev = float(np.sqrt(np.mean(np.minimum(r, 0.0) ** 2)))
        self.assertGreater(dd_dev, 0)
        self.assertAlmostEqual(m["sortino"], (mu / dd_dev) * math.sqrt(2190), places=5)
        self.assertGreaterEqual(m["sortino"], m["sharpe"] - 1e-9)
        self.assertEqual(m["calmar_window"], "full_sample")
        self.assertTrue(m["short_window"])
        self.assertEqual(m["notional"], "1_unit")
        self.assertEqual(m["pnl_unit"], "price")
        self.assertIn("perp funding", m["not_modeled"])

    def test_zero_dd_calmar_is_not_computed(self):
        idx = pd.date_range("2026-01-01", periods=400, freq="4h", tz="UTC")
        e0 = 100.0
        eq = equity_on_bars(400, e0, [2], [1.0])
        m = strategy_metrics(
            trades=pd.DataFrame({"pnl": [1.0]}),
            equity=eq,
            e0=e0,
            index=idx,
            timeframe="4h",
        )
        self.assertAlmostEqual(m["max_drawdown_pct"], 0.0)
        self.assertIn("cagr", m)
        self.assertNotIn("calmar", m)
        self.assertEqual(m["not_computed"].get("calmar"), "max_drawdown_pct=0")

    def test_no_losses_profit_factor_reason(self):
        idx = pd.date_range("2026-01-01", periods=3, freq="4h", tz="UTC")
        eq = equity_on_bars(3, 100.0, [1], [1.0])
        m = strategy_metrics(
            trades=pd.DataFrame({"pnl": [1.0]}),
            equity=eq,
            e0=100.0,
            index=idx,
            timeframe="4h",
        )
        self.assertEqual(m["not_computed"].get("profit_factor"), "no_losses")
        self.assertEqual(m["win_rate"], 1.0)

    def test_kill_fails_min_trades(self):
        idx = pd.date_range("2026-01-01", periods=3, freq="4h", tz="UTC")
        eq = equity_on_bars(3, 100.0, [], [])
        m = strategy_metrics(
            trades=pd.DataFrame(columns=["pnl"]),
            equity=eq,
            e0=100.0,
            index=idx,
            timeframe="4h",
            kill={"min_trades": 30, "max_drawdown_pct": 40, "min_net_return": 0},
        )
        self.assertFalse(m["kill_pass"])
        self.assertIn("min_trades", m["kill_failed"])
        self.assertEqual(m["not_computed"]["expectancy"], "no trades")


class TestRunWritesCanon(unittest.TestCase):
    def test_run_folder_has_bar_equity_and_ratios_or_reasons(self):
        from themis.ask import run_ask
        from themis.compiler import compile_english
        from themis.runner import run_strategy

        series = {
            "provider": "binance",
            "symbol": "BTCUSDT",
            "timeframe": "4h",
            "exchange": "binanceusdm",
        }
        with tempfile.TemporaryDirectory(prefix="themis-metrics-") as td:
            root = Path(td)
            cache = root / "research" / ".cache" / "binance" / "binanceusdm" / "BTCUSDT"
            cache.mkdir(parents=True)
            rng = np.random.default_rng(21)
            n = 4500
            idx = pd.date_range("2022-01-01", periods=n, freq="4h", tz="UTC")
            close = 20000 * np.cumprod(1 + rng.normal(0, 0.004, n))
            df = pd.DataFrame(
                {
                    "ts": idx,
                    "open": close / 1.001,
                    "high": close * 1.006,
                    "low": close * 0.994,
                    "close": close,
                    "volume": 10,
                }
            )
            df.to_csv(cache / "4h.csv", index=False)
            job = compile_english("G1", series, write=True, root=root)
            for item in job["plan"]:
                if item["kind"] == "question":
                    run_ask(root / item["yaml"], root=root, network=False)
            st = [p for p in job["plan"] if p["kind"] == "strategy"][0]
            folder = run_strategy(root / st["yaml"], root=root, network=False, thin=False)
            metrics = json.loads((folder / "metrics.json").read_text())
            self.assertTrue((folder / "equity.csv").exists())
            eq = pd.read_csv(folder / "equity.csv")
            self.assertEqual(len(eq), n)
            nc = metrics.get("not_computed") or {}
            self.assertIsInstance(nc, dict)
            for key in (
                "sharpe",
                "sortino",
                "calmar",
                "cagr",
                "profit_factor",
                "expectancy",
                "win_rate",
                "payoff_ratio",
            ):
                self.assertTrue(
                    key in metrics or key in nc,
                    f"{key} missing from metrics and not_computed",
                )
            self.assertNotIsInstance(nc, list)
            self.assertEqual(metrics["periods_per_year"], 2190)
            self.assertIn("n_ambiguous", metrics)
            self.assertFalse(metrics["execution_ready"])
            self.assertIn("kill_pass", metrics)


if __name__ == "__main__":
    unittest.main()
