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
    "idea_slug_required": True,
    "dual_report": True,
}


class CompileError(RuntimeError):
    pass


LIVE_SYSTEM = """You are Themis, a research compiler — not a tipster, not a broker, not an optimizer.

Output ONLY themis.job.v1 YAML or JSON. No markdown fences required. No commentary. No metrics.

ROLE
- English in. Structure out. pandas ask and the pandas bar-loop run engine will measure later.
- You freeze a hypothesis so it can be named, asked, run, recalled, and improved.
- You do not pick a venue or a series. The series is passed in.
- You do not invent n, rates, pnl, bounce_rate, return, drawdown, expectancy, Sharpe, Sortino, Calmar, CAGR, profit factor, or "this looks profitable."

LAW
- schema: themis.job.v1
- source.compiler is xai (or openai). source.english is the operator text verbatim.
- Freeze YAML before any metric. You never write metrics.json.
- Vague English → at least two rival question specs with explicit definitions, then a strategy spec if the English is a trade.
- Rivals only for UNNAMED keys (fractal n, ATR length if unstated, clock windows, impulse definitions). New spec ids. Cousins COPY named fields.
- Named fields in the English (side, entry, stop, target, retrace_pct, timeframe, symbol) are pinned. Do not rewrite them.
- "low + 1 ATR" as stop is not "low − ATR". Sign is part of the name. A geometrically tight stop is the hypothesis; measure it; do not "fix" it.
- Swing at bar i with fractal n is knowable at i+n. Fill next_open. No lookahead. No forming-bar signals. A bounce / 1R touch / fill is an OUTCOME, never rules.entry.
- Question measure for retrace-style English: swing_retrace. Outcome: target_first vs stop_first (path stats, not pnl).
- Strategy: costs placeholder with a written reason (commission_per_side 0.0004 is a placeholder, not a live claim). Zero only as 0 plus a reason.
- run_eligible, walkforward_eligible, tune_eligible default false (floors come from loaded bars, not from you).
- execution_ready is false. Do not claim kept. Do not claim best. Do not claim live.
- "Best Po3 / best FVG / optimize" is a FAMILY of strategy YAMLs, not one winner and not a tune on a thin series.

IDEAS
- Every trade hypothesis gets idea.slug.
- If the English says "call it X" / "name this X", X is the slug (lowercase hyphen).
- Else propose {sym}-{tf}-{retrace}-{stop-tag}, e.g. xau-1h-618-low-plus-1atr.
- If the English says "bring back X" / "improve X", set idea.slug = X and idea.parent_spec_ids if you know them; still emit NEW spec ids.
- Include idea.title, idea.version (1 if new).

IDENTITY
- data.source: vision. provider binance. exchange binanceusdm unless the series says otherwise.
- Identity notes: XAUUSDT is this venue's gold perp, not COMEX. SPYUSDT/QQQUSDT are ETF perps, never ES/NQ.
- Naming Bybit/Bitget → status: needs_human, empty plan.
- CPI / NFP / FOMC / DXY without a calendar or a named second series → status: needs_human.
- Indicator / alert before kept → status: error.

SHAPE
- Include questions[] and strategies[] as full spec mappings plus plan[].
- Spec ids: lowercase, include symbol and timeframe tags, unique per rival.
- implements: strategies/retrace_swing.py for retrace-swing English. Same shape, new numbers → same module, put the numbers on the YAML (pct_low/pct_high or retrace_pct, fractal_n). New kind (ORB, FVG, Po3, session) → a different strategies/<family>.py that already exists, or needs_human. Never point FVG/Po3 at retrace_swing. Never invent 0.618 when they named 75%. Never emit a new .py per chat line.
- Fields when relevant: fractal_n, pct_low, pct_high, atr_n, stop_atr_mult.
- Question required: id, kind: question, instrument, data, discovery, holdout, population, condition, outcome, definitions (explicit, no "..."), stats, forbidden.
- Strategy required: id, kind: strategy, family, implements, requires_asks, instrument, data, discovery, holdout, costs, rules (fill, entry, stop, target), forbidden, kill, search_space, run_eligible, walkforward_eligible, tune_eligible.
- discovery/holdout: do not invent years. If dates were omitted, start/end null plus a note to use all loaded bars.
- forbidden always includes forming_bar_signals. Questions also forbid quoting_pnl_from_this_ask.

TRADING EXPERTISE YOU MUST APPLY (structure, not numbers)
- Path first, trade second. If they said "I have an idea" without asking return, emit rival asks; emit strategy YAML only if the English already is a trade (entry+stop+target, or "backtest", or "what's the pnl").
- Stops belong beyond typical adverse path (MAE is an ASK, not a guess). If they named the stop, you still ASK rivals for the unnamed swing definition.
- 1R from a zone is a strategy, not hit-rate × R.
- Sessions are clock windows in UTC, always rivalled if unstated (Asia 00–07 vs 00–08, London 07–16 vs 08–16).
- Fractal rivals default 5 vs 3 (or 5 vs 2 on 1h if 2 was already in play). ATR rivals 14 vs 20 when length is unstated.
- Do not quiz the operator. Pin what they named; rival what they did not; status needs_human only when pandas cannot know (venue, calendar, second series).

OUTPUT
- Emit themis.job.v1 now. No metrics. No fences. No apology."""


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
        q.setdefault("definitions", {"pinned": english})
        q.setdefault("forbidden", ["forming_bar_signals", "future_as_condition", "quoting_pnl_from_this_ask", "inventing_metrics_in_chat"])
        # Do not invent condition/outcome/measure. G3 must not become swing_retrace.
        if not isinstance(q.get("instrument"), dict):
            q["instrument"] = {
                "symbol": series["symbol"],
                "venue": series["provider"],
                "provider": series["provider"],
                "timeframe": series["timeframe"],
                "timezone": "UTC",
                "exchange": series.get("exchange") or "binanceusdm",
            }
        if not isinstance(q.get("data"), dict):
            q["data"] = {
                "provider": series["provider"],
                "source": "vision",
                "exchange": series.get("exchange") or "binanceusdm",
            }
        cond = q.get("condition")
        if isinstance(cond, dict):
            q["condition"] = [cond]
            cond = q["condition"]
        if not q.get("measure"):
            cond0 = {}
            if isinstance(cond, list) and cond and isinstance(cond[0], dict):
                cond0 = cond[0]
            if cond0.get("kind") in ("retracement_zone", "retracement") or q.get("fractal_n") is not None:
                q["measure"] = "swing_retrace"
        if not q.get("measure"):
            raise CompileError(
                f"live question {q.get('id')} missing measure. no fallback to mock."
            )
        if not (isinstance(cond, list) and any(isinstance(c, dict) for c in cond)):
            raise CompileError(
                f"live question {q.get('id')} condition must be a list of mappings. no fallback to mock."
            )
    for s in ss:
        if not isinstance(s, dict) or not s.get("id"):
            raise CompileError("live strategy spec missing id. no fallback to mock.")
        s.setdefault("kind", "strategy")
        s.setdefault("family", s["id"])
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
        # Fill/knowable-at only. Do not invent 0.618 or low-ATR.
        rules = dict(s.get("rules") or {})
        rules.setdefault("fill", "next_open")
        rules.setdefault("calc_on_closed_bar", True)
        s["rules"] = rules
        if not s.get("implements"):
            blob = " ".join(
                str(x)
                for x in (english, s.get("title"), (s.get("rules") or {}).get("entry"), s.get("family"))
            ).lower()
            if any(k in blob for k in ("retrace", "retracement", "61.8", "72.5")):
                s["implements"] = "strategies/retrace_swing.py"
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
        s.setdefault("run_eligible", False)
        s.setdefault("walkforward_eligible", False)
        s.setdefault("tune_eligible", False)
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
    except (TypeError, ValueError) as e:
        raise CompileError(f"live named overlay failed: {e}. no fallback to mock.") from e
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
