"""Named-stop gate. Compile must not rewrite low+1 ATR as low-ATR."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from themis.compiler import CompileError, compile_english
from themis.named import (
    AMIR_H1_ENGLISH,
    NamedGateError,
    check_named,
    extract_stop,
    overlay_named,
    parse_named,
    parse_stop_text,
    pin_plan,
)
from themis.spec import load_yaml

SERIES = {
    "provider": "binance",
    "symbol": "XAUUSDT",
    "timeframe": "1h",
    "exchange": "binanceusdm",
}


class TestParseNamed(unittest.TestCase):
    def test_amir_english_pins_plus_atr_not_minus(self):
        named = parse_named(AMIR_H1_ENGLISH)
        self.assertEqual(named["timeframe"], "1h")
        self.assertEqual(named["retrace_pct"], 0.618)
        self.assertEqual(named["stop"]["anchor"], "swing_low")
        self.assertEqual(named["stop"]["op"], "+")
        self.assertEqual(named["stop"]["k"], 1.0)
        self.assertEqual(named["stop"]["unit"], "ATR")
        self.assertEqual(named["target"]["anchor"], "swing_high")
        plus = parse_stop_text("swing low + 1*ATR")
        minus = parse_stop_text("1 ATR beyond the swing origin (long: low - ATR; short: high + ATR)")
        self.assertNotEqual(
            (plus["anchor"], plus["op"], plus["k"], plus["unit"]),
            (minus["anchor"], minus["op"], minus["k"], minus["unit"]),
        )
        self.assertEqual(minus["op"], "-")


class TestOverlayAndRefuse(unittest.TestCase):
    def test_overlay_rewrites_minus_atr_to_named_plus(self):
        named = parse_named(AMIR_H1_ENGLISH)
        spec = {
            "id": "drift",
            "kind": "strategy",
            "rules": {
                "stop": "1 ATR beyond the swing origin (long: low - ATR; short: high + ATR)",
                "target": "swing extreme",
            },
        }
        overlay_named(named, spec)
        got = extract_stop(spec)
        self.assertEqual(got["op"], "+")
        self.assertIn("+", spec["rules"]["stop"])
        self.assertNotIn("low -", spec["rules"]["stop"].replace("\u2212", "-"))
        pin_plan(named, [], [spec])

    def test_refuse_names_the_field_when_yaml_still_differs(self):
        named = parse_named(AMIR_H1_ENGLISH)
        spec = {
            "id": "bad",
            "kind": "strategy",
            "rules": {"stop": "low - ATR", "target": "swing high"},
        }
        with self.assertRaises(NamedGateError) as ctx:
            check_named(named, [spec])
        msg = str(ctx.exception)
        self.assertIn("stop", msg)
        self.assertIn("english=", msg)
        self.assertIn("yaml=", msg)
        self.assertIn("+", msg)


class TestCompileNamedEnglish(unittest.TestCase):
    def test_mock_compile_writes_swing_low_plus_one_atr(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            job = compile_english(AMIR_H1_ENGLISH, SERIES, backend="mock", write=True, root=root)
            self.assertEqual(job["status"], "ok")
            self.assertTrue(job["gates"].get("named_fields_pinned"))
            self.assertEqual(job["named"]["stop"]["op"], "+")
            strats = [p for p in job["plan"] if p["kind"] == "strategy"]
            self.assertTrue(strats)
            spec = load_yaml(root / strats[0]["yaml"])
            stop = spec["rules"]["stop"]
            self.assertRegex(stop, r"low\s*\+\s*1\*ATR")
            self.assertNotRegex(stop.replace("\u2212", "-"), r"low\s*-\s*ATR")
            qs = [p for p in job["plan"] if p["kind"] == "question"]
            self.assertGreaterEqual(len(qs), 2)
            ids = {p["id"] for p in qs}
            self.assertEqual(len(ids), len(qs), "rivals must be new spec ids")
            stops = set()
            fractals = set()
            for p in qs:
                q = load_yaml(root / p["yaml"])
                self.assertEqual(q["named"]["stop"]["op"], "+")
                stops.add(q["rules"]["stop"])
                fractals.add(q.get("fractal_n"))
            self.assertEqual(len(stops), 1, "cousins copy the named stop")
            self.assertGreaterEqual(len(fractals), 2, "rivals only for unnamed fractal n")

    def test_cli_nonzero_on_named_disagree(self):
        named = parse_named(AMIR_H1_ENGLISH)
        spec = {"id": "x", "kind": "strategy", "rules": {"stop": "low - ATR", "target": "swing high"}}
        with self.assertRaises(NamedGateError):
            check_named(named, [spec])
        with self.assertRaises(CompileError) as ctx:
            raise CompileError(
                "named field stop disagrees: english=swing low + 1*ATR yaml=swing low - 1*ATR"
            )
        self.assertIn("stop", str(ctx.exception))

    def test_unknown_without_named_still_needs_human(self):
        job = compile_english("how do I cook pasta", SERIES, write=False)
        self.assertEqual(job["status"], "needs_human")
