# H1: 1h 61.8% retrace of swing high/low, stop 1 ATR beyond origin, target the extreme

English (Amir): find highs and lows of the 1h and wait retrace until 61.8 percent, stop loss is the low + 1 ATR, take profit is the high. How good is that hypothesis.

This report quotes numbers only from the run folders named below. Chat did not invent them.

## Series (from run folder meta)

- provider / exchange / symbol / timeframe: `binance` / `binanceusdm` / `XAUUSDT` / `1h`
- identity: Binance USD-M XAUUSDT perp. Not COMEX. Venue locked Binance; compiler did not pick it.
- source in folder: `csv` (Vision monthly zips fetched then read from gitignored cache with `--offline`)
- actual_start: `2025-12-11 08:00:00+00:00`
- actual_end: `2026-07-31 23:00:00+00:00`
- n_bars: `5584`
- thin (ask meta): `False`
- thin (strategy meta): `False`
- execution_ready: `False`
- kept_possible (strategy metrics): `False`

## Job YAML

- live xai job: `research/jobs/20260828T181443Z-live/job.yaml`
- rival ask A: `research/questions/xauusdt_1h_swing_retrace_fractal2_atr14.yaml`
- rival ask B: `research/questions/xauusdt_1h_swing_retrace_fractal5_atr20.yaml`
- strategy: `research/specs/xauusdt_1h_retrace_swing.yaml`
- explicit backup freeze (same English, n=5 ATR14 vs n=3 ATR20): `research/jobs/20260828T180511Z-h1/job.yaml`

Live compiler: xai / grok-4. No mock fallback. YAML frozen before metrics. Rival definitions: fractal n=2 + ATR 14 vs fractal n=5 + ATR 20. Fill next_open. Swing at i knowable at i+n. Stop = 1 ATR beyond the swing origin (English "low + 1 ATR"). Target = swing extreme. Costs placeholder written with reason. Not modeled: funding, intra-bar path.

## Ask folders (path stats, not pnl)

### `20260828T181511Z-xauusdt_1h_swing_retrace_fractal2_atr14-e49e8256`

Copied from `runs/20260828T181511Z-xauusdt_1h_swing_retrace_fractal2_atr14-e49e8256/metrics.json`:

```json
{
  "kind": "question",
  "spec_id": "xauusdt_1h_swing_retrace_fractal2_atr14",
  "n": 1070,
  "target_rate": 0.5617,
  "stop_rate": 0.4262,
  "neither_rate": 0.0121,
  "target_rate_ci95": 0.0297,
  "stop_rate_ci95": 0.0296,
  "fractal_n": 2,
  "atr_n": 14,
  "stop_atr_mult": 1.0,
  "note": "path stats only. not pnl. not edge. stop is 1 ATR beyond the swing origin when atr_n is set.",
  "identity": {
    "provider": "binance",
    "symbol": "XAUUSDT",
    "exchange": "binanceusdm",
    "timeframe": "1h",
    "source": "csv",
    "row_count": 5584,
    "actual_start": "2025-12-11 08:00:00+00:00",
    "actual_end": "2026-07-31 23:00:00+00:00",
    "not": "not COMEX"
  },
  "n_bars": 5584
}
```

Copied from `runs/20260828T181511Z-xauusdt_1h_swing_retrace_fractal2_atr14-e49e8256/meta.json`:

```json
{
  "kind": "question",
  "stage": "discovery",
  "execution_ready": false,
  "spec_id": "xauusdt_1h_swing_retrace_fractal2_atr14",
  "actual_start": "2025-12-11 08:00:00+00:00",
  "actual_end": "2026-07-31 23:00:00+00:00",
  "n_bars": 5584,
  "provider": "binance",
  "source": "csv",
  "symbol": "XAUUSDT",
  "timeframe": "1h",
  "exchange": "binanceusdm",
  "thin": false
}
```

### `20260828T181515Z-xauusdt_1h_swing_retrace_fractal5_atr20-cb131913`

Copied from `runs/20260828T181515Z-xauusdt_1h_swing_retrace_fractal5_atr20-cb131913/metrics.json`:

```json
{
  "kind": "question",
  "spec_id": "xauusdt_1h_swing_retrace_fractal5_atr20",
  "n": 471,
  "target_rate": 0.4883,
  "stop_rate": 0.5011,
  "neither_rate": 0.0106,
  "target_rate_ci95": 0.0451,
  "stop_rate_ci95": 0.0452,
  "fractal_n": 5,
  "atr_n": 20,
  "stop_atr_mult": 1.0,
  "note": "path stats only. not pnl. not edge. stop is 1 ATR beyond the swing origin when atr_n is set.",
  "identity": {
    "provider": "binance",
    "symbol": "XAUUSDT",
    "exchange": "binanceusdm",
    "timeframe": "1h",
    "source": "csv",
    "row_count": 5584,
    "actual_start": "2025-12-11 08:00:00+00:00",
    "actual_end": "2026-07-31 23:00:00+00:00",
    "not": "not COMEX"
  },
  "n_bars": 5584
}
```

