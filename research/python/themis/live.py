"""Live xAI compile via grok cli-chat-proxy. HTTP stays in auth.py."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from themis import auth
from themis import named as named_fields
from themis.fees import fee_schedule
from themis.metrics import tick_size
from themis.paths import jobs_dir, questions_dir, repo_root, specs_dir
from themis.spec import dump_yaml

SCHEMA = "themis.job.v1"
GATES = {
    "freeze_yaml_before_metrics": True,
    "rivals_min": 2,
    "ask_before_run": True,
    "tune_requires": "walkforward_eligible",
    "named_fields_pinned": True,
}


class CompileError(RuntimeError):
    pass


LIVE_SYSTEM = """You are Themis compiler. Output ONLY themis.job.v1 YAML or JSON. No markdown fences required. No metrics. No commentary.

Rules:
- schema: themis.job.v1
- source.compiler is xai. Do not invent n, rates, pnl, bounce_rate, return, drawdown, expectancy.
- Freeze YAML structure only. pandas ask and the pandas bar-loop write metrics later.
- The series is passed in. You do not pick a venue or a symbol.
- data.source: vision. provider binance. exchange binanceusdm.
- Vague English must emit at least two rival question specs (kind: question) with explicit definitions, then a strategy spec if the English is a trade.
- Rival definitions for swing highs/lows: fractal n (at least two n values). For ATR: length 14 vs 20.
- Swing at bar i with fractal n is knowable at i+n. Fill next_open. No lookahead. No forming-bar signals.
- Question measure: swing_retrace. Outcome: target_first vs stop_first (path stats, not pnl).
- Strategy: costs are the Binance Regular / VIP0 table (themis.fees), not a placeholder. next_open fills use taker both sides. Zero only as 0 plus a reason. No funding.
- run_eligible, walkforward_eligible, tune_eligible default false (floors come from loaded bars, not from you).
- execution_ready is false. Do not claim kept.
- Include questions[] and strategies[] as full spec mappings plus plan[].
- Spec ids: lowercase, include symbol and timeframe tags.
- implements: strategies/retrace_swing.py for retrace-swing English only. Same shape, new numbers → same module, numbers on the YAML. New kind → existing family module or needs_human. Never default 0.618. Never a new .py per message.
- Fields when relevant: fractal_n, pct_low, pct_high, retrace_pct, atr_n, stop_atr_mult.
- Named fields in the English (stop, target, retrace pct, timeframe, symbol, entry, side) are pinned. Do not rewrite them.
- low + 1 ATR as stop is not low - ATR. Sign is part of the name.
- Rivals only for unnamed keys (fractal n, ATR period if unstated). New spec ids. Cousins copy the named stop/target.
"""


def _strip_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _parse_live_job(text: str) -> dict[str, Any]:
    t = _strip_fence(text)
    obj = None
    try:
        obj = yaml.safe_load(t)
    except Exception:
        obj = None
    if not isinstance(obj, dict):
        start = t.find("{")
        end = t.rfind("}")
        if start >= 0 and end > start:
            try:
                obj = json.loads(t[start : end + 1])
            except json.JSONDecodeError as e:
                raise CompileError(f"live compile output is not YAML/JSON: {e}. no fallback to mock.") from e
    if not isinstance(obj, dict):
        raise CompileError("live compile output is not a mapping. no fallback to mock.")
    if obj.get("schema") and obj.get("schema") != SCHEMA:
        raise CompileError(f"live compile schema {obj.get('schema')!r} != {SCHEMA}. no fallback to mock.")
    return obj


def _materialize(job: dict[str, Any], qs: list[dict], ss: list[dict], *, write: bool, root: Path | None, cid: str) -> dict[str, Any]:
    job.setdefault("schema", SCHEMA)
    job.setdefault("status", "ok")
    job.setdefault("gates", GATES)
    job.setdefault("single_winner", False)
    if write:
        root = root or repo_root()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        job_dir = jobs_dir(root) / f"{stamp}-{cid.lower()}"
        questions_dir(root).mkdir(parents=True, exist_ok=True)
        specs_dir(root).mkdir(parents=True, exist_ok=True)
        job_dir.mkdir(parents=True, exist_ok=True)
        plan = []
        for q in qs:
            rel = f"research/questions/{q['id']}.yaml"
            dump_yaml(dict(q), root / rel)
            plan.append({"kind": "question", "id": q["id"], "purpose": q.get("purpose") or "rival_definition", "yaml": rel})
        for s in ss:
            rel = f"research/specs/{s['id']}.yaml"
            dump_yaml(dict(s), root / rel)
            plan.append({
                "kind": "strategy",
                "id": s["id"],
                "requires": list(s.get("requires_asks") or s.get("requires") or []),
                "yaml": rel,
                "run_eligible": bool(s.get("run_eligible")),
                "walkforward_eligible": bool(s.get("walkforward_eligible")),
                "tune_eligible": bool(s.get("tune_eligible")),
            })
        job["plan"] = plan
        dump_yaml({k: v for k, v in job.items() if k not in ("questions", "strategies")}, job_dir / "job.yaml")
        (job_dir / "job.json").write_text(json.dumps({k: v for k, v in job.items() if k not in ("questions", "strategies")}, indent=2, default=str) + "\n")
        job["written"] = str(job_dir)
    else:
        job["plan"] = (
            [{"kind": "question", "id": q["id"], "purpose": q.get("purpose") or "rival_definition"} for q in qs]
            + [
                {
                    "kind": "strategy",
                    "id": s["id"],
                    "requires": list(s.get("requires_asks") or s.get("requires") or []),
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


def _lift_engine_fields(spec: dict[str, Any]) -> None:
    """Copy fractal_n/atr_n/pct/stop from nested definition/condition to top-level for engines."""
    nested: dict[str, Any] = {}
    for key in ("definition", "definitions"):
        blob = spec.get(key)
        if isinstance(blob, dict):
            nested.update(blob)
    cond = spec.get("condition")
    if isinstance(cond, list) and cond and isinstance(cond[0], dict):
        nested = {**nested, **cond[0]}
    for key in ("fractal_n", "atr_n", "pct_low", "pct_high", "stop_atr_mult"):
        if spec.get(key) is None and nested.get(key) is not None:
            spec[key] = nested[key]


def _compile_live(
    english: str,
    series: dict[str, str],
    *,
    backend: str,
    media: list | None,
    write: bool,
    root: Path | None,
) -> dict[str, Any]:
    if backend != "xai":
        raise CompileError(
            f"live compile backend={backend} is not released. no fallback to mock."
        )
    media_status = []
    if media:
        for m in media:
            media_status.append({**dict(m), "status": "unsupported"})
    user = (
        f"English:\n{english}\n\n"
        f"series: provider={series.get('provider')} symbol={series.get('symbol')} "
        f"timeframe={series.get('timeframe')} exchange={series.get('exchange') or 'binanceusdm'}\n"
        "Emit themis.job.v1 now."
    )
    try:
        text = auth.grok_complete(LIVE_SYSTEM, user)
    except auth.AuthError as e:
        raise CompileError(str(e)) from e
    parsed = _parse_live_job(text)
    parsed.setdefault("source", {})
    if isinstance(parsed["source"], dict):
        parsed["source"]["english"] = english
        parsed["source"]["media"] = media_status
        parsed["source"]["compiler"] = "xai"
        parsed["source"].setdefault("model", "grok-4")
    parsed.setdefault("instrument", {
        "provider": series["provider"],
        "symbol": series["symbol"],
        "timeframe": series["timeframe"],
        "exchange": series.get("exchange") or "binanceusdm",
    })
    qs = list(parsed.get("questions") or [])
    ss = list(parsed.get("strategies") or [])
    if not qs:
        for item in parsed.get("plan") or []:
            if isinstance(item, dict) and item.get("kind") == "question" and item.get("spec"):
                qs.append(item["spec"])
            elif isinstance(item, dict) and item.get("kind") == "strategy" and item.get("spec"):
                ss.append(item["spec"])
    if len(qs) < 2:
        raise CompileError(
            f"live xai compile did not emit >=2 rival questions (got {len(qs)}). no fallback to mock."
        )
    for q in qs:
        if not isinstance(q, dict) or not q.get("id"):
            raise CompileError("live question spec missing id. no fallback to mock.")
        q.setdefault("kind", "question")
        q.setdefault("instrument", {
            "symbol": series["symbol"],
            "venue": series["provider"],
            "provider": series["provider"],
            "timeframe": series["timeframe"],
            "timezone": "UTC",
            "exchange": series.get("exchange") or "binanceusdm",
        })
        q.setdefault("data", {
            "provider": series["provider"],
            "source": "vision",
            "exchange": series.get("exchange") or "binanceusdm",
        })
        q.setdefault("discovery", {"start": None, "end": None, "note": "use all loaded bars"})
        q.setdefault("holdout", {"start": None, "end": None, "note": "holdout null until bars lock a tail"})
        q.setdefault("population", "events")
        q.setdefault("condition", [{"kind": "retracement_zone"}])
        q.setdefault("outcome", {"name": "target_before_stop", "kind": "flag"})
        q.setdefault("definitions", {"pinned": english})
        q.setdefault("stats", ["n", "target_rate", "stop_rate"])
        q.setdefault("forbidden", ["forming_bar_signals", "future_as_condition", "quoting_pnl_from_this_ask", "inventing_metrics_in_chat"])
        q.setdefault("measure", "swing_retrace")
    for s in ss:
        if not isinstance(s, dict) or not s.get("id"):
            raise CompileError("live strategy spec missing id. no fallback to mock.")
        s.setdefault("kind", "strategy")
        s.setdefault("family", s["id"])
        s.setdefault("implements", "strategies/retrace_swing.py")
        s.setdefault("requires_asks", [q["id"] for q in qs])
        s.setdefault("instrument", {
            "symbol": series["symbol"],
            "venue": series["provider"],
            "provider": series["provider"],
            "timeframe": series["timeframe"],
            "timezone": "UTC",
            "exchange": series.get("exchange") or "binanceusdm",
        })
        s.setdefault("data", {
            "provider": series["provider"],
            "source": "vision",
            "exchange": series.get("exchange") or "binanceusdm",
        })
        s.setdefault("discovery", {"start": None, "end": None, "note": "use all loaded bars"})
        s.setdefault("holdout", {"start": None, "end": None, "note": "holdout null until bars lock a tail"})
        s.setdefault("rules", {
            "fill": "next_open",
            "entry": "next open after closed-bar 61.8 percent retrace touch, swing knowable",
            "stop": "1 ATR beyond the swing origin (long: low - ATR; short: high + ATR)",
            "target": "swing extreme (the high for longs, the low for shorts)",
            "calc_on_closed_bar": True,
        })
        fill = (s.get("rules") or {}).get("fill") or "next_open"
        existing = dict(s.get("costs") or {})
        # Python is the law: overlay fee table even if the model wrote a placeholder.
        law = fee_schedule(series["symbol"], fill=fill)
        s["costs"] = {
            **law,
            "slippage_ticks": existing.get("slippage_ticks", 1),
            "tick_size": existing.get("tick_size") if existing.get("tick_size") is not None else tick_size(series.get("symbol"), existing),
        }
        s.setdefault("forbidden", ["forming_bar_signals", "same_bar_fill", "future_pivots"])
        s.setdefault("kill", {"min_trades": 30, "max_drawdown_pct": 40, "min_net_return": 0})
        s.setdefault("search_space", {})
        s.setdefault("run_eligible": False)
        s.setdefault("walkforward_eligible": False)
        s.setdefault("tune_eligible": False)
    for q in qs:
        _lift_engine_fields(q)
    for s in ss:
        _lift_engine_fields(s)
    parsed_named = named_fields.parse_named(english)
    parsed["named"] = parsed_named
    gates = dict(parsed.get("gates") or GATES)
    gates["named_fields_pinned"] = True
    parsed["gates"] = gates
    try:
        named_fields.pin_plan(parsed_named, qs, ss)
    except named_fields.NamedGateError as e:
        parsed["status"] = "error"
        raise CompileError(str(e)) from e
    cid = str(parsed.get("case_id") or "live")
    parsed["questions"] = qs
    parsed["strategies"] = ss
    return _materialize(parsed, qs, ss, write=write, root=root, cid=cid)


def compile_live(
    english: str,
    series: dict[str, str],
    *,
    backend: str,
    media: list | None = None,
    write: bool = False,
    root: Path | None = None,
) -> dict[str, Any]:
    return _compile_live(english, series, backend=backend, media=media, write=write, root=root)
