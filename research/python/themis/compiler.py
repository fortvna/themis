"""Mock compiler: English in, themis.job.v1 out. Never networks. No spend."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from themis import auth
from themis import named as named_fields
from themis.metrics import tick_size
from themis.paths import jobs_dir, questions_dir, repo_root, specs_dir
from themis.spec import dump_yaml
from themis.live import compile_live, CompileError as LiveCompileError

SCHEMA = "themis.job.v1"
GATES = {
    "freeze_yaml_before_metrics": True,
    "rivals_min": 2,
    "ask_before_run": True,
    "tune_requires": "walkforward_eligible",
    "named_fields_pinned": True,
}

# §9 bank. path: ask | run | family | needs_human | error
BANK: dict[str, dict[str, Any]] = {
    "G1": {
        "path": "run",
        "english": "4h swing high/low, enter retrace 61.8-72.5, stop swing low, target swing high",
        "needles": [("61.8", "72.5", "swing"), ("retrace 61.8",), ("61.8-72.5", "swing")],
    },
    "G2": {
        "path": "ask",
        "english": "Gold points and percent in Asian and London sessions",
        "needles": [("points and percent", "asian"), ("points and percent", "london"), ("gold points", "session")],
    },
    "G3": {
        "path": "ask",
        "english": "Prior-day ATR, lines at -33% and +33%, does price react",
        "needles": [("prior-day atr",), ("prior day atr",), ("-33%", "+33%"), ("atr", "33%")],
    },
    "G4": {
        "path": "family",
        "english": "Find the best Po3, or the best FVG",
        "needles": [("best fvg",), ("find the best po3",), ("best po3, or",), ("or the best fvg",)],
    },
    "R1": {
        "path": "ask",
        "english": "How many times has price bounced after a 75% retracement on this series, this timeframe?",
        "needles": [("75%", "retracement"), ("75% retracement",), ("bounced after a 75",)],
    },
    "R2": {
        "path": "ask",
        "english": "After that zone is touched, how often do we get a reaction within N bars before invalidation?",
        "needles": [("reaction within n bars",), ("before invalidation", "reaction")],
    },
    "R3": {
        "path": "ask",
        "english": "After the zone is touched, what is the MAE / MFE distribution? Where does a 1R stop usually sit?",
        "needles": [("mae", "mfe"), ("1r stop",)],
    },
    "U1": {
        "path": "ask",
        "english": "How much does this series move on Monday?",
        "needles": [("move on monday",), ("how much", "monday")],
    },
    "U2": {
        "path": "ask",
        "english": "How does today behave given yesterday? Does Monday change that?",
        "needles": [("today", "yesterday"), ("monday change that",)],
    },
    "U6": {
        "path": "ask",
        "english": "After a break below the daily open, what % continues vs returns?",
        "needles": [("break below the daily open",), ("daily open", "continues")],
    },
    "S1": {
        "path": "ask",
        "english": "Is Monday's range different from Friday's?",
        "needles": [("monday", "friday", "range"), ("monday's range",)],
    },
    "S2": {
        "path": "ask",
        "english": "After 3 down days, chance of an up day?",
        "needles": [("3 down days",), ("three down days",)],
    },
    "S5": {
        "path": "ask",
        "english": "After a top-decile range day, what is the next day's range?",
        "needles": [("top-decile",), ("top decile range",)],
    },
    "S12": {
        "path": "ask",
        "english": "What fraction of the daily range happens in each session?",
        "needles": [("fraction of the daily range",), ("daily range happens in each session",)],
    },
    "L1": {
        "path": "ask",
        "english": "How do Asia and London behave on this series (range, trend vs fade, where high/low form)?",
        "needles": [("asia and london behave",), ("where high/low form",)],
    },
    "L2": {
        "path": "ask",
        "english": "What share of the daily range is Asia vs London vs NY?",
        "needles": [("share of the daily range", "asia"), ("asia vs london vs ny",)],
    },
    "L3": {
        "path": "ask",
        "english": "If Asia is narrow, what does London usually do?",
        "needles": [("asia is narrow",), ("if asia is narrow",)],
    },
    "L4": {
        "path": "ask",
        "english": "If London breaks Asia, how often does NY continue vs fade?",
        "needles": [("london breaks asia",), ("ny continue vs fade",)],
    },
    "L5": {
        "path": "ask",
        "english": "Is the London open usually a continuation of Asia or a reversal?",
        "needles": [("london open", "continuation"), ("london open", "reversal")],
    },
    "B0": {
        "path": "run",
        "english": "From the 75% retracement, 1:1 R — what is the return / pnl / drawdown?",
        "needles": [("1:1", "return"), ("75% retracement", "pnl"), ("75% retracement", "return")],
    },
    "B1": {
        "path": "family",
        "english": "What is the best PO3 scenario on this series?",
        "needles": [("best po3",), ("best po3 scenario",)],
    },
    "B2": {
        "path": "family",
        "english": "What is the best A+ setup on this series?",
        "needles": [("best a+",), ("a+ setup",)],
    },
    "B3": {
        "path": "family",
        "english": "What is the best opening-range breakout on this series?",
        "needles": [("opening-range breakout",), ("opening range breakout",), ("best orb",)],
    },
    "B4": {
        "path": "family",
        "english": "Does a high prior-day-range Monday ORB beat a normal Monday ORB?",
        "needles": [("monday orb",), ("prior-day-range monday",)],
    },
    "B5": {
        "path": "family",
        "english": "Buy or sell the 61-75% pullback — is there edge after costs?",
        "needles": [("61-75%", "pullback"), ("61–75%", "edge"), ("buy or sell the 61",)],
    },
    "B6": {
        "path": "family",
        "english": "Optimize the kept retracement stop and target",
        "needles": [("optimize the kept",), ("optimize", "retracement stop")],
    },
    "F1": {"path": "needs_human", "english": "How does this series behave on CPI days?", "needles": [("cpi days",), ("on cpi",)], "why": "no event calendar"},
    "F2": {"path": "needs_human", "english": "Monday stats excluding NFP-Friday follow-through", "needles": [("nfp",), ("nfp-friday",)], "why": "no event calendar"},
    "F3": {"path": "needs_human", "english": "How does this series behave on FOMC days?", "needles": [("fomc",)], "why": "no event calendar"},
    "F4": {"path": "needs_human", "english": "This series vs DXY divergence — what happens next?", "needles": [("dxy",)], "why": "no named DXY series"},
    "A1": {"path": "error", "english": "Create the indicator for the winning spec", "needles": [("create the indicator",), ("indicator for the winning",)], "why": "after kept only"},
    "A2": {"path": "error", "english": "Create the alert for the winning spec", "needles": [("create the alert",), ("alert for the winning",)], "why": "after kept only"},
}


class CompileError(RuntimeError):
    pass


def _norm(s: str) -> str:
    s = s.lower()
    s = s.replace("\u2014", "-").replace("\u2013", "-").replace("\u2212", "-")
    s = s.replace("\u201c", '"').replace("\u201d", '"').replace("\u2019", "'")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _sym_tag(symbol: str) -> str:
    return re.sub(r"usdt$", "", symbol.lower())


def _tf_tag(timeframe: str) -> str:
    return timeframe.lower()


def _series_id(cid: str, suffix: str, series: dict[str, str]) -> str:
    return f"{cid.lower()}-{suffix}-{_sym_tag(series['symbol'])}-{_tf_tag(series['timeframe'])}-v1"


def match_case(english: str) -> tuple[str | None, dict[str, Any] | None]:
    raw = english.strip()
    key = raw.upper()
    if key in BANK:
        return key, BANK[key]
    n = _norm(english)
    for cid, rec in BANK.items():
        if _norm(rec["english"]) == n:
            return cid, rec
    hits: list[str] = []
    for cid, rec in BANK.items():
        for group in rec.get("needles") or []:
            if all(_norm(g) in n for g in group):
                hits.append(cid)
                break
    if len(hits) == 1:
        return hits[0], BANK[hits[0]]
    if len(hits) > 1:
        for prefer in ("G1", "G2", "G3", "G4", "B0"):
            if prefer in hits:
                return prefer, BANK[prefer]
        return hits[0], BANK[hits[0]]
    return None, None


def _instrument(series: dict[str, str]) -> dict[str, Any]:
    return {
        "symbol": series["symbol"],
        "venue": series["provider"],
        "provider": series["provider"],
        "timeframe": series["timeframe"],
        "timezone": "UTC",
        "exchange": series.get("exchange") or "binanceusdm",
    }


def _data_block(series: dict[str, str]) -> dict[str, Any]:
    note = f"Binance USD-M {series['symbol']} perp."
    if series["symbol"] == "XAUUSDT":
        note += " Not COMEX. Not another venue."
    if series["symbol"] == "SPYUSDT":
        note += " ETF perp, not ES."
    if series["symbol"] == "QQQUSDT":
        note += " ETF perp, not NQ."
    return {
        "provider": series["provider"],
        "source": "csv",
        "exchange": series.get("exchange") or "binanceusdm",
        "identity_note": note,
    }


def _windows() -> tuple[dict[str, Any], dict[str, Any]]:
    discovery = {"start": None, "end": None, "note": "use all loaded bars of this series; do not invent missing years"}
    holdout = {"start": None, "end": None, "note": "holdout null until bars can lock a tail without emptying discovery"}
    return discovery, holdout


def _question(qid: str, title: str, series: dict[str, str], *, measure: str, definitions: dict, condition: list, outcome: dict, stats: list, population: str = "events", extra: dict | None = None) -> dict[str, Any]:
    discovery, holdout = _windows()
    spec: dict[str, Any] = {
        "id": qid,
        "kind": "question",
        "title": title,
        "instrument": _instrument(series),
        "data": _data_block(series),
        "discovery": discovery,
        "holdout": holdout,
        "population": population,
        "condition": condition,
        "outcome": outcome,
        "definitions": definitions,
        "stats": stats,
        "forbidden": [
            "forming_bar_signals",
            "future_as_condition",
            "quoting_pnl_from_this_ask",
            "inventing_metrics_in_chat",
        ],
        "measure": measure,
    }
    if extra:
        spec.update(extra)
    return spec


def _strategy(sid: str, title: str, series: dict[str, str], *, family: str, implements: str, requires: list[str], rules: dict, extra: dict | None = None) -> dict[str, Any]:
    discovery, holdout = _windows()
    spec: dict[str, Any] = {
        "id": sid,
        "kind": "strategy",
        "title": title,
        "family": family,
        "implements": implements,
        "requires_asks": requires,
        "instrument": _instrument(series),
        "data": _data_block(series),
        "discovery": discovery,
        "holdout": holdout,
        "costs": {
            "commission_per_side": 0.0004,
            "slippage_ticks": 1,
            "tick_size": tick_size(series["symbol"], {}),
            "cost_unit": "fraction_of_price",
            "notes": "Placeholder. No funding. Not a live claim. Zero only as written 0 plus a reason.",
        },
        "rules": rules,
        "forbidden": ["forming_bar_signals", "same_bar_fill", "future_pivots"],
        "kill": {"min_trades": 30, "max_drawdown_pct": 40, "min_net_return": 0},
        "search_space": {},
        "run_eligible": False,
        "walkforward_eligible": False,
        "tune_eligible": False,
    }
    if extra:
        spec.update(extra)
    thin_sym = series["symbol"] in ("XAUUSDT", "SPYUSDT", "QQQUSDT")
    if thin_sym:
        spec["run_eligible"] = False
        spec["walkforward_eligible"] = False
        spec["tune_eligible"] = False
    else:
        spec["run_eligible"] = True
        spec["walkforward_eligible"] = True
        spec["tune_eligible"] = bool(spec.get("search_space"))
    return spec


from themis.cases import build_case


def _build_named_case(english: str, series: dict[str, str], named: dict[str, Any]):
    """Rivals only for unnamed keys. New spec ids. Cousins copy job.named."""
    tag = _sym_tag(series["symbol"])
    tf = _tf_tag(series["timeframe"])
    family = f"{tag}_{tf}_named_retrace"
    pct = float(named.get("retrace_pct") or 0.618)
    pct_high = float(named.get("retrace_pct_high") or pct)
    stop_txt = named_fields._pretty_stop(named["stop"]) if named.get("stop") else "named stop"
    target_txt = named_fields._pretty_target(named["target"]) if named.get("target") else "named target"
    rivals = ((5, 14), (3, 20))
    qs = []
    for n_frac, n_atr in rivals:
        qid = f"{tag}_{tf}_named_n{n_frac}_atr{n_atr}"
        qs.append(
            _question(
                qid,
                f"Confirmed n={n_frac} swing, retrace {pct}, stop {stop_txt}",
                series,
                measure="swing_retrace",
                extra={
                    "family": family,
                    "fractal_n": n_frac,
                    "atr_n": n_atr,
                    "pct_low": pct,
                    "pct_high": pct_high,
                },
                definitions={
                    "swing_high": f"bar i is a swing high if high[i] is strictly the max of i-n..i+n, n={n_frac}. Knowable at i+n.",
                    "swing_low": f"bar i is a swing low if low[i] is strictly the min of i-n..i+n, n={n_frac}. Knowable at i+n.",
                    "stop": stop_txt,
                    "target": target_txt,
                    "pinned": english,
                },
                condition=[{
                    "kind": "retracement_zone",
                    "pct_low": pct,
                    "pct_high": pct_high,
                    "of": "confirmed_swing",
                    "fractal_n": n_frac,
                }],
                outcome={
                    "name": "target_before_stop",
                    "kind": "flag",
                    "target": target_txt,
                    "stop": stop_txt,
                },
                stats=["n", "target_rate", "stop_rate", "neither_rate"],
            )
        )
    sid = f"{tag}_{tf}_named_retrace"
    st = _strategy(
        sid,
        f"Enter {pct} retrace of confirmed n=5 swing, stop {stop_txt}, target {target_txt}",
        series,
        family=family,
        implements="strategies/retrace_swing.py",
        requires=[q["id"] for q in qs],
        rules={
            "fill": "next_open",
            "entry": "next open after closed-bar retrace touch, swing already knowable",
            "stop": stop_txt,
            "target": target_txt,
            "calc_on_closed_bar": True,
        },
        extra={
            "fractal_n": 5,
            "atr_n": 14,
            "pct_low": pct,
            "pct_high": pct_high,
            "definition": {
                "fractal_n": 5,
                "pct_low": pct,
                "pct_high": pct_high,
                "atr_n": 14,
                "stop": stop_txt,
                "take_profit": target_txt,
            },
        },
    )
    note = "named stop/target pinned; rivals are unnamed fractal n and ATR period only"
    return qs, [st], "run", note


def _blank_job(english: str, series: dict[str, str], status: str, note: str, media_status: list | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "status": status,
        "source": {
            "english": english,
            "media": media_status or [],
            "compiler": "mock",
            "model": "mock",
        },
        "instrument": {
            "provider": series["provider"],
            "symbol": series["symbol"],
            "timeframe": series["timeframe"],
            "exchange": series.get("exchange") or "binanceusdm",
        },
        "plan": [],
        "gates": GATES,
        "note": note,
    }


def compile_english(
    english: str,
    series: dict[str, str],
    media: list | None = None,
    *,
    backend: str = "mock",
    write: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    backend = (backend or "mock").lower()
    if backend not in ("mock", "xai", "openai"):
        raise CompileError(f"unknown backend {backend}")
    if backend != "mock":
        try:
            auth.require_login(backend)
        except auth.AuthError as e:
            raise CompileError(str(e)) from e
        try:
            return compile_live(english, series, backend=backend, media=media, write=write, root=root)
        except LiveCompileError as e:
            raise CompileError(str(e)) from e

    media_status = []
    if media:
        for m in media:
            media_status.append({**dict(m), "status": "unsupported"})

    n = _norm(english)
    parsed_named = named_fields.parse_named(english)
    if "bybit" in n or "bitget" in n:
        job = _blank_job(english, series, "needs_human", "v1 venue is Binance. Naming Bybit/Bitget is needs_human.", media_status)
        job["named"] = parsed_named
        if write:
            _write_job(job, root=root)
        return job

    cid, rec = match_case(english)
    if rec is None and not named_fields.has_named_trade_fields(parsed_named):
        job = _blank_job(english, series, "needs_human", "unknown English under mock. do not invent definitions.", media_status)
        job["named"] = parsed_named
        if write:
            _write_job(job, root=root)
        return job

    if rec is not None and rec["path"] == "needs_human":
        job = _blank_job(english, series, "needs_human", rec.get("why") or "needs_human", media_status)
        job["case_id"] = cid
        job["named"] = parsed_named
        job["path"] = "needs_human"
        if write:
            _write_job(job, root=root)
        return job
    if rec is not None and rec["path"] == "error":
        job = _blank_job(english, series, "error", rec.get("why") or "after kept only", media_status)
        job["case_id"] = cid
        job["named"] = parsed_named
        job["path"] = "error"
        if write:
            _write_job(job, root=root)
        return job

    if rec is None:
        qs, ss, path, note = _build_named_case(english, series, parsed_named)
        cid = "NAMED"
    else:
        qs, ss, path, note = build_case(cid, rec, series, english)
    try:
        named_fields.pin_plan(parsed_named, qs, ss)
    except named_fields.NamedGateError as e:
        raise CompileError(str(e)) from e
    job = {
        "schema": SCHEMA,
        "status": "ok",
        "case_id": cid,
        "path": path,
        "note": note,
        "source": {
            "english": english,
            "media": media_status,
            "compiler": "mock",
            "model": "mock",
        },
        "instrument": {
            "provider": series["provider"],
            "symbol": series["symbol"],
            "timeframe": series["timeframe"],
            "exchange": series.get("exchange") or "binanceusdm",
        },
        "plan": [],
        "gates": GATES,
        "single_winner": False,
        "refuse_tune_on_thin": path == "family",
        "named": parsed_named,
    }
    if write:
        root = root or repo_root()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        job_dir = jobs_dir(root) / f"{stamp}-{cid.lower()}"
        qdir = questions_dir(root)
        sdir = specs_dir(root)
        job_dir.mkdir(parents=True, exist_ok=True)
        qdir.mkdir(parents=True, exist_ok=True)
        sdir.mkdir(parents=True, exist_ok=True)
        plan = []
        for q in qs:
            rel = f"research/questions/{q['id']}.yaml"
            dump_yaml(dict(q), root / rel)
            plan.append({"kind": "question", "id": q["id"], "purpose": "rival_definition", "yaml": rel})
        for s in ss:
            rel = f"research/specs/{s['id']}.yaml"
            dump_yaml(dict(s), root / rel)
            plan.append({
                "kind": "strategy",
                "id": s["id"],
                "requires": list(s.get("requires_asks") or []),
                "yaml": rel,
                "run_eligible": bool(s.get("run_eligible")),
                "walkforward_eligible": bool(s.get("walkforward_eligible")),
                "tune_eligible": bool(s.get("tune_eligible")),
            })
        job["plan"] = plan
        dump_yaml(job, job_dir / "job.yaml")
        (job_dir / "job.json").write_text(json.dumps(job, indent=2) + "\n")
        job["written"] = str(job_dir)
    else:
        job["plan"] = (
            [{"kind": "question", "id": q["id"], "purpose": "rival_definition"} for q in qs]
            + [
                {
                    "kind": "strategy",
                    "id": s["id"],
                    "requires": list(s.get("requires_asks") or []),
                    "run_eligible": bool(s.get("run_eligible")),
                    "walkforward_eligible": bool(s.get("walkforward_eligible")),
                    "tune_eligible": bool(s.get("tune_eligible")),
                }
                for s in ss
            ]
        )
        job["questions"] = qs
        job["strategies"] = ss
    return job


def _write_job(job: dict[str, Any], root: Path | None = None) -> None:
    root = root or repo_root()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    cid = job.get("case_id") or "unknown"
    job_dir = jobs_dir(root) / f"{stamp}-{cid}"
    job_dir.mkdir(parents=True, exist_ok=True)
    dump_yaml(job, job_dir / "job.yaml")
    (job_dir / "job.json").write_text(json.dumps(job, indent=2) + "\n")
    job["written"] = str(job_dir)


def compile_bank(series: dict[str, str], *, write: bool = False, root: Path | None = None) -> dict[str, dict[str, Any]]:
    out = {}
    for cid, rec in BANK.items():
        out[cid] = compile_english(cid, series, backend="mock", write=write, root=root)
        out[cid]["case_id"] = cid
    return out
