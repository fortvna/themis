"""pandas ask. Writes run folders. Never pnl. Never trades.csv."""
from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from themis.data import SeriesLoad, load_from_spec
from themis.eligibility import evaluate
from themis.paths import repo_root, runs_dir
from themis.spec import SpecError, dump_yaml, is_return_question, load_spec, PNL_KEYS

PNL_FORBIDDEN = PNL_KEYS | {"trades", "trade_count", "expectancy", "edge"}


class AskError(RuntimeError):
    pass


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _short_hash(spec_id: str) -> str:
    return hashlib.sha1(spec_id.encode()).hexdigest()[:8]


def ci95(p: float, n: int) -> float | None:
    if not n or n <= 0:
        return None
    return round(1.96 * math.sqrt(p * (1 - p) / n), 4)


def _strip_pnl(metrics: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in metrics.items() if k.lower() not in PNL_FORBIDDEN}


def _daily(df: pd.DataFrame) -> pd.DataFrame:
    # UTC date, labeled at session start. Prior-day features must shift(1)
    # (G3 already does). closed/label left so the day's high is not stamped
    # on the next midnight.
    how = {
        "open": ("open", "first"),
        "high": ("high", "max"),
        "low": ("low", "min"),
        "close": ("close", "last"),
    }
    if "volume" in df.columns:
        how["volume"] = ("volume", "sum")
    d = df.resample("1D", closed="left", label="left").agg(**how)
    return d.dropna()


def _session_ohlc(df: pd.DataFrame, start_h: int, end_h: int) -> pd.DataFrame:
    part = df[(df.index.hour >= start_h) & (df.index.hour < end_h)]
    if part.empty:
        return part
    g = part.groupby(part.index.date)
    out = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    out.index = pd.to_datetime(out.index, utc=True)
    return out


def fractals(df: pd.DataFrame, n: int) -> tuple[list[int], list[int]]:
    highs, lows = [], []
    h, l = df["high"].to_numpy(), df["low"].to_numpy()
    for i in range(n, len(df) - n):
        if h[i] == h[i - n : i + n + 1].max() and h[i] > h[i - n : i].max() and h[i] > h[i + 1 : i + n + 1].max():
            highs.append(i)
        if l[i] == l[i - n : i + n + 1].min() and l[i] < l[i - n : i].min() and l[i] < l[i + 1 : i + n + 1].min():
            lows.append(i)
    return highs, lows


