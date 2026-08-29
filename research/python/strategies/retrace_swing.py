"""Retrace-swing family. Numbers come from the YAML. Shared fill is themis.fill."""
from __future__ import annotations

from typing import Any

import pandas as pd

from themis.ask import fractals
from themis.fill import simulate_exit

# fractal_n always required. Zone is pct_low/pct_high, or retrace_pct (both edges).
REQUIRED_SPEC_KEYS = ("fractal_n",)
FILL = "next_open"


class RetraceSpecError(ValueError):
    pass


def zone_from_spec(spec: dict[str, Any]) -> tuple[int, float, float]:
    n = spec.get("fractal_n")
    if n is None:
        raise RetraceSpecError("retrace_swing requires fractal_n on the YAML")
    low = spec.get("pct_low")
    high = spec.get("pct_high")
    one = spec.get("retrace_pct")
    if low is None and high is None and one is not None:
        low = high = one
    if low is None or high is None:
        raise RetraceSpecError(
            "retrace_swing requires pct_low and pct_high (or retrace_pct) on the YAML. "
            "No 0.618 default."
        )
    lo_f, hi_f = float(low), float(high)
    if lo_f > hi_f:
        lo_f, hi_f = hi_f, lo_f
    return int(n), lo_f, hi_f


def trades(spec: dict[str, Any], df: pd.DataFrame, *, commission: float = 0.0, slip: float = 0.0) -> pd.DataFrame:
    """Next-open fill after zone touch. Stop origin, target extreme. Geometry from YAML."""
    n, pct_low, pct_high = zone_from_spec(spec)
    sh, sl = fractals(df, n)
    rows: list[dict[str, Any]] = []
    used: set[int] = set()
    opens = df["open"].to_numpy()
    highs = df["high"].to_numpy()
    lows = df["low"].to_numpy()
    closes = df["close"].to_numpy()
    idx = df.index

    def fill_trade(side: str, touch: int, origin: float, extreme: float) -> None:
        entry_i = touch + 1
        if entry_i >= len(df):
            return
        row = simulate_exit(
            side,
            entry_i,
            origin,
            extreme,
            opens,
            highs,
            lows,
            closes,
            slip=slip,
            commission=commission,
        )
        if row is None:
            return
        row["entry_ts"] = str(idx[row["entry_i"]])
        row["exit_ts"] = str(idx[row["exit_i"]])
        row["origin"] = origin
        row["extreme"] = extreme
        row["fractal_n"] = n
        row["pct_low"] = pct_low
        row["pct_high"] = pct_high
        rows.append(row)

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
        for i in range(knowable + 1, len(df) - 1):
            if lows[i] <= z_hi and highs[i] >= z_lo:
                touched = i
                break
            if closes[i] < origin:
                break
        if touched is None or touched in used:
            continue
        used.add(touched)
        fill_trade("long", touched, origin, extreme)

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
        for i in range(knowable + 1, len(df) - 1):
            if lows[i] <= z_hi and highs[i] >= z_lo:
                touched = i
                break
            if closes[i] > origin:
                break
        if touched is None or touched in used_s:
            continue
        used_s.add(touched)
        fill_trade("short", touched, origin, extreme)
    return pd.DataFrame(rows)
