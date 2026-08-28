from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(os.environ.get("THEMIS_ROOT") or Path(__file__).resolve().parents[3])
PY = ROOT / "research" / "python"
sys.path.insert(0, str(PY))
os.environ["THEMIS_ROOT"] = str(ROOT)

FIX = ROOT / "research" / ".cache" / "binance" / "binanceusdm"


def _write_ohlc(path: Path, df: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    if "ts" not in out.columns:
        out = out.reset_index().rename(columns={out.columns[0]: "ts"})
    out.to_csv(path, index=False)


def concat_vision_gold() -> Path:
    import glob

    files = sorted(glob.glob("/workspace/r1_runs/vision/xau4h/csv/XAUUSDT-4h-*.csv"))
    dest = FIX / "XAUUSDT" / "4h.csv"
    dest.parent.mkdir(parents=True, exist_ok=True)
    if files:
        frames = [pd.read_csv(f) for f in files]
        df = pd.concat(frames, ignore_index=True)
        df.to_csv(dest, index=False)
        return dest
    # fallback: generate thin gold locally (not committed)
    df = synth_bars(1396, start="2025-08-01", px=2400.0)
    _write_ohlc(dest, df)
    return dest


def synth_bars(n: int, start: str = "2022-01-01", px: float = 20000.0) -> pd.DataFrame:
    import numpy as np

    idx = pd.date_range(start, periods=n, freq="4h", tz="UTC")
    rng = np.random.default_rng(7)
    rets = rng.normal(0, 0.004, size=n)
    close = px * (1 + pd.Series(rets)).cumprod().to_numpy()
    high = close * (1 + rng.uniform(0.0005, 0.006, size=n))
    low = close * (1 - rng.uniform(0.0005, 0.006, size=n))
    open_ = close / (1 + rets)
    vol = rng.uniform(10, 100, size=n)
    return pd.DataFrame({"ts": idx, "open": open_, "high": high, "low": low, "close": close, "volume": vol})


@pytest.fixture(scope="session")
def thin_gold_csv() -> Path:
    return concat_vision_gold()


@pytest.fixture(scope="session")
def btc_csv() -> Path:
    df = synth_bars(5000, start="2022-01-01", px=20000.0)
    dest = FIX / "BTCUSDT" / "4h.csv"
    _write_ohlc(dest, df)
    return dest


@pytest.fixture(scope="session")
def spy_csv() -> Path:
    df = synth_bars(1500, start="2026-04-01", px=500.0)
    dest = FIX / "SPYUSDT" / "4h.csv"
    _write_ohlc(dest, df)
    return dest


@pytest.fixture(scope="session")
def qqq_csv() -> Path:
    df = synth_bars(1500, start="2026-04-01", px=400.0)
    dest = FIX / "QQQUSDT" / "4h.csv"
    _write_ohlc(dest, df)
    return dest