def swing_retrace_events(df: pd.DataFrame, n: int, pct_low: float, pct_high: float) -> pd.DataFrame:
    sh, sl = fractals(df, n)
    rows = []
    used: set[int] = set()
    for hi in sh:
        knowable = hi + n
        if knowable >= len(df) - 2:
            continue
        lows_before = [j for j in sl if j < hi]
        if not lows_before:
            continue
        lo = lows_before[-1]
        origin = float(df["low"].iloc[lo])
        extreme = float(df["high"].iloc[hi])
        rng = extreme - origin
        if rng <= 0:
            continue
        z_lo = extreme - pct_high * rng
        z_hi = extreme - pct_low * rng
        touched = None
        for i in range(knowable + 1, len(df)):
            bar = df.iloc[i]
            if bar["low"] <= z_hi and bar["high"] >= z_lo:
                touched = i
                break
            if bar["close"] < origin:
                break
        if touched is None or touched in used:
            continue
        used.add(touched)
        target_hit = stop_hit = False
        bars_to = None
        mae = mfe = 0.0
        entry = float(df["close"].iloc[touched])
        for k in range(touched + 1, len(df)):
            fb = df.iloc[k]
            mae = max(mae, entry - float(fb["low"]))
            mfe = max(mfe, float(fb["high"]) - entry)
            hit_t = fb["high"] >= extreme
            hit_s = fb["low"] <= origin
            if hit_t and hit_s:
                bars_to = k - touched
                break
            if hit_t:
                target_hit, bars_to = True, k - touched
                break
            if hit_s:
                stop_hit, bars_to = True, k - touched
                break
        rows.append({"side": "long", "n": n, "touch_ts": str(df.index[touched]), "target_first": bool(target_hit), "stop_first": bool(stop_hit), "open_end": bars_to is None, "mae": mae, "mfe": mfe})
    used_s: set[int] = set()
    for lo in sl:
        knowable = lo + n
        if knowable >= len(df) - 2:
            continue
        highs_before = [j for j in sh if j < lo]
        if not highs_before:
            continue
        hi = highs_before[-1]
        origin = float(df["high"].iloc[hi])
        extreme = float(df["low"].iloc[lo])
        rng = origin - extreme
        if rng <= 0:
            continue
        z_hi = extreme + pct_high * rng
        z_lo = extreme + pct_low * rng
        touched = None
        for i in range(knowable + 1, len(df)):
            bar = df.iloc[i]
            if bar["low"] <= z_hi and bar["high"] >= z_lo:
                touched = i
                break
            if bar["close"] > origin:
                break
        if touched is None or touched in used_s:
            continue
        used_s.add(touched)
        target_hit = stop_hit = False
        bars_to = None
        mae = mfe = 0.0
        entry = float(df["close"].iloc[touched])
        for k in range(touched + 1, len(df)):
            fb = df.iloc[k]
            mae = max(mae, float(fb["high"]) - entry)
            mfe = max(mfe, entry - float(fb["low"]))
            hit_t = fb["low"] <= extreme
            hit_s = fb["high"] >= origin
            if hit_t and hit_s:
                bars_to = k - touched
                break
            if hit_t:
                target_hit, bars_to = True, k - touched
                break
            if hit_s:
                stop_hit, bars_to = True, k - touched
                break
        rows.append({"side": "short", "n": n, "touch_ts": str(df.index[touched]), "target_first": bool(target_hit), "stop_first": bool(stop_hit), "open_end": bars_to is None, "mae": mae, "mfe": mfe})
    return pd.DataFrame(rows)


def _atr_daily(d: pd.DataFrame, n: int) -> pd.Series:
    prev = d.shift(1)
    tr = pd.concat([d.high - d.low, (d.high - prev.close).abs(), (d.low - prev.close).abs()], axis=1).max(axis=1)
    return tr.rolling(n).mean()


def daily_bars(df: pd.DataFrame) -> pd.DataFrame:
    """UTC daily OHLC from finer bars. Public for hypothesis notebooks."""
    return _daily(df)


# Unnamed-key catalog for this ask family. YAML freezes one row each. Notebook does not invent rivals.
ATR_COMPLETE_RIVALS = (
    {"atr_n": 14, "complete": "day_range"},
    {"atr_n": 20, "complete": "day_range"},
    {"atr_n": 14, "complete": "from_open"},
    {"atr_n": 20, "complete": "from_open"},
)


def atr_path_days(df: pd.DataFrame, *, atr_n: int) -> pd.DataFrame:
    """Daily OHLC + range + from_open + ATR + prior_atr. No month cut. Not pnl."""
    d = _daily(df).copy()
    d["day_range"] = d.high - d.low
    d["from_open"] = np.maximum(d.high - d.open, d.open - d.low)
    d["atr"] = _atr_daily(d, int(atr_n))
    d["prior_atr"] = d["atr"].shift(1)
    return d


def atr_complete_table(
    df: pd.DataFrame,
    *,
    atr_n: int,
    complete: str = "day_range",
    window: str = "last_calendar_month",
) -> pd.DataFrame:
    """Prior-day ATR complete flags. Knowable-at: prior_atr uses shift(1). Not pnl."""
    d2 = atr_path_days(df, atr_n=atr_n).dropna(subset=["prior_atr"]).copy()
    if d2.empty:
        return d2
    last = d2.index.max()
    if window == "last_calendar_month":
        month_start = pd.Timestamp(year=int(last.year), month=int(last.month), day=1, tz="UTC")
        d2 = d2[d2.index >= month_start].copy()
    complete_def = complete if complete in ("from_open", "day_range") else "day_range"
    if complete_def == "from_open":
        d2["excursion"] = d2["from_open"]
    else:
        d2["excursion"] = d2["day_range"]
    d2["complete"] = d2["excursion"] >= d2["prior_atr"]
    d2["range_over_atr"] = d2["excursion"] / d2["prior_atr"].replace(0, np.nan)
    d2["atr_n"] = int(atr_n)
    d2["complete_def"] = complete_def
    return d2