Copied from `runs/20260828T181515Z-xauusdt_1h_swing_retrace_fractal5_atr20-cb131913/meta.json`:

```json
{
  "kind": "question",
  "stage": "discovery",
  "execution_ready": false,
  "spec_id": "xauusdt_1h_swing_retrace_fractal5_atr20",
  "actual_start": "2025-12-11 08:00:00+00:00",
  "actual_end": "2026-07-31 23:00:00+00:00",
  "n_bars": 5584,
  "provider": "binance",
  "source": "csv",
  "symbol": "XAUUSDT",
  "timeframe": "1h",
  "exchange": "binanceusdm",
  "thin": false
}
```

## Strategy folder (the trade / "how good")

### `20260828T181520Z-xauusdt_1h_retrace_swing-ce_swing`

Copied from `runs/20260828T181520Z-xauusdt_1h_retrace_swing-ce_swing/metrics.json`:

```json
{
  "kind": "strategy",
  "spec_id": "xauusdt_1h_retrace_swing",
  "n_trades": 1070,
  "pnl": -5799.15927,
  "net_return": -1.371985,
  "max_drawdown_pct": 138.0605,
  "thin": false,
  "kept_possible": false,
  "not_modeled": [
    "perp funding",
    "intra-bar stop/target path"
  ],
  "not_computed": [
    "calmar",
    "cagr",
    "sortino",
    "sharpe",
    "profit_factor"
  ],
  "execution_ready": false,
  "costs": {
    "commission_per_side": 0.0004,
    "slippage_ticks": 1,
    "cost_unit": "fraction_of_price",
    "notes": "Placeholder. Binance USD-M taker-ish. No funding. Not a live claim."
  },
  "commission_per_side": 0.0004,
  "note": "placeholder costs. not a live claim. 4h SL/TP from OHLC is optimistic.",
  "identity": {
    "provider": "binance",
    "symbol": "XAUUSDT",
    "exchange": "binanceusdm",
    "timeframe": "1h",
    "source": "csv",
    "row_count": 5584,
    "actual_start": "2025-12-11 08:00:00+00:00",
    "actual_end": "2026-07-31 23:00:00+00:00",
    "not": "not COMEX"
  }
}
```

Copied from `runs/20260828T181520Z-xauusdt_1h_retrace_swing-ce_swing/meta.json`:

```json
{
  "kind": "strategy",
  "stage": "discovery",
  "execution_ready": false,
  "spec_id": "xauusdt_1h_retrace_swing",
  "actual_start": "2025-12-11 08:00:00+00:00",
  "actual_end": "2026-07-31 23:00:00+00:00",
  "n_bars": 5584,
  "provider": "binance",
  "source": "csv",
  "symbol": "XAUUSDT",
  "thin": false,
  "family": "xauusdt_1h_retrace_swing"
}
```

## Verdict from folders only

- Ask A (`fractal_n=2`, `atr_n=14`): n=1070, target_rate=0.5617, stop_rate=0.4262, neither_rate=0.0121, target_rate_ci95=0.0297, stop_rate_ci95=0.0296. Path stats. Not pnl.
- Ask B (`fractal_n=5`, `atr_n=20`): n=471, target_rate=0.4883, stop_rate=0.5011, neither_rate=0.0106, target_rate_ci95=0.0451, stop_rate_ci95=0.0452. Path stats. Not pnl.
- Strategy run: n_trades=1070, net_return=-1.371985, pnl=-5799.15927, max_drawdown_pct=138.0605, thin=False, kept_possible=False, execution_ready=False.
- Gold 1h on this load is not thin (`n_bars=5584`). `kept_possible` is still false (no unused holdout / one validate). Kill would also fail on these strategy metrics. Not kept. Not execution-ready.
- Not modeled (folder): ['perp funding', 'intra-bar stop/target path'].
- Costs in folder: placeholder commission_per_side=0.0004. Not a live claim.

Per-run markdown also at:

- `research/reports/20260828T181511Z-xauusdt_1h_swing_retrace_fractal2_atr14-e49e8256.md`
- `research/reports/20260828T181515Z-xauusdt_1h_swing_retrace_fractal5_atr20-cb131913.md`
- `research/reports/20260828T181520Z-xauusdt_1h_retrace_swing-ce_swing.md`
