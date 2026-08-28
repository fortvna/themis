# Pressure test: English-to-code trading harness

Minerva. 2026-08-28. Extra research. Not a spec. Not a build.

Target: ask → prove → metrics → backtest → walk-forward → auto-optimize
Books: Binance `XAUUSDT`, `BTCUSDT`, `SOLUSDT`, `SPYUSDT`, `QQQUSDT`.

Land in `fortvna/themis` with the other notes. Caesar: Themis only.

Prometheus's real gold ask (Vision 4h, 1396 bars, 2025-12-11 → 2026-07-31) is the sample this note uses. I did not rebuild it.

## Verdict

The *loop* is coherent. The *ladder on every symbol* is not.

Ask on gold is coherent. A first `run` on gold is barely coherent (thin n, no funding, optimistic 4h SL/TP). Walk-forward and auto-optimize on gold, SPY, and QQQ are wrong with the history we actually have. Those stages belong on BTC/SOL, or the CLI must refuse them until n and holdout clear a floor.

If the spec promises Amir's full ladder on gold, it will lie.

## Is it coherent?

Yes, as a **state machine per spec**, with gates:

| stage | job | coherent when |
| --- | --- | --- |
| English → question YAML | structure, not numbers | always, if YAML is frozen before any metric is spoken |
| `ask` | behavior: n, rate, MAE/MFE, rival definitions | any named series that has bars; CI must be printed |
| prove / metrics | "is the hypothesis even a thing" | rival folders exist; do not pick the flattering rate |
| `run` (backtest) | after-cost trades on discovery | costs written; fill next-open; holdout locked; n not theater |
| `validate` / walk-forward | OOS, unused in discovery | holdout has enough bars *and* trades |
| `tune` | declared `search_space`, new spec ids | only if walk-forward is eligible; never on empty space |
| kept → indicator | twin of one spec | after one validate; never implied live |

Amir's English described this as one pipeline on "the" strategy. That is the wrong geometry. History is not equal across the five books. The spec must degrade the ladder per series instead of faking later stages.

## Where it is wrong

### 1. Gold cannot carry walk-forward or auto-optimize

~7.5 months of 4h (1396 bars). Prometheus: same 75% English, n=58 / 86 / 58, bounce 53% ±13 / 62% ±10 / 72% ±12. Definition swing equals the noise.

A 80/20 split leaves ~1.5 months of holdout and maybe ~12–17 events. Walk-forward folds would have n≈20. `min_trades: 30` fails. `tune` will fit definition C's 72% and call it optimization.

**Change:** gold go-live is `ask` (+ a cautious `run` if costs are written and the report screams thin sample). Refuse `validate` theater and refuse `tune` on this window.

### 2. SPYUSDT / QQQUSDT are worse, and they are not the index

Vision 4h starts 2026-04. ~4 months. Not ES. Not NQ. English "research NQ / ES" on these books is a false series.

**Change:** identity note is mandatory. `run` allowed. Walk-forward and `tune` refused until history exists. Never label reports ES/NQ.

### 3. BTC/SOL can hold the rest of the ladder

4h from 2022. Long enough for discovery / yearly-style walk-forward / a declared search space. That is where we prove `run` → `validate` → `tune`.

**Change:** the spec names BTC/SOL as the window-proof series. A gold winner is not transferred onto BTC. A BTC-tuned spec is not gold.

### 4. English without rival asks ships the 72%

The product failure mode is not missing pandas. It is answering one English line with one definition. C looks like a win. It is a wording.

**Change:** `ask` on vague English must write ≥2 rival folders and print the spread before any strategy YAML. No compiler until those files exist. Chat may not quote a rate that is not in a folder.

### 5. "Good enough" is undefined, so everything gets promoted

Amir: metrics, then if good, backtest, then walk-forward, then optimize. There is no kill for *ask*. Bounce rate is not a promotion key.

**Change:** explicit gates (see below). `ask` never auto-promotes. `run` never auto-validates. `tune` never runs because someone said optimize.

### 6. The `run` engine will overstate gold

`backtesting.py`: no perp funding, 4h stop/target from OHLC is optimistic, costs are placeholders. On XAUUSDT that bias is the whole story: small n plus optimistic fills.

**Change:** every strategy report lists not-computed / not-modeled (funding, intra-bar path, real fees). `execution_ready: false` until Amir writes real costs. Thin-sample `run` cannot reach `kept`.

### 7. Walk-forward ≠ a second backtest

README `validate` is one locked holdout, once. Amir said walk-forward. Those are different. Rolling WF on 8 months is one extra overfit. Rolling WF on 4 years of BTC is a real test.

**Change:** spec two commands. `validate` = single holdout, all series that have a tail. `walkforward` = rolling folds, refused unless `n_bars` and `n_trades` clear floors (BTC/SOL today; gold/SPY/QQQ no).

### 8. Auto-optimize without a floor is genetic theater

prompt.md already forbids "AI make it profitable" and empty `search_space`. Good. It still allows `tune` on any strategy spec. On gold that is a random search over noise.

**Change:** `tune` requires: declared space, parent discovery folder, walk-forward eligibility (or an explicit `thin: refuse`). Each trial new spec id. `compare` lists failures. No "best" with one run.

## Gates to write into the spec

Ask: named provider, symbol, timeframe, actual dates loaded, ≥2 rivals if definitions were unstated, CI on rates, no pnl keys.

Run: question folders cited for stop/entry, costs written, next-open fill, discovery bars only. If `n` < floor, status `thin` and `kept` is impossible.

Validate: holdout unused in discovery; refuse if holdout bars or OOS trades < floor.

Walk-forward: refuse gold/SPY/QQQ on current Vision history. Allow BTC/SOL.

Tune: refuse unless walk-forward eligible. Empty space errors.

Kept: one cousin beat the family on after-cost net return (or the family key), passed kill, one validate, holdout unused. Then indicator. Never live.

## What not to change

Law stands: YAML is structure. Quote only run folders. No warehouse. No live. No mixing books. CSV + Vision first-class. ccxt optional. Skill package later. Question bank later.

## Before we spec

1. Write the ladder as gated stages, not a promise on XAU.
2. Put floors in numbers the CLI can enforce (holdout bars, OOS trades). Gold fails WF/`tune` today; do not leave that to taste.
3. Force rival asks on vague English.
4. Split `validate` and `walkforward`.
5. Mark SPY/QQQ as ETF perps, not e-minis, in every report.
6. Do not freeze prompt.md dates, `min_trades: 30` on gold, or ccxt-only fetch.

Then Vulcan forges. Not before.
