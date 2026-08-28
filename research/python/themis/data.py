"""csv | vision | optional ccxt. Cache under research/.cache. No warehouse."""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pandas as pd

from themis.paths import cache_dir

VISION_BASE = "https://data.binance.vision/data/futures/um/monthly/klines"
KLINE_COLS = [
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


@dataclass
class SeriesLoad:
    df: pd.DataFrame
    provider: str
    symbol: str
    timeframe: str
    exchange: str
    source: str
    actual_start: str | None
    actual_end: str | None
    n_bars: int
    cache_path: str | None = None
    note: str = ""
    identity: dict[str, Any] = field(default_factory=dict)

    def meta(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "exchange": self.exchange,
            "source": self.source,
            "actual_start": self.actual_start,
            "actual_end": self.actual_end,
            "n_bars": self.n_bars,
            "cache_path": self.cache_path,
            "note": self.note,
            "identity": self.identity,
        }


def _exchange_for(provider: str) -> str:
    if provider == "binance":
        return "binanceusdm"
    return provider


def _to_ohlc(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "open_time" in out.columns and "ts" not in out.columns:
        ot = out["open_time"]
        if pd.api.types.is_numeric_dtype(ot):
            out["ts"] = pd.to_datetime(ot, unit="ms", utc=True)
        else:
            out["ts"] = pd.to_datetime(ot, utc=True)
    if "ts" in out.columns:
        out["ts"] = pd.to_datetime(out["ts"], utc=True)
        out = out.set_index("ts")
    if not isinstance(out.index, pd.DatetimeIndex):
        raise DataError("bars need a datetime index or open_time")
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    for c in ("open", "high", "low", "close"):
        if c not in out.columns:
            raise DataError(f"missing column {c}")
        out[c] = pd.to_numeric(out[c], errors="coerce")
    if "volume" in out.columns:
        out["volume"] = pd.to_numeric(out["volume"], errors="coerce")
    else:
        out["volume"] = 0.0
    out = out.dropna(subset=["open", "high", "low", "close"]).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    return out[["open", "high", "low", "close", "volume"]]


def _wrap(df: pd.DataFrame, *, provider: str, symbol: str, timeframe: str, exchange: str, source: str, cache_path: str | None = None, note: str = "") -> SeriesLoad:
    n = int(len(df))
    start = str(df.index[0]) if n else None
    end = str(df.index[-1]) if n else None
    ident = {
        "provider": provider,
        "symbol": symbol,
        "exchange": exchange,
        "timeframe": timeframe,
        "source": source,
        "row_count": n,
        "actual_start": start,
        "actual_end": end,
    }
    if symbol in ("SPYUSDT", "QQQUSDT"):
        ident["product"] = "etf_perp"
        ident["not"] = "not ES" if symbol == "SPYUSDT" else "not NQ"
    if symbol == "XAUUSDT":
        ident["not"] = "not COMEX"
    return SeriesLoad(
        df=df,
        provider=provider,
        symbol=symbol,
        timeframe=timeframe,
        exchange=exchange,
        source=source,
        actual_start=start,
        actual_end=end,
        n_bars=n,
        cache_path=cache_path,
        note=note,
        identity=ident,
    )


def load_csv(path: str | Path, *, provider: str, symbol: str, timeframe: str, exchange: str | None = None) -> SeriesLoad:
    p = Path(path)
    if not p.exists():
        raise DataError(f"csv not found: {p}")
    df = pd.read_csv(p)
    df = _to_ohlc(df)
    return _wrap(
        df,
        provider=provider,
        symbol=symbol,
        timeframe=timeframe,
        exchange=exchange or _exchange_for(provider),
        source="csv",
        cache_path=str(p),
        note="operator csv or cached extract",
    )


def _month_range(start: datetime, end: datetime) -> list[tuple[int, int]]:
    months = []
    y, m = start.year, start.month
    while (y, m) <= (end.year, end.month):
        months.append((y, m))
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return months


def _vision_url(symbol: str, interval: str, year: int, month: int) -> str:
    name = f"{symbol}-{interval}-{year}-{month:02d}.zip"
    return f"{VISION_BASE}/{symbol}/{interval}/{name}"


def _http_get(url: str, timeout: int = 60) -> bytes:
    req = Request(url, headers={"User-Agent": "themis/0.1 (research; no spend)"})
    with urlopen(req, timeout=timeout) as resp:
        return resp.read()


def fetch_vision(
    symbol: str,
    timeframe: str,
    *,
    provider: str = "binance",
    exchange: str = "binanceusdm",
    start: str | None = None,
    end: str | None = None,
    root: Path | None = None,
    network: bool = True,
) -> SeriesLoad:
    """USD-M monthly kline zips from data.binance.vision. First-class. Free CDN, not a paid SDK."""
    cache = cache_dir(root) / provider / exchange / symbol
    cache.mkdir(parents=True, exist_ok=True)
    merged = cache / f"{timeframe}.csv"
    now = datetime.now(timezone.utc)
    if start:
        t0 = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        if t0.tzinfo is None:
            t0 = t0.replace(tzinfo=timezone.utc)
    else:
        t0 = datetime(2020, 1, 1, tzinfo=timezone.utc)
    if end:
        t1 = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
        if t1.tzinfo is None:
            t1 = t1.replace(tzinfo=timezone.utc)
    else:
        t1 = now
    frames: list[pd.DataFrame] = []
    skipped_404 = 0
    if not network:
        if merged.exists():
            return load_csv(merged, provider=provider, symbol=symbol, timeframe=timeframe, exchange=exchange)
        raise DataError("vision cache empty and network disabled")
    for y, m in _month_range(t0, t1):
        url = _vision_url(symbol, timeframe, y, m)
        try:
            blob = _http_get(url)
        except HTTPError as e:
            if e.code == 404:
                skipped_404 += 1
                continue
            raise DataError(f"vision HTTP {e.code} for {url}") from e
        except URLError as e:
            raise DataError(f"vision network error: {e}") from e
        with zipfile.ZipFile(io.BytesIO(blob)) as zf:
            names = zf.namelist()
            if not names:
                continue
            raw = zf.read(names[0])
        text = raw.decode("utf-8", errors="replace")
        sample = io.StringIO(text)
        first = sample.readline()
        sample.seek(0)
        if first.lower().startswith("open_time") or first.lower().startswith("opentime"):
            df = pd.read_csv(sample)
            df.columns = [c.strip().lower() for c in df.columns]
            rename = {"opentime": "open_time", "closetime": "close_time"}
            df = df.rename(columns=rename)
        else:
            df = pd.read_csv(sample, header=None, names=KLINE_COLS)
        frames.append(df)
    if not frames:
        raise DataError(f"vision returned no months for {symbol} {timeframe} (404s={skipped_404})")
    all_df = pd.concat(frames, ignore_index=True)
    all_df = _to_ohlc(all_df)
    all_df = all_df[(all_df.index >= t0) & (all_df.index <= t1)]
    merged.parent.mkdir(parents=True, exist_ok=True)
    out = all_df.reset_index().rename(columns={"ts": "open_time"})
    out["open_time"] = (out["open_time"].astype("int64") // 10**6)
    out.to_csv(merged, index=False)
    return _wrap(
        all_df,
        provider=provider,
        symbol=symbol,
        timeframe=timeframe,
        exchange=exchange,
        source="vision",
        cache_path=str(merged),
        note=f"binance.vision USD-M monthly klines; skipped_404={skipped_404}",
    )


def fetch_ccxt(
    symbol: str,
    timeframe: str,
    *,
    provider: str = "binance",
    exchange: str = "binanceusdm",
    start: str | None = None,
    end: str | None = None,
) -> SeriesLoad:
    """Optional. Must not be assumed. Live fapi is HTTP 451 from some desks."""
    try:
        import ccxt  # type: ignore
    except ImportError as e:
        raise DataError("ccxt not installed (optional)") from e
    cls = getattr(ccxt, exchange, None) or getattr(ccxt, provider, None)
    if cls is None:
        raise DataError(f"ccxt has no exchange {exchange}")
    ex = cls({"enableRateLimit": True})
    since = None
    if start:
        t0 = datetime.fromisoformat(str(start).replace("Z", "+00:00"))
        since = int(t0.timestamp() * 1000)
    rows = []
    try:
        while True:
            batch = ex.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=1500)
            if not batch:
                break
            rows.extend(batch)
            since = batch[-1][0] + 1
            if len(batch) < 1500:
                break
            if end:
                t1 = datetime.fromisoformat(str(end).replace("Z", "+00:00"))
                if batch[-1][0] >= int(t1.timestamp() * 1000):
                    break
    except Exception as e:
        raise DataError(f"ccxt fetch failed (do not assume fapi): {e}") from e
    if not rows:
        raise DataError("ccxt returned no bars")
    df = pd.DataFrame(rows, columns=["open_time", "open", "high", "low", "close", "volume"])
    df = _to_ohlc(df)
    return _wrap(df, provider=provider, symbol=symbol, timeframe=timeframe, exchange=exchange, source="ccxt")


def load_from_spec(spec: dict[str, Any], *, root: Path | None = None, network: bool = True) -> SeriesLoad:
    data = spec.get("data") or {}
    inst = spec.get("instrument") or {}
    source = (data.get("source") or "csv").lower()
    provider = data.get("provider") or inst.get("venue") or inst.get("provider") or "binance"
    symbol = inst.get("symbol") or data.get("symbol")
    timeframe = inst.get("timeframe") or data.get("timeframe") or "4h"
    exchange = data.get("exchange") or _exchange_for(provider)
    if not symbol:
        raise DataError("spec has no symbol")
    discovery = spec.get("discovery") or {}
    start = discovery.get("start")
    end = discovery.get("end")
    if source == "csv":
        csv_path = data.get("csv_path")
        if not csv_path:
            cached = cache_dir(root) / provider / exchange / symbol / f"{timeframe}.csv"
            csv_path = str(cached)
        return load_csv(csv_path, provider=provider, symbol=symbol, timeframe=timeframe, exchange=exchange)
    if source == "vision":
        return fetch_vision(
            symbol,
            timeframe,
            provider=provider,
            exchange=exchange,
            start=start,
            end=end,
            root=root,
            network=network,
        )
    if source == "ccxt":
        return fetch_ccxt(symbol, timeframe, provider=provider, exchange=exchange, start=start, end=end)
    raise DataError(f"unknown data.source {source!r}")


def research_root(start=None):
    from themis.paths import repo_root
    return repo_root(start)


def cache_path(symbol: str, timeframe: str, root=None):
    return cache_dir(root) / "binance" / "binanceusdm" / symbol.upper() / f"{timeframe}.csv"


def load_bars(spec: dict, root=None):
    series = load_from_spec(spec, root=root, network=True)
    return series.df, series.meta()
