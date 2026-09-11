"""Run engine: honest folders, costs, requires_asks, --thin, no silent 0.618."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from themis.fees import fee_schedule
from themis.metrics import MUST
from themis.paths import short_hash
from themis.runner import RunError, run_strategy
from themis.spec import dump_yaml, load_spec


def _ohlc_csv(path: Path, n: int, seed: int = 21, start: str = "2022-01-01") -> None:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="4h", tz="UTC")
    drift = np.linspace(0, 80, n)
    noise = np.cumsum(rng.normal(0, 2.2, n))
    wave = 55 * np.sin(np.arange(n) / 16.0)
    close = 20000 + drift + noise + wave
    high = close + rng.uniform(20, 180, n)
    low = close - rng.uniform(20, 180, n)
    open_ = np.concatenate([[close[0]], close[:-1]])
    df = pd.DataFrame(
        {
            "ts": idx,
            "open": open_,
            "high": np.maximum.reduce([open_, high, close]),
            "low": np.minimum.reduce([open_, low, close]),
            "close": close,
            "volume": rng.uniform(1, 20, n),
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


def _strategy_spec(**extra) -> dict:
    spec = {
        "id": "g1-n5-1r-btc-4h-v1",
        "kind": "strategy",
        "family": "g1-btc-4h-v1",
        "implements": "strategies/retrace_swing.py",
        "requires_asks": ["g1-n5-btc-4h-v1", "g1-n3-btc-4h-v1"],
        "instrument": {
            "symbol": "BTCUSDT",
            "venue": "binance",
            "provider": "binance",
            "timeframe": "4h",
        },
        "data": {"provider": "binance", "source": "csv", "exchange": "binanceusdm"},
        "discovery": {"start": None, "end": None, "note": "all bars"},
        "holdout": {"start": None, "end": None, "note": "none"},
        "costs": {
            **fee_schedule("BTCUSDT", fill="next_open"),
            "slippage_ticks": 1,
            "tick_size": 0.1,
        },
        "rules": {
            "fill": "next_open",
            "entry": "next open after closed-bar zone touch",
            "stop": "swing origin",
            "target": "swing extreme",
        },
        "forbidden": ["forming_bar_signals", "same_bar_fill", "future_pivots"],
        "kill": {"min_trades": 30, "max_drawdown_pct": 40, "min_net_return": 0},
        "search_space": {},
        "run_eligible": False,
        "walkforward_eligible": False,
        "tune_eligible": False,
        "fractal_n": 5,
        "pct_low": 0.618,
        "pct_high": 0.725,
    }
    spec.update(extra)
    return spec


def _dummy_asks(root: Path, ids: list[str]) -> None:
    runs = root / "research" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    for rid in ids:
        d = runs / f"dummy-{rid}-ask"
        d.mkdir(exist_ok=True)
        (d / "metrics.json").write_text("{}\n", encoding="utf-8")
        (d / "meta.json").write_text(
            json.dumps({"kind": "question", "spec_id": rid}) + "\n", encoding="utf-8"
        )


def _write_ready(root: Path, n: int = 800, spec: dict | None = None) -> Path:
    _ohlc_csv(root / "research" / ".cache" / "binance" / "binanceusdm" / "BTCUSDT" / "4h.csv", n)
    spec = spec or _strategy_spec()
    _dummy_asks(root, list(spec.get("requires_asks") or []))
    path = root / "research" / "specs" / f"{spec['id']}.yaml"
    dump_yaml(spec, path)
    return path


class TestRunRefuses(unittest.TestCase):
    def test_question_spec_refused(self):
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            spec = {
                "id": "q-not-a-run",
                "kind": "question",
                "instrument": {"symbol": "BTCUSDT", "venue": "binance", "provider": "binance"},
                "data": {"provider": "binance", "source": "csv"},
                "discovery": {"start": None, "end": None, "note": "all"},
                "holdout": {"start": None, "end": None, "note": "none"},
                "population": "events",
                "condition": [{"kind": "generic"}],
                "outcome": {"name": "flag", "kind": "flag"},
                "definitions": {"x": "pinned"},
                "stats": ["n"],
                "forbidden": ["quoting_pnl_from_this_ask"],
            }
            path = root / "q.yaml"
            dump_yaml(spec, path)
            with self.assertRaises(RunError) as ctx:
                run_strategy(path, root=root, network=False, thin=True)
            self.assertIn("question", str(ctx.exception).lower())

    def test_empty_requires_asks_refused(self):
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            path = _write_ready(root, spec=_strategy_spec(requires_asks=[]))
            with self.assertRaises(RunError) as ctx:
                run_strategy(path, root=root, network=False, thin=True)
            self.assertIn("requires_asks", str(ctx.exception).lower())

    def test_missing_ask_folders_refused(self):
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            _ohlc_csv(root / "research" / ".cache" / "binance" / "binanceusdm" / "BTCUSDT" / "4h.csv", 400)
            spec = _strategy_spec()
            path = root / "research" / "specs" / f"{spec['id']}.yaml"
            dump_yaml(spec, path)
            with self.assertRaises(RunError) as ctx:
                run_strategy(path, root=root, network=False, thin=True)
            self.assertIn("requires_asks", str(ctx.exception).lower())

    def test_thin_without_flag_refused(self):
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            path = _write_ready(root, n=800, spec=_strategy_spec(run_eligible=False))
            with self.assertRaises(RunError) as ctx:
                run_strategy(path, root=root, network=False, thin=False)
            msg = str(ctx.exception).lower()
            self.assertTrue("thin" in msg or "run_eligible" in msg)
            self.assertIn("n_bars", msg)

    def test_no_costs_dict_is_spec_error(self):
        spec = _strategy_spec()
        del spec["costs"]
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            path = root / "s.yaml"
            dump_yaml(spec, path)
            with self.assertRaises(RunError) as ctx:
                run_strategy(path, root=root, network=False, thin=True)
            self.assertIn("cost", str(ctx.exception).lower())

    def test_missing_zone_does_not_default_618(self):
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            spec = _strategy_spec()
            del spec["pct_low"]
            del spec["pct_high"]
            path = _write_ready(root, spec=spec)
            with self.assertRaises(RunError) as ctx:
                run_strategy(path, root=root, network=False, thin=True)
            msg = str(ctx.exception)
            self.assertIn("0.618", msg)
            self.assertIn("disagree", msg.lower())


class TestRunWritesHonestFolder(unittest.TestCase):
    def test_thin_run_writes_canon_files(self):
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            n = 800
            path = _write_ready(root, n=n, spec=_strategy_spec(run_eligible=False))
            folder = run_strategy(path, root=root, network=False, thin=True)
            for name in ("trades.csv", "equity.csv", "metrics.json", "meta.json", "spec.yaml", "engine.log", "status.json"):
                self.assertTrue((folder / name).exists(), name)
            self.assertEqual(folder.name.split("-")[-1], short_hash("g1-n5-1r-btc-4h-v1"))
            self.assertEqual(folder.name.split("-")[-1], hashlib.sha1(b"g1-n5-1r-btc-4h-v1").hexdigest()[:8])
            eq = pd.read_csv(folder / "equity.csv")
            self.assertEqual(len(eq), n)
            self.assertEqual(list(eq.columns)[:3], ["bar_i", "ts", "equity"])
            self.assertEqual(int(eq["bar_i"].iloc[0]), 0)
            self.assertEqual(int(eq["bar_i"].iloc[-1]), n - 1)
            metrics = json.loads((folder / "metrics.json").read_text())
            self.assertTrue(metrics["thin"])
            self.assertFalse(metrics["kept_possible"])
            self.assertFalse(metrics["execution_ready"])
            self.assertEqual(metrics["notional"], "1_unit")
            self.assertEqual(metrics["pnl_unit"], "price")
            self.assertEqual(metrics["periods_per_year"], 2190)
            nc = metrics.get("not_computed") or {}
            self.assertIsInstance(nc, dict)
            for key in MUST:
                self.assertTrue(key in metrics or key in nc, key)
            for key in ("sharpe", "sortino", "calmar", "cagr", "profit_factor", "expectancy", "win_rate", "payoff_ratio"):
                self.assertTrue(key in metrics or key in nc, key)
            modeled = metrics.get("not_modeled") or []
            self.assertIn("perp funding", modeled)
            self.assertTrue(any("intra-bar" in x for x in modeled), modeled)
            self.assertEqual(metrics["same_bar_policy"], "ambiguous_tagged_fill_stop")
            self.assertEqual(metrics["gap_policy"], "fill_at_open")
            log = (folder / "engine.log").read_text().lower()
            self.assertIn("funding", log)
            self.assertIn("intra-bar", log)
            self.assertIn("costs_applied", metrics)
            self.assertEqual(metrics["costs_applied"]["commission_per_side"], 0.0005)
            frozen = load_spec(folder / "spec.yaml")
            self.assertEqual(frozen["costs"]["commission_per_side"], 0.0005)
            trades = pd.read_csv(folder / "trades.csv")
            self.assertIn("pnl", trades.columns)
            self.assertIn("why", trades.columns)

    def test_missing_commission_is_frozen_from_fees(self):
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            spec = _strategy_spec(
                costs={"slippage_ticks": 1, "tick_size": 0.1},
            )
            path = _write_ready(root, n=400, spec=spec)
            folder = run_strategy(path, root=root, network=False, thin=True)
            frozen = load_spec(folder / "spec.yaml")
            self.assertEqual(frozen["costs"]["commission_per_side"], 0.0005)
            self.assertEqual(frozen["costs"]["product"], "usd_m_crypto")
            metrics = json.loads((folder / "metrics.json").read_text())
            self.assertEqual(metrics["costs_applied"]["commission_per_side"], 0.0005)

    def test_btc_over_thin_floor_writes_without_thin_flag(self):
        with tempfile.TemporaryDirectory(prefix="themis-run-") as td:
            root = Path(td)
            n = 4200
            path = _write_ready(root, n=n, spec=_strategy_spec(run_eligible=True))
            folder = run_strategy(path, root=root, network=False, thin=False)
            metrics = json.loads((folder / "metrics.json").read_text())
            meta = json.loads((folder / "meta.json").read_text())
            self.assertFalse(metrics["thin"])
            self.assertEqual(meta["n_bars"], n)
            self.assertTrue((folder / "trades.csv").exists())
            eq = pd.read_csv(folder / "equity.csv")
            self.assertEqual(len(eq), n)
            nc = metrics.get("not_computed") or {}
            # Two or more equity points: Sharpe/Sortino write unless std/downside is 0.
            if "sharpe" not in metrics:
                self.assertIn("sharpe", nc)
            if "sortino" not in metrics:
                self.assertIn("sortino", nc)
            self.assertIn("cagr", metrics)
            self.assertFalse(metrics["execution_ready"])
            self.assertIn("perp funding", metrics["not_modeled"])


if __name__ == "__main__":
    unittest.main()
