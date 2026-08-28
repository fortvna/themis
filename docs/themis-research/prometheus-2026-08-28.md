# Themis technology research

Prometheus. 2026-08-28. Trial only. No harness. Venue locked: Binance.

Land this in `fortvna/themis`. Do not treat it as a spec.

## What is real

- Repo `fortvna/themis`: LICENSE, README.md, prompt.md, questions.md. Two commits (Amir 2026-08-26, then 2026-08-28). No Python, no YAML specs, no run folders.
- Named stack exists as libraries: pandas, numpy, pyyaml, ccxt, `backtesting.py` (kernc). pandas 3.0.5 ran here. ccxt and backtesting.py were not installed for the trial.
- Public Fortvna also has `taap-taap` (Swift iOS tap game). No reuse for Themis.
- `argus`, `stake`, `university`, `ts-console` 404 from this desk. Not inventoried.

## What is vapor

- The conversation in README (English → YAML → fetch → ask → run) is not implemented.
- prompt.md is a build brief, not the product. Do not freeze it as-is.
- Default windows in prompt.md (`discovery` 2022-01-01–2024-12-31, `holdout` 2025) are already stale as of 2026-08-28, and empty for gold and the index stand-ins.

## Law to keep

- YAML is structure, not a program.
- `ask` measures behavior. `run` trades. A bounce rate is not return. Do not multiply hit-rate × R in chat.
- Quote metrics only from a run folder.
- No warehouse. No live orders. No indicator/alert before a kept spec.
- Same ticker on two venues is two series. SPYUSDT is not ES. QQQUSDT is not NQ. Binance XAUUSDT is not COMEX.

## R1 trial (CSV fixture)

Throwaway pandas ask on a synthetic 4h CSV. Planted 40 impulse/retrace episodes inside 6570 bars. Not gold. Not Binance. Do not quote as market behavior.

Same English (“75% retracement bounce”), three explicit definitions:

| id | impulse | bounce | n | bounce rate | invalidated |
| --- | --- | --- | ---: | ---: | ---: |
| A | 12-bar swing, range ≥ 1.5 ATR | close back through 50% of impulse within 10 bars | 257 | 53.3% | 43.2% |
| B | 8-bar swing, range ≥ 1.2 ATR | close back through 50% | 358 | 47.8% | 52.0% |
| C | 12-bar swing, range ≥ 1.5 ATR | 1×ATR reaction within 10 bars | 257 | 58.4% | 40.9% |

Bounce rate moved 11 points when impulse and bounce changed. Rival asks are the product. Freeze strategy YAML only after those folders exist.

Artifacts on the shared machine (not in git): `/workspace/r1_runs/` (`metrics.json`, fixture CSV, per-rival event tables).

## Binance 4h history (Vision monthly zips)

Live `fapi.binance.com` from this desk: HTTP 451 (geo-restricted). `data.binance.vision` bulk zips work. `ccxt` live fetch is optional and will fail on restricted desks. CSV plus Vision is the fetch.

Checked `data/futures/um/monthly/klines/<symbol>/4h/` (USD-M). August 2026 monthly zip not published yet (month open).

| series | first monthly 4h zip | last monthly 4h zip | notes |
| --- | --- | --- | --- |
| BTCUSDT | 2022-01 or earlier | 2026-07 | long window; can prove 2022–2024 discovery |
| SOLUSDT | 2022-01 or earlier | 2026-07 | same |
| XAUUSDT | 2025-12 | 2026-07 | gold go-live is ~8 months of 4h; 2022–2024 empty; 2025 holdout is one month |
| SPYUSDT | 2026-04 | 2026-07 | not ES; ~4 months |
| QQQUSDT | 2026-04 | 2026-07 | not NQ; ~4 months |

Gold R1 on real Binance bars will have small n. Kill rule `min_trades: 30` may fail. Do not put one global discovery/holdout on every spec.

## `backtesting.py`

Fine for v1 `run` (next-open fill, commission, spread). It does not accrue perp funding. 4h stop/target from OHLC is optimistic on volatile bars. Costs stay a written placeholder. Net return from this engine is not a live claim.

## Product changes (ratified)

1. CSV + Binance Vision first-class. ccxt optional.
2. Dates per series, recorded as actually loaded. Do not freeze prompt.md dates.
3. Rival asks first-class (2–4 explicit definitions, separate run folders).
4. Freeze question YAML before any English compiler. Compiler is last mile.
5. Gold go-live is an 8-month `ask`. BTC/SOL prove long windows.
6. Skip indicator, skill package, question bank, live, warehouse.

## First fire (when Vulcan is released)

Not the harness. One question YAML + fixture CSV `ask` that writes `runs/<id>/` with `n` and bounce rate, plus one rival cousin. Then one real Binance Vision fetch of XAUUSDT 4h for the dates that actually exist. Strategy `run` only after those folders exist.
