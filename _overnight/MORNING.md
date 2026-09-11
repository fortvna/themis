# Themis overnight status

Updated as work finishes. Amir asked: harness loop ready by morning; backtest engine OK too.

## Idea harness loop — DONE (2026-09-11)

- Commit: `43ec410` `fix(loop): §20 live prompt, G3 ci95, refuse incomplete live YAML` (local main, not pushed)
- pytest: `research/python/tests/test_ideas.py` → **27 passed**
- Offline prove: `themis idea … --offline --name g3-loop-prove-run` → screen `weak`, latest.{md,html,ipynb}
- Live `--backend xai`: no mock fallback; refuses incomplete measure (see `/tmp/themis-loop-finish.md`)

### Demo tomorrow
```bash
cd /workspace/fortuna/projects/themis
research/python/.venv/bin/themis idea list
research/python/.venv/bin/themis idea show --name g3-loop-prove-run
# open research/ideas/g3-loop-prove-run/latest.html
```

## Backtest / run engine — DONE (2026-09-11)

pandas bar-loop is v1 `run` (not kernc). Path: load `implements` → `trades()` → `themis.fill` → `metrics.py`. Fees from `themis.fees` (Binance Regular). YAML records what Python froze.

### What's ready

- `themis run --spec <yaml> [--offline] [--thin]` writes an honest folder:
  - `trades.csv`, `equity.csv` on the **bar** index (`bar_i`, `ts`, `equity`, `drawdown_pct`)
  - `metrics.json` with Sharpe / Sortino / Calmar / CAGR / PF / expectancy / win_rate / payoff_ratio when they can be computed; otherwise `not_computed` is a **map of name → reason**
  - `not_modeled` always lists perp funding and intra-bar path
  - same-bar SL+TP → `ambiguous_same_bar`, fill at **stop**; gap through a level → fill at **open** (`stop_gap` / `target_gap`)
  - folder name is `{utc}-{spec-id}-{sha1[:8]}` (same short-hash as ask)
- No silent `0.618` in the runner. Missing zone / `fractal_n` is `YAML and implements disagree`.
- Costs required. Empty costs dict is a spec error. Missing `commission_per_side` is frozen from `themis.fees` and written back onto `spec.yaml`. Zero commission only as `0` plus a reason/notes.
- `requires_asks` enforced (non-empty; matching ask folders must exist).
- `--thin` required for gold / thin discovery; `kept` still impossible.
- `execution_ready: false`. Not a live claim.

### Offline prove (quote only this folder)

Spec: `research/ideas/g1-btc-4h-618-retrace/g1-n5-1r-btc-4h-v1.yaml` (G1 family, costs written, `requires_asks` → existing G1 ask folders).

```bash
cd /workspace/fortuna/projects/themis
research/python/.venv/bin/themis run \
  --spec research/ideas/g1-btc-4h-618-retrace/g1-n5-1r-btc-4h-v1.yaml \
  --offline
```

Folder: `research/runs/20260911T071431Z-g1-n5-1r-btc-4h-v1-fa1c8946`

From that folder's `metrics.json` / `meta.json` (not invented):

| key | value |
| --- | --- |
| spec_id | `g1-n5-1r-btc-4h-v1` |
| implements | `strategies/retrace_swing.py` |
| identity | Binance USD-M BTCUSDT 4h, source csv (vision cache, `--offline`) |
| actual window | 2022-01-01 → 2026-08-31, **n_bars=10224**, thin=false |
| n_trades | 992 (win 375 / loss 617) |
| n_ambiguous | 5 |
| n_gap | 62 |
| pnl | 16952.20487 (1_unit, pnl_unit=price) |
| net_return | 0.362307 |
| max_drawdown_pct | 125.829 |
| cagr | 0.068525 |
| calmar | 0.054459 (full_sample) |
| sharpe | -0.076018 |
| sortino | -0.106052 |
| profit_factor | 1.024179 |
| expectancy | 17.088916 |
| win_rate | 0.378024 |
| payoff_ratio | 1.685115 |
| periods_per_year | 2190 |
| costs_applied | commission_per_side 0.0005, slippage_ticks 1, tick_size 0.1 |
| not_computed | `{}` |
| not_modeled | perp funding; intra-bar path; intra-bar stop/target path |
| kill_pass | false (`max_drawdown_pct`) |
| kept / execution_ready | false / false |

`equity.csv` has 10224 rows, `bar_i` 0..10223. `trades.csv` why counts: stop 549, target 376, stop_gap 47, target_gap 15, ambiguous_same_bar 5.

Kill failed on drawdown (125% > 40). 1-unit price PnL can push equity through zero; `n_returns` is 9413 (bars after `E<=0` dropped). That is the model, not a hidden Sharpe.

### Commands to demo idea loop + run

```bash
cd /workspace/fortuna/projects/themis
VENV=research/python/.venv/bin

# idea loop (already proven overnight)
$VENV/themis idea list
$VENV/themis idea show --name g3-loop-prove-run
# open research/ideas/g3-loop-prove-run/latest.html

# compile → YAML only (does not ask or run)
$VENV/themis compile --english G1 --symbol BTCUSDT --timeframe 4h --no-write

# strategy run on the frozen G1 YAML + existing asks + BTC 4h cache
$VENV/themis run --spec research/ideas/g1-btc-4h-618-retrace/g1-n5-1r-btc-4h-v1.yaml --offline

# gold discovery still needs --thin (cannot keep)
# $VENV/themis run --spec <gold g1 strategy yaml> --offline --thin
```

Quote numbers only from `research/runs/<id>/metrics.json` (or `table.csv` for asks).

### Remaining gaps

- **Live xai compile still open.** `--backend xai` does not fall back to mock. A G3 live compile this session exited 1: `live question … missing measure. no fallback to mock.` The model emits prose `condition`/`outcome` and omits `measure: atr_react`. Operator path stays `--backend mock`. `openai` live is not released. Do not claim live compile is desk-ready.
- **`validate` does not slice holdout.** It checks the holdout floor, then calls `run_strategy` on discovery bars. Holdout unused is a gate, not a second window yet.
- **`retrace_swing` geometry is origin/extreme.** Named `low + 1 ATR` and B0 “1R from the 75% touch” are YAML text; the module does not move the stop/target off origin/extreme. G1 (stop origin, target extreme) matches. B0 1R is not a honest run of that English until the module reads `target_r` / `stop_atr_mult`.
- **G4 / Po3 / FVG family YAML still points at `retrace_swing`.** A run now refuses (missing `fractal_n` / zone) instead of silently trading a retrace. New family modules are still `needs_human`.
- **`tune` is still a stub** once walkforward floors clear.
- **Strategy HTML report** still captions “gold perp, not COMEX” even on BTC. Markdown dumps `metrics.json`. Chat must quote the JSON.
- **Ask** still has a silent `0.618` fallback in `measure()` if a question omits `pct_low`. Runner does not. Left alone (not a run blocker).
- Pytest session fixtures used to **overwrite** `research/.cache/.../BTCUSDT/4h.csv`. `btc_csv` now keeps an existing cache. Do not treat a synth 5000-bar file as Vision.

### pytest summary

```
cd /workspace/fortuna/projects/themis/research/python
.venv/bin/python -m pytest tests -q
# 112 passed in ~9.5s
```

New/extended: `tests/test_run.py` (honest folder, costs freeze, requires_asks, --thin, no silent 0.618), fill same-bar/gap short+long in `test_metrics.py`, missing zone in `test_implements.py`.

Venv only: `research/python/.venv`. Not pushed.
