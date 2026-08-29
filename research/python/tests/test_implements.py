"""Runner loads implements. No silent 0.618. YAML is not executed."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import pandas as pd

from themis.implements import ImplementsError, load_implements, resolve_implements
from themis.runner import RunError, _trades_from_implements
from strategies.retrace_swing import RetraceSpecError, zone_from_spec


class TestZoneFromYaml(unittest.TestCase):
    def test_reads_pct_low_high_no_default(self):
        n, lo, hi = zone_from_spec({"fractal_n": 3, "pct_low": 0.5, "pct_high": 0.8})
        self.assertEqual(n, 3)
        self.assertEqual(lo, 0.5)
        self.assertEqual(hi, 0.8)

    def test_retrace_pct_is_both_edges(self):
        n, lo, hi = zone_from_spec({"fractal_n": 5, "retrace_pct": 0.75})
        self.assertEqual(n, 5)
        self.assertEqual(lo, 0.75)
        self.assertEqual(hi, 0.75)

    def test_refuses_missing_zone(self):
        with self.assertRaises(RetraceSpecError) as ctx:
            zone_from_spec({"fractal_n": 5})
        self.assertIn("No 0.618 default", str(ctx.exception))


class TestLoadImplements(unittest.TestCase):
    def test_missing_implements(self):
        with self.assertRaises(ImplementsError) as ctx:
            load_implements({"id": "x", "kind": "strategy"})
        self.assertIn("no implements", str(ctx.exception).lower())

    def test_retrace_swing_found(self):
        spec = {
            "implements": "strategies/retrace_swing.py",
            "fractal_n": 5,
            "pct_low": 0.618,
            "pct_high": 0.725,
        }
        path = resolve_implements(spec)
        self.assertTrue(path.is_file())
        self.assertEqual(path.name, "retrace_swing.py")
        mod = load_implements(spec)
        self.assertTrue(callable(mod.trades))

    def test_missing_fractal_n_is_disagreement(self):
        with self.assertRaises(ImplementsError) as ctx:
            load_implements({"implements": "strategies/retrace_swing.py"})
        self.assertIn("disagree", str(ctx.exception).lower())
        self.assertIn("fractal_n", str(ctx.exception))

    def test_sma_stub_not_a_silent_retrace(self):
        spec = {
            "implements": "strategies/sma_cross.py",
            "n_fast": 10,
            "n_slow": 40,
            "costs": {"commission_per_side": 0},
        }
        idx = pd.date_range("2026-01-01", periods=50, freq="4h", tz="UTC")
        df = pd.DataFrame(
            {"open": 100.0, "high": 101.0, "low": 99.0, "close": 100.0},
            index=idx,
        )
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(RunError) as ctx:
                _trades_from_implements(spec, df, root=Path(td), symbol="BTCUSDT")
            self.assertIn("sma_cross", str(ctx.exception))
            self.assertNotIn("0.618", str(ctx.exception))


class TestRunnerDoesNotOwnRetrace(unittest.TestCase):
    def test_runner_source_has_no_pct_default(self):
        import inspect
        from themis import runner as r

        src = inspect.getsource(r)
        self.assertNotIn("0.618", src)
        self.assertNotIn("_swing_trades", src)
        self.assertIn("load_implements", src)


if __name__ == "__main__":
    unittest.main()
