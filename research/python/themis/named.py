"""Named-field pin for compile. English names a stop; YAML may not rewrite it."""
from __future__ import annotations

import copy
import re
from typing import Any

NAMED_KEYS = ("side", "entry", "stop", "target", "retrace_pct", "timeframe", "symbol")

# Amir's English, used as the acceptance fixture. Not a live re-run.
AMIR_H1_ENGLISH = (
    "find highs and lows of the 1h and wait retrace until 61.8 percent, "
    "is the low + 1 atr as stop loss and the high as take profit"
)


class NamedGateError(RuntimeError):
    """Named field missing or disagrees after overlay. Compile must not status ok."""


def _norm(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("\u2014", "-").replace("\u2013", "-").replace("\u2212", "-")
    s = s.replace("\u00d7", "*").replace("x atr", "* atr")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _pretty_stop(stop: dict[str, Any]) -> str:
    if not stop:
        return ""
    if stop.get("unit") == "ATR" and stop.get("op"):
        k = stop.get("k")
        k_s = "1" if k in (None, 1, 1.0) else f"{k:g}"
        anchor = (stop.get("anchor") or "swing_low").replace("_", " ")
        return f"{anchor} {stop['op']} {k_s}*ATR"
    return (stop.get("formula") or stop.get("anchor") or "").replace("_", " ")


def _pretty_target(target: dict[str, Any] | str) -> str:
    if isinstance(target, dict):
        return (target.get("formula") or target.get("anchor") or "").replace("_", " ")
    return str(target).replace("_", " ")


def _stop_tuple(stop: Any) -> tuple | None:
    """Normalized (anchor, op, k, unit). Sign is part of the name."""
    if stop is None:
        return None
    if isinstance(stop, dict):
        anchor = stop.get("anchor")
        if not anchor:
            return None
        unit = stop.get("unit")
        op = stop.get("op")
        k = stop.get("k")
        if unit == "ATR":
            k = 1.0 if k is None else float(k)
            op = op or "+"
        return (anchor, op, k, unit)
    parsed = parse_stop_text(str(stop))
    if parsed:
        return _stop_tuple(parsed)
    return None


def _target_key(target: Any) -> str | None:
    if target is None:
        return None
    if isinstance(target, dict):
        return target.get("anchor") or target.get("formula")
    t = _norm(str(target))
    if "high" in t and "low" not in t:
        return "swing_high"
    if "low" in t and "high" not in t:
        return "swing_low"
    if "extreme" in t:
        return "swing_high"
    return t or None


def parse_stop_text(text: str) -> dict[str, Any] | None:
    """Parse a stop formula. 'low + 1 ATR' is not 'low - ATR'."""
    n = _norm(text)
    if not n:
        return None
    m = re.search(
        r"(?:(?:the|a|swing)\s+)?(low|high)\s*([+-])\s*(\d+(?:\.\d+)?)?\s*\*?\s*atr(?:\s*\(\s*\d+\s*\))?",
        n,
    )
    if m:
        anchor = "swing_low" if m.group(1) == "low" else "swing_high"
        op = m.group(2)
        k = float(m.group(3)) if m.group(3) else 1.0
        return {
            "anchor": anchor,
            "op": op,
            "k": k,
            "unit": "ATR",
            "formula": f"{anchor} {op} {k:g}*ATR",
        }
    m = re.search(r"long:\s*(?:the\s+|swing\s+)?(low|high)\s*([+-])\s*(\d+(?:\.\d+)?)?\s*\*?\s*atr", n)
    if m:
        anchor = "swing_low" if m.group(1) == "low" else "swing_high"
        op = m.group(2)
        k = float(m.group(3)) if m.group(3) else 1.0
        return {
            "anchor": anchor,
            "op": op,
            "k": k,
            "unit": "ATR",
            "formula": f"{anchor} {op} {k:g}*ATR",
        }
    if re.search(r"\b(swing[_\s-]?low|origin)\b", n) and "atr" not in n:
        return {"anchor": "swing_low", "op": None, "k": None, "unit": None, "formula": "swing_low"}
    if re.search(r"\bswing[_\s-]?high\b", n) and "atr" not in n and "target" not in n:
        return {"anchor": "swing_high", "op": None, "k": None, "unit": None, "formula": "swing_high"}
    return None


def parse_named(english: str) -> dict[str, Any]:
    """MUST: parse English into job.named before write. Only keys the English names."""
    n = _norm(english)
    named: dict[str, Any] = {}
    if not n:
        return named

    m = re.search(r"\b(\d+)\s*(m|h|d|w)\b", n)
    if m:
        named["timeframe"] = f"{m.group(1)}{m.group(2)}"
    elif re.search(r"\bhourly\b", n):
        named["timeframe"] = "1h"
    elif re.search(r"\bdaily\b", n):
        named["timeframe"] = "1d"

    m = re.search(r"\b([a-z]{2,10}usdt)\b", n)
    if m:
        named["symbol"] = m.group(1).upper()

    range_m = re.search(
        r"(?:retrace(?:ment)?(?:\s+(?:until|to|of))?\s+)?(\d+(?:\.\d+)?)\s*[-/]\s*(\d+(?:\.\d+)?)\s*(?:percent|%)?",
        n,
    )
    single_m = re.search(
        r"(?:retrace(?:ment)?(?:\s+(?:until|to|of))?\s+)?(\d+(?:\.\d+)?)\s*(?:percent|%)",
        n,
    )
    if range_m:
        a, b = float(range_m.group(1)), float(range_m.group(2))
        named["retrace_pct"] = a / 100.0 if a > 1 else a
        named["retrace_pct_high"] = b / 100.0 if b > 1 else b
    elif single_m:
        v = float(single_m.group(1))
        named["retrace_pct"] = v / 100.0 if v > 1 else v
    else:
        m = re.search(r"\b(0\.618|0\.725|0\.61|0\.75)\b", n)
        if m:
            named["retrace_pct"] = float(m.group(1))

    stop = None
    stop_clause = None
    m = re.search(
        r"((?:the|a|swing)\s+)?(low|high)\s*[+-]\s*(?:\d+(?:\.\d+)?)?\s*\*?\s*atr.{0,20}(?:as\s+)?stop(?:\s+loss)?",
        n,
    )
    if m:
        stop_clause = m.group(0)
    if stop_clause is None:
        m = re.search(
            r"stop(?:\s+loss)?(?:\s*(?:is|=|:|as))?\s+.{0,40}?(?:(?:the|a|swing)\s+)?(low|high)\s*[+-]\s*(?:\d+(?:\.\d+)?)?\s*\*?\s*atr",
            n,
        )
        if m:
            stop_clause = m.group(0)
    if stop_clause:
        stop = parse_stop_text(stop_clause)
    if stop is None:
        if "stop" in n:
            stop = parse_stop_text(n)
    if stop is None and re.search(r"stop(?:\s+loss)?(?:\s*(?:is|=|:))?\s+(?:the\s+|swing\s+)?low\b", n):
        stop = {"anchor": "swing_low", "op": None, "k": None, "unit": None, "formula": "swing_low"}
    if stop is None and "stop swing low" in n:
        stop = {"anchor": "swing_low", "op": None, "k": None, "unit": None, "formula": "swing_low"}
    if stop:
        named["stop"] = stop

    target = None
    if re.search(
        r"(?:(?:the|a|swing)\s+)?high.{0,30}(?:as\s+)?(?:take\s*profit|take-profit|\btp\b|target)",
        n,
    ) or re.search(
        r"(?:take\s*profit|take-profit|\btp\b|target).{0,30}(?:(?:the|a|swing)\s+)?high",
        n,
    ):
        target = {"anchor": "swing_high", "formula": "swing_high"}
    elif "target swing high" in n:
        target = {"anchor": "swing_high", "formula": "swing_high"}
    elif re.search(r"target(?:\s*(?:is|=|:))?\s+(?:the\s+|swing\s+)?low\b", n):
        target = {"anchor": "swing_low", "formula": "swing_low"}
    if target:
        named["target"] = target

    if "retrace" in n:
        named["entry"] = "retrace_touch"
    if re.search(r"\blong\b", n) and not re.search(r"\bshort\b", n):
        named["side"] = "long"
    elif re.search(r"\bshort\b", n) and not re.search(r"\blong\b", n):
        named["side"] = "short"

    return named


def overlay_named(named: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """MUST overlay job.named onto every YAML after the model, before write."""
    if not named:
        return spec
    spec["named"] = copy.deepcopy(named)
    stop = named.get("stop")
    target = named.get("target")
    if stop:
        rules = dict(spec.get("rules") or {})
        rules["stop"] = _pretty_stop(stop)
        spec["rules"] = rules
        defs = dict(spec.get("definitions") or {})
        defs["stop"] = _pretty_stop(stop)
        spec["definitions"] = defs
        if spec.get("kind") == "strategy":
            extra = dict(spec.get("definition") or {})
            if stop.get("unit") == "ATR":
                extra["stop_atr_mult"] = float(stop.get("k") or 1)
                extra["stop"] = _pretty_stop(stop)
            spec["definition"] = extra
        outcome = dict(spec.get("outcome") or {})
        if outcome:
            outcome["stop"] = _pretty_stop(stop)
            spec["outcome"] = outcome
    if target:
        rules = dict(spec.get("rules") or {})
        rules["target"] = _pretty_target(target)
        spec["rules"] = rules
        defs = dict(spec.get("definitions") or {})
        defs["target"] = _pretty_target(target)
        spec["definitions"] = defs
        outcome = dict(spec.get("outcome") or {})
        if outcome:
            outcome["target"] = _pretty_target(target)
            spec["outcome"] = outcome
    pct = named.get("retrace_pct")
    pct_high = named.get("retrace_pct_high", pct)
    if pct is not None:
        spec["pct_low"] = pct
        spec["pct_high"] = pct_high if pct_high is not None else pct
        conds = []
        for c in spec.get("condition") or []:
            c = dict(c)
            if c.get("kind") == "retracement_zone":
                c["pct_low"] = pct
                c["pct_high"] = pct_high if pct_high is not None else pct
            conds.append(c)
        if conds:
            spec["condition"] = conds
    if named.get("timeframe"):
        inst = dict(spec.get("instrument") or {})
        inst["timeframe"] = named["timeframe"]
        spec["instrument"] = inst
    if named.get("symbol"):
        inst = dict(spec.get("instrument") or {})
        inst["symbol"] = named["symbol"]
        spec["instrument"] = inst
    if named.get("entry"):
        rules = dict(spec.get("rules") or {})
        if spec.get("kind") == "strategy":
            rules.setdefault("entry", "next open after closed-bar retrace touch, swing knowable")
            spec["rules"] = rules
    if named.get("side"):
        spec["side"] = named["side"]
    return spec


def extract_stop(spec: dict[str, Any]) -> dict[str, Any] | None:
    texts = []
    rules = spec.get("rules") or {}
    if rules.get("stop"):
        texts.append(str(rules["stop"]))
    defs = spec.get("definitions") or {}
    if defs.get("stop"):
        texts.append(str(defs["stop"]))
    definition = spec.get("definition") or {}
    if definition.get("stop"):
        texts.append(str(definition["stop"]))
    outcome = spec.get("outcome") or {}
    if outcome.get("stop"):
        texts.append(str(outcome["stop"]))
    parsed = None
    for t in texts:
        p = parse_stop_text(t)
        if p and p.get("unit") == "ATR":
            return p
        if p and parsed is None:
            parsed = p
    return parsed


def extract_target(spec: dict[str, Any]) -> dict[str, Any] | None:
    rules = spec.get("rules") or {}
    if rules.get("target"):
        key = _target_key(rules["target"])
        if key:
            return {"anchor": key, "formula": key}
    defs = spec.get("definitions") or {}
    if defs.get("target"):
        key = _target_key(defs["target"])
        if key:
            return {"anchor": key, "formula": key}
    outcome = spec.get("outcome") or {}
    if outcome.get("target"):
        key = _target_key(outcome["target"])
        if key:
            return {"anchor": key, "formula": key}
    return None


def check_named(named: dict[str, Any], specs: list[dict[str, Any]]) -> None:
    """MUST refuse if a named stop/target is missing or disagrees after overlay.

    Message names the field and both values. Caller turns this into CompileError.
    """
    if not named:
        return
    if not specs:
        for field in ("stop", "target"):
            if field in named:
                raise NamedGateError(
                    f"named field {field} missing after overlay: "
                    f"english={_fmt(named[field])} yaml=missing"
                )
        return
    for spec in specs:
        if named.get("stop"):
            got = extract_stop(spec)
            want = named["stop"]
            if got is None:
                raise NamedGateError(
                    f"named field stop missing after overlay: "
                    f"english={_pretty_stop(want)} yaml=missing"
                )
            if _stop_tuple(got) != _stop_tuple(want):
                raise NamedGateError(
                    f"named field stop disagrees: "
                    f"english={_pretty_stop(want)} yaml={_pretty_stop(got)}"
                )
        if named.get("target"):
            got = extract_target(spec)
            want = named["target"]
            if got is None:
                raise NamedGateError(
                    f"named field target missing after overlay: "
                    f"english={_pretty_target(want)} yaml=missing"
                )
            if _target_key(got) != _target_key(want):
                raise NamedGateError(
                    f"named field target disagrees: "
                    f"english={_pretty_target(want)} yaml={_pretty_target(got)}"
                )


def _fmt(v: Any) -> str:
    if isinstance(v, dict) and v.get("unit") == "ATR":
        return _pretty_stop(v)
    if isinstance(v, dict):
        return _pretty_target(v)
    return str(v)


def pin_plan(named: dict[str, Any], questions: list[dict], strategies: list[dict]) -> None:
    """Overlay then refuse. Mutates lists in place. Same rules for mock, xai, openai."""
    for spec in list(questions) + list(strategies):
        overlay_named(named, spec)
    check_named(named, list(questions) + list(strategies))


def has_named_trade_fields(named: dict[str, Any]) -> bool:
    return bool(named.get("stop") or named.get("target") or named.get("retrace_pct"))
