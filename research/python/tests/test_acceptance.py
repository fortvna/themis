"""§15 acceptance. Fixtures stay in research/.cache, never git."""

from __future__ import annotations

import inspect
import json
import os
import socket
from pathlib import Path

import pytest
import yaml

os.environ.setdefault("THEMIS_ROOT", str(Path(__file__).resolve().parents[3]))

from themis import compiler, eligibility
from themis.compiler import BANK, compile_english
from themis.cli import main as themis_main

ROOT = Path(os.environ["THEMIS_ROOT"])


def ce(english: str = "", symbol: str = "XAUUSDT", bank_id: str | None = None, **kw):
    series = {
        "provider": "binance",
        "symbol": symbol,
        "timeframe": "4h",
        "exchange": "binanceusdm",
    }
    text = bank_id or english
    return compile_english(text, series, write=True, root=ROOT, **kw)


def cli(argv: list[str]) -> int:
    try:
        return int(themis_main(argv) or 0)
    except SystemExit as e:
        return int(e.code or 0)


def test_compiler_source_has_no_urllib():
    src = inspect.getsource(compiler)
    assert "import urllib" not in src
    assert "import requests" not in src
    assert "import httpx" not in src
    assert "from urllib" not in src


def test_compile_maps_every_bank_id_no_network(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("network forbidden in mock compile")

    monkeypatch.setattr(socket, "create_connection", boom)
    for cid, rec in BANK.items():
        path = rec["path"]
        job = ce(bank_id=cid)
        assert job["schema"] == "themis.job.v1"
        if path == "needs_human":
            assert job["status"] == "needs_human"
            assert job["plan"] == []
        elif path == "error":
            assert job["status"] == "error"
        else:
            assert job["status"] == "ok", (cid, job.get("note"), job)
            assert job.get("case_id") == cid
            qs = [p for p in job["plan"] if p["kind"] == "question"]
            ss = [p for p in job["plan"] if p["kind"] == "strategy"]
            if path == "ask":
                assert len(qs) >= 2, cid
                assert len(ss) == 0
            elif path == "run":
                assert len(qs) >= 2, cid
                assert len(ss) == 1, cid
                assert ss[0]["run_eligible"] is False
            elif path == "family":
                assert len(qs) >= 2, cid
                assert len(ss) >= 2, cid
                assert all(s.get("tune_eligible") is False for s in ss)
    jobs = ROOT / "research" / "jobs"
    if jobs.exists():
        assert not list(jobs.rglob("metrics.json"))


def test_unknown_english_needs_human():
    job = ce("paint me a unicorn order block on mars")
    assert job["status"] == "needs_human"
    assert job["plan"] == []


def test_bybit_needs_human():
    job = ce("gold bounce on Bybit")
    assert job["status"] == "needs_human"


def test_english_needles_map():
    samples = {
        "G1": "4h swing high/low, enter retrace 61.8-72.5, stop swing low, target swing high",
        "G2": "Gold points and percent in Asian and London sessions",
        "G3": "Prior-day ATR, lines at -33% and +33%, does price react",
        "G4": "Find the best Po3, or the best FVG",
        "R1": "How many times has price bounced after a 75% retracement on this series, this timeframe?",
        "B0": "From the 75% retracement, 1:1 R — what is the return / pnl / drawdown?",
        "F1": "How does this series behave on CPI days?",
        "A1": "Create the indicator for the winning spec",
    }
    for cid, english in samples.items():
        job = ce(english)
        if cid == "F1":
            assert job["status"] == "needs_human"
        elif cid == "A1":
            assert job["status"] == "error"
        else:
            assert job.get("case_id") == cid, (cid, job.get("case_id"), job.get("status"), job.get("note"))


def test_ask_rows_write_rivals_and_pandas(thin_gold_csv):
    job = ce(bank_id="R1")
    qs = [p for p in job["plan"] if p["kind"] == "question"]
    assert len(qs) >= 2
    for q in qs:
        yp = ROOT / q["yaml"]
        rc = cli(["ask", "--spec", str(yp), "--csv", str(thin_gold_csv), "--offline"])
        assert rc == 0, q
    runs = [
        d
        for d in (ROOT / "research" / "runs").iterdir()
        if d.is_dir() and "r1-" in d.name.lower() and (d / "table.csv").exists()
    ]
    assert len(runs) >= 2
    for d in runs[-2:]:
        metrics = json.loads((d / "metrics.json").read_text())
        assert "n" in metrics or "n_days" in metrics
        for k in ("pnl", "net_return", "expectancy"):
            assert k not in metrics
        assert not (d / "trades.csv").exists()


def test_b0_g1_freeze_strategy_no_return_from_ask():
    for cid in ("G1", "B0"):
        job = ce(bank_id=cid)
        assert job["status"] == "ok"
        ss = [p for p in job["plan"] if p["kind"] == "strategy"]
        assert len(ss) == 1
        assert ss[0]["run_eligible"] is False
        spec = yaml.safe_load((ROOT / ss[0]["yaml"]).read_text())
        assert spec["kind"] == "strategy"
        assert spec["run_eligible"] is False
        rc = cli(["ask", "--spec", str(ROOT / ss[0]["yaml"])])
        assert rc != 0


def test_family_refuse_single_winner_and_tune_gold(thin_gold_csv):
    for cid in ("G4", "B1", "B2", "B3", "B4", "B5", "B6"):
        job = ce(bank_id=cid)
        assert job["status"] == "ok", cid
        ss = [p for p in job["plan"] if p["kind"] == "strategy"]
        assert len(ss) >= 2, cid
        assert job.get("single_winner") is False
        for s in ss:
            assert s.get("tune_eligible") is False
            yp = ROOT / s["yaml"]
            rc = cli(["tune", "--spec", str(yp), "--csv", str(thin_gold_csv)])
            assert rc != 0, (cid, s["id"])


def test_f_needs_human_a_error():
    for cid, status in [
        ("F1", "needs_human"),
        ("F2", "needs_human"),
        ("F3", "needs_human"),
        ("F4", "needs_human"),
        ("A1", "error"),
        ("A2", "error"),
    ]:
        job = ce(bank_id=cid)
        assert job["status"] == status, (cid, job["status"])


def test_ask_refuses_return_question_no_strategy():
    rc = cli(["ask", "--english", "what is the return / pnl / drawdown from 1:1 R"])
    assert rc != 0


def test_run_gold_thin_gates(thin_gold_csv):
    job = ce(bank_id="G1")
    strat = next(p for p in job["plan"] if p["kind"] == "strategy")
    yp = str(ROOT / strat["yaml"])
    runs = ROOT / "research" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    for q in [p for p in job["plan"] if p["kind"] == "question"]:
        dummy = runs / f"dummy-{q['id']}-ask"
        dummy.mkdir(exist_ok=True)
        (dummy / "metrics.json").write_text("{}", encoding="utf-8")
        (dummy / "meta.json").write_text(
            json.dumps({"kind": "question", "spec_id": q["id"]}), encoding="utf-8"
        )
    rc = cli(["run", "--spec", yp, "--csv", str(thin_gold_csv)])
    assert rc != 0
    rc2 = cli(["run", "--spec", yp, "--csv", str(thin_gold_csv), "--thin"])
    assert rc2 == 0
    strat_runs = []
    for d in (ROOT / "research" / "runs").iterdir():
        if not d.is_dir() or not (d / "metrics.json").exists():
            continue
        meta = json.loads((d / "meta.json").read_text())
        if meta.get("kind") == "strategy" and str(meta.get("symbol") or "").upper() == "XAUUSDT":
            strat_runs.append(d)
    assert strat_runs
    metrics = json.loads((sorted(strat_runs)[-1] / "metrics.json").read_text())
    assert metrics.get("thin") is True
    assert metrics.get("kept") is False or metrics.get("kept_possible") is False


def test_walkforward_tune_xau_spy_qqq(thin_gold_csv, spy_csv, qqq_csv):
    for csv_path, symbol in [(thin_gold_csv, "XAUUSDT"), (spy_csv, "SPYUSDT"), (qqq_csv, "QQQUSDT")]:
        job = ce(bank_id="G1", symbol=symbol)
        strat = next(p for p in job["plan"] if p["kind"] == "strategy")
        yp = str(ROOT / strat["yaml"])
        rc = cli(["walkforward", "--spec", yp, "--csv", str(csv_path)])
        assert rc != 0
        rc2 = cli(["tune", "--spec", yp, "--csv", str(csv_path)])
        assert rc2 != 0


def test_walkforward_btc_not_refused_for_symbol(btc_csv):
    job = ce(bank_id="G1", symbol="BTCUSDT")
    strat = next(p for p in job["plan"] if p["kind"] == "strategy")
    yp = ROOT / strat["yaml"]
    spec = yaml.safe_load(yp.read_text())
    spec["search_space"] = {"n": [3, 5]}
    spec["walkforward_eligible"] = True
    yp.write_text(yaml.safe_dump(spec, sort_keys=False))
    rc = cli(["walkforward", "--spec", str(yp), "--csv", str(btc_csv)])
    assert rc == 0


def test_btc_run_writes_after_cost_metrics(btc_csv):
    job = ce(bank_id="B0", symbol="BTCUSDT")
    qs = [p for p in job["plan"] if p["kind"] == "question"]
    strat = next(p for p in job["plan"] if p["kind"] == "strategy")
    runs = ROOT / "research" / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    for q in qs:
        dummy = runs / f"dummy-{q['id']}-ask"
        dummy.mkdir(exist_ok=True)
        (dummy / "metrics.json").write_text("{}", encoding="utf-8")
        (dummy / "meta.json").write_text(
            json.dumps({"kind": "question", "spec_id": q["id"]}), encoding="utf-8"
        )
    yp = ROOT / strat["yaml"]
    spec = yaml.safe_load(yp.read_text())
    spec["run_eligible"] = True
    yp.write_text(yaml.safe_dump(spec, sort_keys=False))
    rc = cli(["run", "--spec", str(yp), "--csv", str(btc_csv)])
    assert rc == 0
    found = None
    for d in sorted((ROOT / "research" / "runs").iterdir()):
        if not (d / "metrics.json").exists():
            continue
        meta = json.loads((d / "meta.json").read_text())
        if meta.get("kind") == "strategy" and meta.get("symbol") == "BTCUSDT":
            found = d
    assert found is not None
    metrics = json.loads((found / "metrics.json").read_text())
    meta = json.loads((found / "meta.json").read_text())
    assert "net_return" in metrics
    assert "pnl" in metrics
    assert meta.get("source") == "csv"
    assert meta.get("n_bars", 0) >= 200


def test_live_compile_refuses_without_login_no_mock_fallback(tmp_path, monkeypatch):
    authp = tmp_path / ".themis" / "auth.json"
    authp.parent.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("themis.auth.AUTH_PATH", authp)
    rc = cli(["compile", "--english", "bounce after 75% retracement", "--backend", "xai"])
    assert rc != 0


def test_whoami_never_prints_token_and_save_keeps_tokens(tmp_path, monkeypatch, capsys):
    from themis import auth as authmod
    authp = tmp_path / ".themis" / "auth.json"
    monkeypatch.setattr(authmod, "AUTH_PATH", authp)
    monkeypatch.setattr("themis.auth.AUTH_PATH", authp)
    data = {
        "xai": {
            "logged_in": True,
            "stub": False,
            "token_present": True,
            "access_token": "secret-access",
            "refresh_token": "secret-refresh",
        },
        "openai": {"logged_in": False},
    }
    saved = authmod.save_auth(data, path=authp)
    stored = json.loads(saved.read_text())
    assert stored["xai"]["access_token"] == "secret-access"
    assert stored["xai"]["refresh_token"] == "secret-refresh"
    assert oct(saved.stat().st_mode)[-3:] == "600"
    rc = cli(["whoami"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "logged_in" in out or "logged-in" in out
    assert "access_token" not in out
    assert "refresh_token" not in out
    assert "secret-access" not in out
    assert "secret-refresh" not in out


def test_no_auth_json_in_repo():
    hits = [h for h in ROOT.rglob("auth.json") if ".venv" not in h.parts and ".themis" not in h.parts]
    assert hits == []


def test_spy_qqq_identity_not_emini():
    spy = eligibility.identity_label("SPYUSDT")
    qqq = eligibility.identity_label("QQQUSDT")
    assert "ETF perp" in spy
    assert "Not ES" in spy
    assert "ETF perp" in qqq
    assert "Not NQ" in qqq
