"""R1 bounce_retrace rivals must honor impulse_bars / impulse_atr / bounce / retrace_pct.

open-spec.md names the rivals (12-bar 1.5 ATR vs 8-bar 1.2 ATR; close-through 50%
vs 1x ATR reaction) but is silent on exact impulse/bounce geometry. This module
pins the cases.py R1 reading:

* Impulse: a window of N=impulse_bars closed bars whose last bar is the window
  extreme, origin is the opposite extreme earlier in the window, and
  (extreme-origin) >= K * ATR with K=impulse_atr. ATR is SMA of true range on
  this timeframe, length atr_n (default 14), knowable at the bar before the
  impulse completes (no look-ahead).
* Zone: retrace_pct of that frozen impulse range. Touch = first closed bar
  after the impulse is knowable whose range intersects the zone.
* Bounce through_50: close back through the midpoint of origin and extreme.
* Bounce atr: favorable excursion of 1*ATR from the zone, ATR knowable at touch.
* Bounce is an outcome flag, not an entry, not pnl. Missing retrace_pct errors
  (no silent 0.618 / 0.75).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from themis.ask import AskError, measure
from themis.data import SeriesLoad
from themis.spec import PNL_KEYS

SEED = 20260903
R1A = {"impulse_bars": 12, "impulse_atr": 1.5, "bounce": "through_50", "retrace_pct": 0.75}
R1B = {"impulse_bars": 8, "impulse_atr": 1.2, "bounce": "atr", "retrace_pct": 0.75}


def _synth_ohlc(seed: int = SEED) -> pd.DataFrame:
    """One N-bar K-ATR long impulse, 75% touch, through_50 close, not 1x ATR MFE.

    Warmup bars sit in a 1.0-wide channel (99.5–100.5) so ATR14 ~ 1.0 and no
    window of 8 or 12 has range >= 1.2. Then one completing bar prints a 102
    high: origin 99.5, range 2.5, which clears both 8-bar 1.2 ATR and 12-bar
    1.5 ATR. The next closed bar intersects the 75% zone (100.125) and closes
    through the 50% midpoint (100.75) with high 101.00, which is < 1x ATR from
    the zone. Trailing bars stay inside a 0.9-wide channel so neither cousin
    mints a second event and the atr cousin never gets a 1x ATR reaction.
    """
    rng = np.random.default_rng(seed)
    rows: list[tuple[float, float, float, float]] = []

    def add(o: float, h: float, l: float, c: float) -> None:
        rows.append((float(o), max(h, o, c), min(l, o, c), float(c)))

    px = 100.0
    for _ in range(40):
        j = float(rng.uniform(-0.03, 0.03))
        c = float(np.clip(px + j, 99.58, 100.42))
        add(px, 100.5, 99.5, c)
        px = c
    add(px, 102.0, max(px - 0.05, 99.9), 101.7)
    add(100.80, 101.00, 100.10, 100.90)
    px = 100.90
    for _ in range(30):
        j = float(rng.uniform(-0.03, 0.03))
        c = float(np.clip(px + j, 100.15, 100.95))
        add(px, 101.00, 100.10, c)
        px = c
    idx = pd.date_range("2026-01-01", periods=len(rows), freq="4h", tz="UTC")
    o, h, l, c = zip(*rows)
    return pd.DataFrame({"open": o, "high": h, "low": l, "close": c}, index=idx)


def _series(df: pd.DataFrame) -> SeriesLoad:
    return SeriesLoad(
        df=df,
        provider="binance",
        symbol="XAUUSDT",
        timeframe="4h",
        exchange="binanceusdm",
        source="synth",
        actual_start=str(df.index.min()),
        actual_end=str(df.index.max()),
        n_bars=int(len(df)),
        identity={"symbol": "XAUUSDT", "timeframe": "4h", "source": "synth"},
    )


def _spec(sid: str, **cfg) -> dict:
    return {
        "id": sid,
        "kind": "question",
        "measure": "bounce_retrace",
        "question_ref": "R1",
        **cfg,
    }


def _ask(df: pd.DataFrame, sid: str, cfg: dict) -> dict:
    metrics, _table = measure(_spec(sid, **cfg), _series(df))
    return metrics


def test_r1_cousins_disagree_on_n_or_bounce_rate():
    df = _synth_ohlc()
    a = _ask(df, "r1-imp12-through50", R1A)
    b = _ask(df, "r1-imp8-atr", R1B)
    for m, cfg in ((a, R1A), (b, R1B)):
        assert m["impulse_bars"] == cfg["impulse_bars"]
        assert m["impulse_atr"] == cfg["impulse_atr"]
        assert m["bounce"] == cfg["bounce"]
        assert m["retrace_pct"] == cfg["retrace_pct"]
        assert m["atr_n"] == 14
        for k in PNL_KEYS | {"trades", "trade_count", "expectancy", "edge"}:
            assert k not in m
    assert a["n"] != b["n"] or a["bounce_rate"] != b["bounce_rate"]
    assert a["n"] >= 1 or b["n"] >= 1


def test_identical_definitions_identical_metrics():
    df = _synth_ohlc()
    a = _ask(df, "twin-a", R1A)
    b = _ask(df, "twin-b", dict(R1A))
    assert a["n"] == b["n"]
    assert a["bounce_rate"] == b["bounce_rate"]
    assert a["impulse_bars"] == b["impulse_bars"]
    assert a["impulse_atr"] == b["impulse_atr"]
    assert a["bounce"] == b["bounce"]
    assert a["retrace_pct"] == b["retrace_pct"]
    c = _ask(df, "twin-c", R1B)
    d = _ask(df, "twin-d", dict(R1B))
    assert c["n"] == d["n"]
    assert c["bounce_rate"] == d["bounce_rate"]


def test_missing_retrace_pct_raises():
    df = _synth_ohlc()
    spec = _spec(
        "missing-pct",
        impulse_bars=12,
        impulse_atr=1.5,
        bounce="through_50",
    )
    assert "retrace_pct" not in spec
    with pytest.raises(AskError, match="retrace_pct"):
        measure(spec, _series(df))