def atr_complete_summary(table: pd.DataFrame) -> dict[str, Any]:
    """One rival's rates. Same keys the run folder writes (minus identity)."""
    nn = int(len(table))
    k = int(table["complete"].sum()) if nn and "complete" in table.columns else 0
    rate = (k / nn) if nn else None
    complete_def = None
    atr_n = None
    if nn:
        if "complete_def" in table.columns:
            complete_def = str(table["complete_def"].iloc[0])
        if "atr_n" in table.columns:
            atr_n = int(table["atr_n"].iloc[0])
    return {
        "n": nn,
        "n_days": nn,
        "n_complete": k,
        "complete_rate": None if rate is None else round(float(rate), 4),
        "complete_rate_ci95": ci95(float(rate), nn) if rate is not None else None,
        "atr_n": atr_n,
        "complete_def": complete_def,
        "window_start": str(table.index.min()) if nn else None,
        "window_end": str(table.index.max()) if nn else None,
        "median_range_over_atr": (
            round(float(table["range_over_atr"].median()), 4)
            if nn and "range_over_atr" in table.columns
            else None
        ),
    }


def atr_complete_rivals(
    df: pd.DataFrame,
    *,
    rivals: tuple[dict[str, Any], ...] | list[dict[str, Any]] | None = None,
    window: str = "last_calendar_month",
) -> tuple[pd.DataFrame, dict[tuple[int, str], pd.DataFrame]]:
    """All unnamed-key rivals. Logic here; notebook only displays."""
    spec = tuple(rivals) if rivals is not None else ATR_COMPLETE_RIVALS
    tables: dict[tuple[int, str], pd.DataFrame] = {}
    rows = []
    for r in spec:
        n = int(r["atr_n"])
        how = str(r["complete"])
        t = atr_complete_table(df, atr_n=n, complete=how, window=window)
        tables[(n, how)] = t
        rows.append(atr_complete_summary(t))
    return pd.DataFrame(rows), tables


def plot_range_vs_prior_atr(table: pd.DataFrame, *, title: str | None = None):
    """Display helper. No hypothesis math."""
    ax = table[["day_range", "prior_atr"]].plot(
        figsize=(10, 4),
        title=title or "daily range vs prior-day ATR",
    )
    ax.set_ylabel("price points")
    return ax


