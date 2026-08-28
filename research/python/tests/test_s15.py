"""Acceptance tests for open-spec.md §15 items 2-9 and 12. Stdlib unittest; no pytest."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from themis.ask import AskError, run_ask
from themis.auth import login, logout, whoami
from themis.cli import main
from themis.compiler import BANK, CompileError, compile_bank, compile_english
from themis.runner import RunError, run_strategy, tune, walkforward
from themis.spec import dump_yaml, load_spec, PNL_KEYS

SERIES_GOLD = {
    "provider": "binance",
    "symbol": "XAUUSDT",
    "timeframe": "4h",
    "exchange": "binanceusdm",
}
ASK_IDS = [k for k, v in BANK.items() if v["path"] == "ask"]
RUN_IDS = [k for k, v in BANK.items() if v["path"] == "run"]
FAMILY_IDS = [k for k, v in BANK.items() if v["path"] == "family"]
HUMAN_IDS = [k for k, v in BANK.items() if v["path"] == "needs_human"]
ERROR_IDS = [k for k, v in BANK.items() if v["path"] == "error"]


def _ohlc_csv(path: Path, n: int, seed: int = 1, start: str = "2025-12-11") -> None:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start, periods=n, freq="4h", tz="UTC")
    drift = np.linspace(0, 40, n)
    noise = np.cumsum(rng.normal(0, 1.8, n))
    wave = 35 * np.sin(np.arange(n) / 18.0)
    close = 2600 + drift + noise + wave
    high = close + rng.uniform(0.8, 5.0, n)
    low = close - rng.uniform(0.8, 5.0, n)
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


def _cache_csv(root: Path, symbol: str, n: int, seed: int = 1) -> Path:
    p = root / "research" / ".cache" / "binance" / "binanceusdm" / symbol / "4h.csv"
    _ohlc_csv(p, n, seed=seed)
    return p


def _tmp_root() -> tempfile.TemporaryDirectory:
    return tempfile.TemporaryDirectory(prefix="themis-s15-")


class TestS15_2_compile_bank(unittest.TestCase):
    def test_compile_every_id_no_network(self):
        def boom(*_a, **_k):
            raise AssertionError("mock compiler networked")

        with patch("socket.socket", side_effect=boom), patch(
            "urllib.request.urlopen", side_effect=boom
        ):
            jobs = compile_bank(SERIES_GOLD, write=False)
        self.assertEqual(set(jobs), set(BANK))
        for cid, job in jobs.items():
            self.assertEqual(job.get("case_id"), cid, cid)
            self.assertEqual(job["source"]["compiler"], "mock")
            path = BANK[cid]["path"]
            if path == "needs_human":
                self.assertEqual(job["status"], "needs_human", cid)
                self.assertEqual(job.get("plan") or [], [])
            elif path == "error":
                self.assertEqual(job["status"], "error", cid)
            else:
                self.assertEqual(job["status"], "ok", cid)
                qs = [p for p in job["plan"] if p["kind"] == "question"]
                self.assertGreaterEqual(len(qs), 2, cid)


class TestS15_3_ask_rivals(unittest.TestCase):
    def test_ask_rows_write_rivals_then_pandas_no_pnl(self):
        with _tmp_root() as td:
            root = Path(td)
            _cache_csv(root, "XAUUSDT", 400, seed=3)
            for cid in ASK_IDS:
                job = compile_english(cid, SERIES_GOLD, write=True, root=root)
                qs = [p for p in job["plan"] if p["kind"] == "question"]
                self.assertGreaterEqual(len(qs), 2, cid)
                self.assertFalse(any(p["kind"] == "strategy" for p in job["plan"]), cid)
            for cid in ("R1", "G2", "U1", "G3"):
                job = compile_english(cid, SERIES_GOLD, write=True, root=root)
                folders = []
                for item in job["plan"]:
                    if item["kind"] != "question":
                        continue
                    spec_path = root / item["yaml"]
                    folder = run_ask(spec_path, root=root, network=False)
                    folders.append(folder)
                    metrics = json.loads((folder / "metrics.json").read_text())
                    meta = json.loads((folder / "meta.json").read_text())
                    self.assertEqual(meta["kind"], "question")
                    self.assertFalse(meta["execution_ready"])
                    self.assertFalse((folder / "trades.csv").exists(), cid)
                    for k in PNL_KEYS:
                        self.assertNotIn(k, metrics, (cid, k))
                    self.assertNotIn("pnl", metrics)
                    self.assertNotIn("net_return", metrics)
                    self.assertNotIn("expectancy", metrics)
                    blob = json.dumps(metrics)
                    self.assertTrue(
                        any(
                            k in blob
                            for k in ("rate", "n_days", '"n"', "n_mondays", "n_bars", "median")
                        ),
                        cid,
                    )
                self.assertGreaterEqual(len(folders), 2, cid)


class TestS15_4_run_rows(unittest.TestCase):
    def test_b0_g1_freeze_strategy_gold_not_eligible(self):
        for cid in RUN_IDS:
            job = compile_english(cid, SERIES_GOLD, write=False)
            self.assertEqual(job["status"], "ok", cid)
            self.assertEqual(job["path"], "run")
            qs = [p for p in job["plan"] if p["kind"] == "question"]
            ss = [p for p in job["plan"] if p["kind"] == "strategy"]
            self.assertGreaterEqual(len(qs), 2, cid)
            self.assertEqual(len(ss), 1, cid)
            self.assertFalse(ss[0]["run_eligible"], cid)
            self.assertFalse(ss[0]["walkforward_eligible"], cid)
            self.assertFalse(ss[0]["tune_eligible"], cid)
            plan = json.dumps(job["plan"])
            self.assertNotIn('"pnl"', plan)
            self.assertFalse(any("bounce_rate" in json.dumps(p) for p in job["plan"] if p["kind"] == "strategy"))


class TestS15_5_family(unittest.TestCase):
    def test_family_rows_no_single_winner_no_tune_on_gold(self):
        for cid in FAMILY_IDS:
            job = compile_english(cid, SERIES_GOLD, write=False)
            self.assertEqual(job["path"], "family", cid)
            ss = [p for p in job["plan"] if p["kind"] == "strategy"]
            qs = [p for p in job["plan"] if p["kind"] == "question"]
            self.assertGreaterEqual(len(qs), 2, cid)
            self.assertGreaterEqual(len(ss), 2, cid)
            self.assertFalse(job.get("single_winner", False), cid)
            for s in ss:
                self.assertFalse(s["tune_eligible"], cid)
                self.assertFalse(s["walkforward_eligible"], cid)
                self.assertFalse(s["run_eligible"], cid)


class TestS15_6_human_and_error(unittest.TestCase):
    def test_f_rows_needs_human(self):
        for cid in HUMAN_IDS:
            job = compile_english(cid, SERIES_GOLD, write=False)
            self.assertEqual(job["status"], "needs_human", cid)
            self.assertEqual(job.get("plan") or [], [])

    def test_a_rows_error_until_kept(self):
        for cid in ERROR_IDS:
            job = compile_english(cid, SERIES_GOLD, write=False)
            self.assertEqual(job["status"], "error", cid)


class TestS15_7_ask_refuses_return(unittest.TestCase):
    def test_ask_refuses_return_question(self):
        with _tmp_root() as td:
            root = Path(td)
            spec = {
                "id": "return-q-test",
                "kind": "question",
                "title": "what is the return / pnl / drawdown",
                "instrument": {
                    "symbol": "XAUUSDT",
                    "venue": "binance",
                    "provider": "binance",
                    "timeframe": "4h",
                },
                "data": {"provider": "binance", "source": "csv", "exchange": "binanceusdm"},
                "discovery": {"start": None, "end": None, "note": "all bars"},
                "holdout": {"start": None, "end": None, "note": "none"},
                "population": "events",
                "condition": [{"kind": "generic"}],
                "outcome": {"name": "pnl", "kind": "flag"},
                "definitions": {"x": "pinned"},
                "stats": ["n"],
                "forbidden": ["quoting_pnl_from_this_ask"],
            }
            path = root / "research" / "questions" / "return-q-test.yaml"
            dump_yaml(spec, path)
            with self.assertRaises(AskError) as ctx:
                run_ask(path, root=root, network=False)
            self.assertIn("return question", str(ctx.exception).lower())

    def test_ask_rejects_strategy_spec(self):
        job = compile_english("G1", SERIES_GOLD, write=False)
        st = job["strategies"][0]
        with _tmp_root() as td:
            root = Path(td)
            path = root / "research" / "specs" / f"{st['id']}.yaml"
            dump_yaml(st, path)
            with self.assertRaises(AskError):
                run_ask(path, root=root, network=False)


class TestS15_8_gold_run_thin(unittest.TestCase):
    def test_gold_run_without_thin_exits_nonzero(self):
        with _tmp_root() as td:
            root = Path(td)
            _cache_csv(root, "XAUUSDT", 1396, seed=7)
            job = compile_english("G1", SERIES_GOLD, write=True, root=root)
            for item in job["plan"]:
                if item["kind"] == "question":
                    run_ask(root / item["yaml"], root=root, network=False)
            st = [p for p in job["plan"] if p["kind"] == "strategy"][0]
            spec_path = root / st["yaml"]
            with self.assertRaises(RunError) as ctx:
                run_strategy(spec_path, root=root, network=False, thin=False)
            msg = str(ctx.exception).lower()
            self.assertTrue("thin" in msg or "run_eligible" in msg)
            self.assertIn("n_bars", msg)
            folder = run_strategy(spec_path, root=root, network=False, thin=True)
            metrics = json.loads((folder / "metrics.json").read_text())
            self.assertTrue(metrics.get("thin"))
            self.assertFalse(metrics.get("kept_possible"))
            self.assertIn("net_return", metrics)
            self.assertIn("pnl", metrics)


class TestS15_9_walkforward_tune_floors(unittest.TestCase):
    def _refuse_wf_tune(self, symbol: str, n: int):
        series = dict(SERIES_GOLD, symbol=symbol)
        with _tmp_root() as td:
            root = Path(td)
            _cache_csv(root, symbol, n, seed=11)
            job = compile_english("G1", series, write=True, root=root)
            st = [p for p in job["plan"] if p["kind"] == "strategy"][0]
            spec_path = root / st["yaml"]
            with self.assertRaises(RunError) as ctx:
                walkforward(spec_path, root=root, network=False)
            wmsg = str(ctx.exception)
            self.assertIn("walkforward", wmsg.lower())
            self.assertIn("4000", wmsg)
            self.assertIn("n_bars", wmsg)
            self.assertIn(str(n), wmsg)
            with self.assertRaises(RunError) as ctx2:
                tune(spec_path, root=root, network=False)
            tmsg = str(ctx2.exception)
            self.assertIn("n_bars", tmsg)
            self.assertTrue("walkforward" in tmsg.lower() or "4000" in tmsg or "tune" in tmsg.lower())

    def test_xau_spy_qqq(self):
        for sym in ("XAUUSDT", "SPYUSDT", "QQQUSDT"):
            self._refuse_wf_tune(sym, 1396)


class TestS15_12_mock_no_network_login(unittest.TestCase):
    def test_mock_never_networks(self):
        def boom(*_a, **_k):
            raise AssertionError("network")

        with patch("socket.create_connection", side_effect=boom), patch(
            "urllib.request.urlopen", side_effect=boom
        ):
            job = compile_english("R1", SERIES_GOLD, write=False)
        self.assertEqual(job["status"], "ok")

    def test_live_backend_refuses_without_login(self):
        with tempfile.TemporaryDirectory() as td:
            auth_path = Path(td) / "auth.json"
            with patch("themis.auth.AUTH_PATH", auth_path), patch(
                "themis.compiler.auth.AUTH_PATH", auth_path
            ):
                logout("xai", path=auth_path)
                logout("openai", path=auth_path)
                with self.assertRaises(CompileError) as ctx:
                    compile_english("R1", SERIES_GOLD, backend="xai", write=False)
                msg = str(ctx.exception).lower()
                self.assertIn("not logged in", msg)
                self.assertIn("no fallback", msg)
                with self.assertRaises(CompileError) as ctx2:
                    compile_english("R1", SERIES_GOLD, backend="openai", write=False)
                self.assertIn("not logged in", str(ctx2.exception).lower())
                rc = main(["compile", "--english", "R1", "--backend", "xai", "--no-write"])
                self.assertEqual(rc, 1)

    def test_whoami_never_prints_token(self):
        rows = whoami()
        blob = json.dumps(rows)
        self.assertNotIn("access_token", blob)
        self.assertNotIn("refresh_token", blob)
        for row in rows:
            self.assertIn("provider", row)
            self.assertIn("logged_in", row)

    def test_unknown_and_bybit_needs_human(self):
        job = compile_english("how do I cook pasta", SERIES_GOLD, write=False)
        self.assertEqual(job["status"], "needs_human")
        job2 = compile_english(
            "bounce after 75% retracement on bybit", SERIES_GOLD, write=False
        )
        self.assertEqual(job2["status"], "needs_human")
        job3 = compile_english("gold on bitget london range", SERIES_GOLD, write=False)
        self.assertEqual(job3["status"], "needs_human")


class TestBtcSolRun(unittest.TestCase):
    def test_btc_run_writes_after_cost_metrics(self):
        series = dict(SERIES_GOLD, symbol="BTCUSDT")
        with _tmp_root() as td:
            root = Path(td)
            _cache_csv(root, "BTCUSDT", 4500, seed=21)
            job = compile_english("G1", series, write=True, root=root)
            for item in job["plan"]:
                if item["kind"] == "question":
                    run_ask(root / item["yaml"], root=root, network=False)
            st = [p for p in job["plan"] if p["kind"] == "strategy"][0]
            self.assertTrue(st["run_eligible"])
            folder = run_strategy(root / st["yaml"], root=root, network=False, thin=False)
            metrics = json.loads((folder / "metrics.json").read_text())
            self.assertIn("net_return", metrics)
            self.assertIn("pnl", metrics)
            self.assertIn("max_drawdown_pct", metrics)
            self.assertIn("n_trades", metrics)
            self.assertIn("not_modeled", metrics)
            self.assertFalse(metrics["execution_ready"])
            self.assertTrue((folder / "trades.csv").exists())


class TestCliAuth(unittest.TestCase):
    def test_cli_whoami(self):
        rc = main(["whoami"])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
