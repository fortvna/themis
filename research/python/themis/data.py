"""csv | vision | ccxt. Vision first-class. ccxt optional, must not be assumed."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

VISION_TMPL = (
    "https://data.binance.vision/data/futures/um/monthly/klines/"
    "{symbol}/{tf}/{symbol}-{tf}-{year:04d}-{month:02d}.zip"
)

BINANCE_KLINE_COLS = [
    "open_time",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "close_time",
    "quote_volume",
    "trades",
    "taker_buy_base",
    "taker_buy_quote",
    "ignore",
]


class DataError(RuntimeError):
    pass


def research_root(start: Path | None = None) -> Path:
    import os

    env = os.environ.get("THEMIS_ROOT")
    if env:
        return Path(env)
    here = Path(start or Path.cwd()).resolve()
    for p in [here, *here.parents]:
        if (p / "research" / "python").is_dir():
            return p
    return here


def cache_path(symbol: str, timeframe: str, root: Path | None = None) -> Path:
    r = root or research_root()
    return r / "research" / ".cache" / "binance" / "binanceusdm" / symbol.upper() / f"{timeframe}.csv"


def _to_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "open_time" in out.columns and "ts" not in out.columns:
        ot = pd.to_numeric(out["open_time"], errors="coerce")
        if ot.notna().any():
            unit = "ms" if ot.max() > 1e11 else "s"
            out["ts"] = pd.to_datetime(ot, unit=unit, utc=True)
        else:
            out["ts"] = pd.to_datetime(out["open_time"], utc=True, errors="coerce")
    elif "timestamp" in out.columns:
        out["ts"] = pd.to_datetime(out["timestamp"], utc=True)
    elif "date" in out.columns:
        out["ts"] = pd.to_datetime(out["date"], utc=True)
    elif "ts" in out.columns:
        out["ts"] = pd.to_datetime(out["ts"], utc=True)
    elif isinstance(out.index, pd.DatetimeIndex):
        out = out.reset_index()
        out = out.rename(columns={out.columns[0]: "ts"})
        out["ts"] = pd.to_datetime(out["ts"], utc=True)
    else:
        raise DataError("csv has no timestamp column (open_time/timestamp/date)")
    for c in ("open", "high", "low", "close"):
        if c not in out.columns:
            raise DataError(f"csv missing {c}")
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if "volume" in out.columns:
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce")
    else:
        out["volume"] = 0.0
    out = out.dropna(subset=["open", "high", "low", "close"]).sort_values("ts")
    out = out.drop_duplicates("ts")
    return out.set_index("ts")


def load_csv(path: str | Path) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        raise DataError(f"csv not found: {p}")
    df = pd.read_csv(p)
    return _to_ohlc(df)


def _month_range(start: datetime, end: datetime) -> list[tuple[int, int]]:
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return months


def fetch_vision(
    symbol: str,
    timeframe: str = "4h",
    start: str | None = None,
    end: str | None = None,
    root: Path | None = None,
    timeout: int = 30,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """USD-M monthly kline zips from data.binance.vision. Stdlib urllib only."""
    sym = symbol.upper()
    tf = timeframe
    now = datetime.now(timezone.utc)
    if start:
        sdt = datetime.fromisoformat(str(start)[:10]).replace(tzinfo=timezone.utc)
    else:
        sdt = datetime(2020, 1, 1, tzinfo=timezone.utc)
    if end:
        edt = datetime.fromisoformat(str(end)[:10]).replace(tzinfo=timezone.utc)
    else:
        edt = now
    frames = []
    used = []
    errors = []
    for year, month in _month_range(sdt, edt):
        url = VISION_TMPL.format(symbol=sym, tf=tf, year=year, month=month)
        try:
            req = Request(url, headers={"User-Agent": "themis/0.1"})
            with urlopen(req, timeout=timeout) as resp:
                blob = resp.read()
        except HTTPError as e:
            errors.append(f"{year:04d}-{month:02d} HTTP {e.code}")
            continue
        except URLError as e:
            errors.append(f"{year:04d}-{month:02d} {e.reason}")
            continue
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as zf:
                name = next((n for n in zf.namelist() if n.endswith(".csv")), None)
                if name is None:
                    continue
                raw = pd.read_csv(zf.open(name), header=None)
        except zipfile.BadZipFile:
            errors.append(f"{year:04d}-{month:02d} bad zip")
            continue
        if len(raw) and str(raw.iloc[0, 0]).lower() in {"open_time", "open time"}:
            raw = raw.iloc[1:].reset_index(drop=True)
        if raw.shape[1] >= 6:
            raw.columns = BINANCE_KLINE_COLS[: raw.shape[1]]
        frames.append(raw)
        used.append(f"{year:04d}-{month:02d}")
    if not frames:
        raise DataError(f"vision fetched 0 months for {sym} {tf}: {errors[:8]}")
    df = pd.concat(frames, ignore_index=True)
    ohlc = _to_ohlc(df)
    ohlc = ohlc.loc[(ohlc.index >= sdt) & (ohlc.index <= edt + pd.Timedelta(days=1))]
    root = root or research_root()
    dest = cache_path(sym, tf, root)
    dest.parent.mkdir(parents=True, exist_ok=True)
    out = ohlc.reset_index()
    out.to_csv(dest, index=False)
    meta = {
        "source": "vision",
        "provider": "binance",
        "exchange": "binanceusdm",
        "symbol": sym,
        "timeframe": tf,
        "months": used,
        "errors": errors,
        "cache": str(dest),
        "n_bars": int(len(ohlc)),
        "actual_start": str(ohlc.index.min()) if len(ohlc) else None,
        "actual_end": str(ohlc.index.max()) if len(ohlc) else None,
    }
    return ohlc, meta


def fetch_ccxt(symbol: str, timeframe: str = "4h", **_: Any) -> tuple[pd.DataFrame, dict[str, Any]]:
    try:
        import ccxt  # optional
    except ImportError as e:
        raise DataError("ccxt is optional and not installed; use csv or vision") from e
    try:
        ex = ccxt.binanceusdm({"enableRateLimit": True})
        raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=1500)
    except Exception as e:
        raise DataError(f"ccxt binanceusdm failed (fapi may be HTTP 451): {e}") from e
    df = pd.DataFrame(raw, columns=["open_time", "open", "high", "low", "close", "volume"])
    ohlc = _to_ohlc(df)
    meta = {
        "source": "ccxt",
        "provider": "binance",
        "exchange": "binanceusdm",
        "symbol": symbol.upper(),
        "timeframe": timeframe,
        "n_bars": int(len(ohlc)),
        "actual_start": str(ohlc.index.min()) if len(ohlc) else None,
        "actual_end": str(ohlc.index.max()) if len(ohlc) else None,
    }
    return ohlc, meta


def load_bars(spec: dict[str, Any], root: Path | None = None) -> tuple[pd.DataFrame, dict[str, Any]]:
    data = spec.get("data") or {}
    source = (data.get("source") or "csv").lower()
    symbol = (spec.get("instrument") or {}).get("symbol") or data.get("symbol")
    timeframe = (spec.get("instrument") or {}).get("timeframe") or data.get("timeframe") or "4h"
    discovery = spec.get("discovery") or {}
    start = discovery.get("start")
    end = discovery.get("end")
    root = root or research_root()
    if source == "csv":
        path = data.get("csv_path") or data.get("path")
        if not path:
            cached = cache_path(symbol, timeframe, root)
            if cached.exists():
                path = cached
            else:
                raise DataError("data.source=csv but no csv_path and no cache")
        df = load_csv(path)
        if start:
            df = df[df.index >= pd.Timestamp(start, tz="UTC")]
        if end:
            df = df[df.index <= pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)]
        meta = {
            "source": "csv",
            "provider": data.get("provider") or "binance",
            "exchange": data.get("exchange") or "binanceusdm",
            "symbol": symbol,
            "timeframe": timeframe,
            "n_bars": int(len(df)),
            "actual_start": str(df.index.min()) if len(df) else None,
            "actual_end": str(df.index.max()) if len(df) else None,
            "csv_path": str(path),
        }
        return df, meta
    if source == "vision":
        return fetch_vision(symbol, timeframe, start=start, end=end, root=root)
    if source == "ccxt":
        return fetch_ccxt(symbol, timeframe)
    raise DataError(f"unknown data.source {source!r}; want csv|vision|ccxt")