def measure(spec: dict[str, Any], series: SeriesLoad) -> tuple[dict[str, Any], pd.DataFrame]:
    df = series.df
    kind = spec.get("measure") or (spec.get("condition") or [{}])[0].get("kind")
    extra = spec
    table = pd.DataFrame()
    metrics: dict[str, Any] = {"kind": "question", "spec_id": spec.get("id")}

    if kind == "swing_retrace" or kind == "retracement_zone" and extra.get("fractal_n"):
        n = int(extra.get("fractal_n") or (spec.get("condition") or [{}])[0].get("fractal_n") or 5)
        pct_low = float(extra.get("pct_low") or (spec.get("condition") or [{}])[0].get("pct_low") or 0.618)
        pct_high = float(extra.get("pct_high") or (spec.get("condition") or [{}])[0].get("pct_high") or 0.725)
        ev = swing_retrace_events(df, n, pct_low, pct_high)
        table = ev
        nn = int(len(ev))
        metrics.update({
            "n": nn,
            "target_rate": round(float(ev["target_first"].mean()), 4) if nn else None,
            "stop_rate": round(float(ev["stop_first"].mean()), 4) if nn else None,
            "neither_rate": round(float((~ev["target_first"] & ~ev["stop_first"]).mean()), 4) if nn else None,
            "target_rate_ci95": ci95(float(ev["target_first"].mean()), nn) if nn else None,
            "stop_rate_ci95": ci95(float(ev["stop_first"].mean()), nn) if nn else None,
            "fractal_n": n,
            "note": "path stats only. not pnl. not edge.",
        })
        if extra.get("want_mae_mfe") and nn:
            metrics["median_mae"] = round(float(ev["mae"].median()), 4)
            metrics["median_mfe"] = round(float(ev["mfe"].median()), 4)
        return _strip_pnl(metrics), table

    if kind in ("bounce_retrace", "reaction_horizon") or extra.get("question_ref") in ("R1", "R2", "R3"):
        n = int(extra.get("impulse_bars") or 12)
        pct = float(extra.get("retrace_pct") or 0.75)
        ev = swing_retrace_events(df, max(3, n // 4), pct, pct)
        horizon = extra.get("horizon_bars")
        table = ev
        nn = int(len(ev))
        bounce = float(ev["target_first"].mean()) if nn else None
        metrics.update({
            "n": nn,
            "bounce_rate": round(bounce, 4) if bounce is not None else None,
            "bounce_rate_ci95": ci95(bounce, nn) if bounce is not None else None,
            "note": "bounce/path is an outcome. not an entry. not pnl.",
        })
        if extra.get("want_mae_mfe") and nn:
            metrics["median_mae"] = round(float(ev["mae"].median()), 4)
            metrics["median_mfe"] = round(float(ev["mfe"].median()), 4)
        if horizon and nn:
            metrics["horizon_bars"] = int(horizon)
            metrics["p_reaction"] = metrics["bounce_rate"]
            metrics["p_invalidated"] = round(float(ev["stop_first"].mean()), 4)
        return _strip_pnl(metrics), table

    if kind in ("session_range", "session_clock") or extra.get("windows_utc"):
        win = extra.get("windows_utc") or (spec.get("condition") or [{}])[0].get("windows_utc") or {"asia": [0, 7], "london": [7, 16], "ny": [16, 24]}
        d = _daily(df)
        a = _session_ohlc(df, int(win["asia"][0]), int(win["asia"][1]))
        l = _session_ohlc(df, int(win["london"][0]), int(win["london"][1]))
        ny = _session_ohlc(df, int(win["ny"][0]), int(win["ny"][1]))
        idx = d.index.intersection(a.index).intersection(l.index).intersection(ny.index)
        d, a, l, ny = d.loc[idx], a.loc[idx], l.loc[idx], ny.loc[idx]
        def rng(x):
            return x.high - x.low
        dr = rng(d).replace(0, np.nan)
        table = pd.DataFrame({"asia_pts": rng(a), "london_pts": rng(l), "ny_pts": rng(ny), "day_pts": rng(d)})
        n_days = int(len(d))
        metrics.update({
            "n_days": n_days,
            "asia_median_pts": round(float(rng(a).median()), 4) if n_days else None,
            "london_median_pts": round(float(rng(l).median()), 4) if n_days else None,
            "ny_median_pts": round(float(rng(ny).median()), 4) if n_days else None,
            "asia_share": round(float((rng(a) / dr).median()), 4) if n_days else None,
            "london_share": round(float((rng(l) / dr).median()), 4) if n_days else None,
            "windows_utc": win,
            "note": "4h clocks are coarse. descriptive. not pnl.",
        })
        if extra.get("question_ref") == "L1" and n_days:
            hi_asia = (a.high >= l.high) & (a.high >= ny.high)
            lo_asia = (a.low <= l.low) & (a.low <= ny.low)
            metrics["p_day_high_in_asia"] = round(float(hi_asia.mean()), 4)
            metrics["p_day_low_in_asia"] = round(float(lo_asia.mean()), 4)
        return _strip_pnl(metrics), table.reset_index(names="ts")

    if kind == "atr_react" or extra.get("question_ref") == "G3":
        n_atr = int(extra.get("atr_n") or 14)
        react = extra.get("react") or "through"
        d = _daily(df).copy()
        d["atr"] = _atr_daily(d, n_atr)
        d["line_hi"] = d.close.shift(1) + 0.33 * d.atr.shift(1)
        d["line_lo"] = d.close.shift(1) - 0.33 * d.atr.shift(1)
        d2 = d.dropna()
        touch_hi = d2.high >= d2.line_hi
        touch_lo = d2.low <= d2.line_lo
        if react == "through":
            react_hi = touch_hi & (d2.close < d2.line_hi)
            react_lo = touch_lo & (d2.close > d2.line_lo)
        else:
            react_hi = touch_hi & ((d2.high - d2.close) >= 0.5 * d2.atr.shift(1).reindex(d2.index))
            react_lo = touch_lo & ((d2.close - d2.low) >= 0.5 * d2.atr.shift(1).reindex(d2.index))
        n_hi = int(touch_hi.sum())
        n_lo = int(touch_lo.sum())
        table = d2[["open", "high", "low", "close", "atr", "line_hi", "line_lo"]].reset_index(names="ts")
        metrics.update({
            "n_days": int(len(d2)), "n_touch_plus33": n_hi, "n_touch_minus33": n_lo,
            "react_plus": round(float(react_hi[touch_hi].mean()), 4) if n_hi else None,
            "react_minus": round(float(react_lo[touch_lo].mean()), 4) if n_lo else None,
            "atr_n": n_atr, "react": react, "note": "condition knowable at prior daily close. not a trade.",
        })
        return _strip_pnl(metrics), table

    if kind == "atr_complete" or extra.get("measure") == "atr_complete":
        n_atr = int(extra.get("atr_n") or 14)
        complete_def = extra.get("complete") or extra.get("complete_def") or "day_range"
        win = extra.get("window") or "last_calendar_month"
        d2 = atr_complete_table(df, atr_n=n_atr, complete=complete_def, window=win)
        stats = atr_complete_summary(d2)
        table = d2.reset_index(names="ts")
        keep = [c for c in ("ts", "open", "high", "low", "close", "prior_atr", "day_range", "from_open", "complete", "range_over_atr") if c in table.columns]
        table = table[keep]
        metrics.update(stats)
        metrics["window"] = win
        metrics["note"] = "prior-day ATR knowable at prior daily close. complete is a path flag. not pnl."
        return _strip_pnl(metrics), table

    d = _daily(df).copy()
    d["range"] = d.high - d.low
    d["up"] = d.close > d.open
    d["downday"] = d.close < d.open
    d["dow"] = d.index.dayofweek
    d["prev_up"] = d.up.shift(1)
    d["prev_range"] = d.range.shift(1)
    day_kind = extra.get("day_kind") or kind
    session_kind = extra.get("session_kind")

    if extra.get("question_ref") in ("U1", "S1") or kind == "weekday_range" or kind == "weekday":
        mon = d[d.dow == 0]
        fri = d[d.dow == 4]
        table = d.reset_index(names="ts")
        if extra.get("question_ref") == "S1":
            metrics.update({"n_mon": int(len(mon)), "n_fri": int(len(fri)), "median_mon_pts": round(float(mon.range.median()), 4) if len(mon) else None, "median_fri_pts": round(float(fri.range.median()), 4) if len(fri) else None, "calendar": extra.get("calendar") or "utc"})
        else:
            metrics.update({"n_mondays": int(len(mon)), "median_range_pts": round(float(mon.range.median()), 4) if len(mon) else None, "median_range_pct": round(float((mon.range / mon.open).median() * 100), 4) if len(mon) else None, "calendar": extra.get("calendar") or "utc"})
        return _strip_pnl(metrics), table

    if extra.get("question_ref") == "U2" or day_kind == "given_yesterday":
        both = d.dropna(subset=["prev_up"])
        p_cont = float(both.loc[both.prev_up == True, "up"].mean()) if len(both) else None
        mon2 = both[both.dow == 0]
        p_mon = float(mon2.loc[mon2.prev_up == True, "up"].mean()) if len(mon2) else None
        metrics.update({"n": int(len(both)), "p_up_given_up": None if p_cont is None else round(p_cont, 4), "p_up_given_up_ci95": ci95(p_cont, int(len(both))) if p_cont is not None else None, "n_monday": int(len(mon2)), "p_up_given_up_monday": None if p_mon is None or (isinstance(p_mon, float) and np.isnan(p_mon)) else round(p_mon, 4)})
        return _strip_pnl(metrics), both.reset_index(names="ts")

    if extra.get("question_ref") == "U6" or day_kind == "break_daily_open":
        broke_day = d.low < d.open
        n_b = int(broke_day.sum())
        if extra.get("continue_def") == "range_extension":
            cont = (d.low < d.open) & (d.high - d.open > d.open - d.low)
            retn = broke_day & ~cont
        else:
            cont = (d.close < d.open) & broke_day
            retn = (d.close >= d.open) & broke_day
        metrics.update({"n_breaks": n_b, "continue_rate": round(float(cont.sum() / n_b), 4) if n_b else None, "return_rate": round(float(retn.sum() / n_b), 4) if n_b else None, "continue_rate_ci95": ci95(float(cont.sum() / n_b), n_b) if n_b else None, "continue_def": extra.get("continue_def") or "close_still_below", "note": "return here means price came back through the daily open. not pnl."})
        return _strip_pnl(metrics), d.reset_index(names="ts")

    if extra.get("question_ref") == "S2" or day_kind == "three_down":
        down3 = d.downday.shift(1) & d.downday.shift(2) & d.downday.shift(3)
        sample = d[down3.fillna(False)]
        up = sample.close > sample.low.shift(1).reindex(sample.index) if extra.get("up_def") == "close_vs_prior_low" else sample.up
        n = int(len(sample))
        p = float(up.mean()) if n else None
        metrics.update({"n": n, "p_up": None if p is None else round(p, 4), "p_up_ci95": ci95(p, n) if p is not None else None})
        return _strip_pnl(metrics), sample.reset_index(names="ts")

    if extra.get("question_ref") == "S5" or day_kind == "top_decile":
        look = int(extra.get("lookback") or 20)
        q90 = d.range.shift(1).rolling(look).quantile(0.9)
        top = d[d.prev_range >= q90]
        n = int(len(top))
        metrics.update({"n": n, "lookback": look, "next_median_pts": round(float(top.range.median()), 4) if n else None, "typical_median_pts": round(float(d.range.median()), 4)})
        return _strip_pnl(metrics), top.reset_index(names="ts")

    if session_kind == "asia_narrow" or extra.get("question_ref") == "L3":
        a = _session_ohlc(df, 0, 7)
        l = _session_ohlc(df, 7, 16)
        idx = a.index.intersection(l.index)
        a, l = a.loc[idx], l.loc[idx]
        ar, lr = a.high - a.low, l.high - l.low
        if extra.get("narrow") == "half_atr":
            dd = _daily(df).reindex(idx)
            atr = _atr_daily(dd, 14)
            narrow = ar < 0.5 * atr.reindex(ar.index)
        else:
            narrow = ar <= ar.quantile(0.25)
        metrics.update({"n_narrow": int(narrow.sum()), "london_median_if_asia_narrow": round(float(lr[narrow].median()), 4) if narrow.any() else None, "london_median_otherwise": round(float(lr[~narrow].median()), 4) if (~narrow).any() else None})
        return _strip_pnl(metrics), pd.DataFrame({"asia_pts": ar, "london_pts": lr, "narrow": narrow}).reset_index(names="ts")

    if session_kind == "london_breaks_asia" or extra.get("question_ref") == "L4":
        a = _session_ohlc(df, 0, 7)
        l = _session_ohlc(df, 7, 16)
        ny = _session_ohlc(df, 16, 24)
        idx = a.index.intersection(l.index).intersection(ny.index)
        a, l, ny = a.loc[idx], l.loc[idx], ny.loc[idx]
        brk = ((l.high > a.high) | (l.low < a.low)) if extra.get("break_def") == "wick" else ((l.close > a.high) | (l.close < a.low))
        cont = ny.high > l.high
        fade = ny.high < l.high
        nb = int(brk.sum())
        metrics.update({"n_london_breaks_asia": nb, "ny_continue": round(float(cont[brk].mean()), 4) if nb else None, "ny_fade": round(float(fade[brk].mean()), 4) if nb else None})
        return _strip_pnl(metrics), pd.DataFrame({"break": brk, "ny_continue": cont, "ny_fade": fade}).reset_index(names="ts")

    if session_kind == "london_open" or extra.get("question_ref") == "L5":
        open_h = int(extra.get("london_open_hour") or 7)
        a = _session_ohlc(df, 0, open_h)
        l = _session_ohlc(df, open_h, 16)
        idx = a.index.intersection(l.index)
        a, l = a.loc[idx], l.loc[idx]
        asia_up = a.close > a.open
        lon_dir = l.close > l.open
        metrics.update({"n": int(len(a)), "p_london_up_given_asia_up": round(float(lon_dir[asia_up].mean()), 4) if asia_up.any() else None, "p_london_up_given_asia_down": round(float(lon_dir[~asia_up].mean()), 4) if (~asia_up).any() else None, "london_open_hour": open_h})
        return _strip_pnl(metrics), pd.DataFrame({"asia_up": asia_up, "london_up": lon_dir}).reset_index(names="ts")

    d = _daily(df)
    metrics.update({"n_bars": int(len(df)), "n_days": int(len(d)), "median_day_range_pts": round(float((d.high - d.low).median()), 4) if len(d) else None, "note": "generic descriptive ask. not pnl."})
    return _strip_pnl(metrics), d.reset_index(names="ts")


def run_ask(spec_path: str | Path, *, root: Path | None = None, network: bool = True, stage: str = "discovery") -> Path:
    spec = load_spec(spec_path)
    if spec.get("kind") != "question":
        raise AskError("ask rejects strategy specs")
    blob = " ".join(str(spec.get(k) or "") for k in ("title", "hypothesis", "id", "english")).lower()
    return_needles = (
        "what is the return",
        "pnl",
        "drawdown",
        "expectancy",
        "edge after costs",
        "1:1 r",
        "1:1r",
    )
    if any(n in blob for n in return_needles):
        raise AskError("ask refuses a return question with no strategy spec")
    root = root or repo_root()
    try:
        series = load_from_spec(spec, root=root, network=network)
    except Exception as e:
        raise AskError(f"data load failed: {e}") from e
    el = evaluate(series.n_bars)
    if not el.ask_ok:
        raise AskError(el.refuse_message("ask"))
    metrics, table = measure(spec, series)
    metrics = _strip_pnl(metrics)
    metrics["identity"] = series.identity
    metrics["n_bars"] = series.n_bars
    folder = runs_dir(root) / f"{_utc_stamp()}-{spec['id']}-{_short_hash(spec['id'])}"
    folder.mkdir(parents=True, exist_ok=True)
    dump_yaml(spec, folder / "spec.yaml")
    meta = {"kind": "question", "stage": stage, "execution_ready": False, "spec_id": spec["id"], "actual_start": series.actual_start, "actual_end": series.actual_end, "n_bars": series.n_bars, "provider": series.provider, "source": series.source, "symbol": series.symbol, "timeframe": series.timeframe, "exchange": series.exchange, "thin": el.thin}
    (folder / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    (folder / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    if table is not None and len(table):
        table.to_csv(folder / "table.csv", index=False)
    else:
        pd.DataFrame([{"n": metrics.get("n") or metrics.get("n_days") or 0}]).to_csv(folder / "table.csv", index=False)
    (folder / "engine.log").write_text("ask pandas. no pnl. no trades.\n")
    (folder / "status.json").write_text(json.dumps({"ok": True, "kind": "question"}, indent=2) + "\n")
    if (folder / "trades.csv").exists():
        (folder / "trades.csv").unlink()
    from themis.report import write_report
    write_report(folder, root=root)
    return folder
