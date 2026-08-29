# Backtest engine, trade metrics, and whether Python/pandas is the desk

Research. 2026-08-28. Not a spec. Not a build.

This note answers the desk question: what is required for a *good* backtest engine for Themis, how to calculate the metrics on trades and equity, and whether Python / pandas is the right language for EDA, hypothesis research, and the backtest itself.

Canon stays [`docs/open-spec.md`](../open-spec.md). Formulas here that match §18 are implementation notes. Formulas here that go beyond §18 are optional or later. Do not treat this file as a second spec.

---

## 0. Did the question explain itself?

Yes. No blocking clarification.

Themis is a research loop you can talk to:

1. English in.
2. Freeze YAML (structure, not numbers).
3. **Ask** with pandas: is the path even a thing? (`n`, rates, MAE/MFE, rival definitions). No pnl.
4. **Run** a strategy: after-cost trades, equity, drawdown, ratios. Numbers only from a run folder.
5. Promote only through floors (thin / validate / walk-forward / kept). Chat does not invent a 70% or a Sharpe.

What this note is for: *how the measuring machines in steps 3–4 should work*, and whether “we will do it in pandas” is a good bet.

One pin, because “pandas backtest” is overloaded:

| Phrase people say | What they often mean | What Themis needs |
| --- | --- | --- |
| “Backtest in pandas” | `signal.shift(1) * returns` on the whole array | That is a **research screen**, not a fill simulator |
| “Event-driven engine” | Tick matching, order book, live parity (Nautilus, LEAN) | That is a **broker sim**. Out of v1. No live. |
| “Pandas bar-loop” | Walk closed bars in time order, fill next open, check high/low for stop/target | **This is the v1 `run` engine.** The current `_swing_trades` already is this shape. |

So: **Python + pandas is the right desk.** The ask is vectorized-ish pandas on event tables. The run is a sequential bar-loop that *reads* pandas OHLC. Those are two engines. Mixing them is how a bounce rate becomes a fake return.

---

## 1. What Themis is actually measuring

Two questions, two machines, two metric sets. Spec law 4 / §18. Industry agrees; Themis already named it.

| | `ask` (hypothesis / EDA) | `run` (backtest) |
| --- | --- | --- |
| Question | Does this path happen? How often? How far against us? | After costs, did the *trade* make money, and how painful was the path? |
| Input | Frozen question YAML + OHLC | Frozen strategy YAML + OHLC + costs + `implements` |
| Output | Event table, rates, CI, MAE/MFE | `trades.csv`, equity, §18 ratios |
| Forbidden | pnl, expectancy, Sharpe, trades-as-edge | quoting a bounce rate as return |
| Industry analogue | Event study / signal research | Portfolio / trade simulation |

Prometheus already showed why the split is the product: same English “75% retrace bounce” on gold 4h moved **11–19 points** across rival definitions. Path first, trade second. G1 on gold 4h (stop-first ~2× target) is `dead` on path stats — that is pandas-before-backtest doing its job.

Current gap vs spec: `research/python/themis/runner.py` already writes `n_trades`, `pnl`, `net_return`, `max_drawdown_pct`, then lists Sharpe / Sortino / Calmar / CAGR / profit factor as a **permanent** `not_computed`. Spec §18 says: if equity has two or more points, compute them. `metrics.py` is named in the tree and does not exist yet.

---

## 2. What a good backtest engine is

A backtest engine is not “code that prints a Sharpe.” It is a **clock plus a fill model plus a ledger**, with the same information constraint a live desk would have.

Consensus from QuantStackExchange, Quantopian lectures, Lo, López de Prado, Interactive Brokers quant notes, and 2025–2026 engine comparisons (vectorbt / backtesting.py / Backtrader / Nautilus / LEAN):

### 2.1 Non-negotiable properties

1. **Causality.** At bar `i`, the strategy may use only data knowable at `i`. A fractal swing at `i` with window `n` is knowable at `i+n` (already law). Forming-bar signals are forbidden. A bounce / 1R touch is an **outcome**, never `rules.entry`.
2. **Fill after signal.** Closed bar in, fill at **next open** unless the spec says otherwise and why. Using bar `i` close as both signal and fill is the classic lookahead (QuantInsti / systematicls: this single off-by-one inflates results 10–30% on faster bars).
3. **Deterministic ledger.** Same spec + same bars + same costs → same `trades.csv` and `metrics.json`. No RNG in v1 fills.
4. **Costs are first-class.** No costs, no strategy run (already law). Commission, slippage, and (later) funding are not a post-hoc haircut you forget.
5. **Honest path inside the bar.** OHLC does not tell you whether stop or target printed first. The engine must pick a **stated** rule and write it on the report.
6. **Identity.** Provider, symbol, exchange id, actual dates loaded, `n_bars`. Binance `XAUUSDT` is not COMEX. SPYUSDT is not ES.
7. **No silent lookahead in resampling.** pandas `resample` defaults (`closed='left'`, `label='left'` on most freqs) can stamp a bar with a high that has not happened yet (Quant Arb, “Why is my backtest wrong?”). Session / daily bars in `ask.py` must close the interval on the right and label the close.
8. **Holdout is unused until `validate`.** Discovery cannot see it. Using OOS to pick the winner, then “validating” again, is still overfitting (Quantopian overfitting lecture).
9. **Every cousin is recorded.** Including zero trades and kill failures. López de Prado: if you tried 1,000 specs and quote the best Sharpe, that Sharpe is not a Sharpe — it is the max of a sample. Themis already stores every run id; keep doing that.
10. **Quote only artifacts.** If it is not in `metrics.json` / `table.csv`, it is unknown.

### 2.2 What “good” does *not* mean for v1

A production matching engine (NautilusTrader, LEAN, tick-level MT5) models:

- order book / queue position
- partial fills and latency
- floating spread
- mark-price liquidation
- perp funding every 8h
- intra-bar path from ticks

Themis v1 is **not that**. Go-live is the conversation on files, not an order. Spec already lists **not modeled**: perp funding, intra-bar stop/target path, real fees until Amir writes them. `execution_ready: false`.

A good *research* engine for this product is: **strict causality, next-open fill, stated costs, pessimistic-or-explicit same-bar rule, bar-indexed equity, §18 metrics, floors that refuse theater on gold.**

That is closer to a careful pandas bar-loop than to a broker.

### 2.3 Vectorized vs event-driven vs bar-loop

| Style | How it works | Speed | Realism | Themis fit |
| --- | --- | --- | --- | --- |
| Vectorized (`signal * returns`, vectorbt) | Whole history as arrays | Fastest | Weak fills; easy lookahead; cannot condition on “would I skip this trade after costs” | **Ask / screens / rival definitions.** Not `run`. |
| Sequential bar-loop (pandas/`itertuples` or numpy walk) | One closed bar at a time; pending stop/target; fill next open | Fast enough on 4h (thousands of bars, not millions of ticks) | Honest for swing/stop/target on OHLC if same-bar rule is stated | **v1 `run`.** |
| Event-driven (Backtrader, Nautilus, LEAN) | Events: bar, order, fill, timer | Slow in pure Python; Rust/C# can be fast | Needed when microstructure *is* the edge | Later, if ever. No live in v1. |

Hedge-fund mid-frequency desks still use vectorized screens for idea triage, then a sequential sim for anything they might size (systematicls, 2026). Themis already is that two-step: `ask` then `run`.

Scale check: gold 4h today is ~1.4k bars; BTC 4h from 2022 is tens of thousands. A Python loop over that is milliseconds to low seconds. Do not pick Rust because of speed. Pick a loop because of **causality**.

### 2.4 Same-bar stop and target (the OHLC lie)

This is the #1 engine bug for Themis-shaped trades (entry, hard stop, hard target on 4h/1h).

On bar `k` after entry, both `high >= target` and `low <= stop` can be true. Path is unknown.

Industry practice:

| Policy | Rule | Bias |
| --- | --- | --- |
| Optimistic | Target wins | Inflates win rate. Common silent bug. |
| Pessimistic | Stop wins | Conservative. ManifoldBT, kernc `backtesting.py` market orders (SL priority). |
| Ambiguous | Fill at close (or skip), tag `why=ambiguous_same_bar` | Honest about ignorance. Current `_swing_trades` does this. |
| Tick / 1m path | Resolve from finer bars | Best, not v1 (no tick warehouse). |

**Recommendation:** keep tagging `ambiguous_same_bar` (do not pretend you know the path), and for **kill / screen** treat ambiguous as **stop** (pessimistic). Write the count of ambiguous bars into `metrics.json`. Reports already must say OHLC path is not modeled.

Gaps: a 4h gold bar can be tens of dollars. Filling a stop at the stop price when the bar gapped through is also optimistic. If `open` is through the stop, fill at **open** (gap), not at the stop. Same for target. Spec should eventually say this; v1 code should do it even if YAML does not.

kernc `backtesting.py` documents the same intra-bar ambiguity (issues #119, #242, discussion #989): contingent SL/TP on the entry bar is “somewhat dubious.” Do not outsource this judgment to that library.

### 2.5 Perp-specific costs the engine must *name* even if it does not model them

Binance USD-M:

| Cost | Typical size | Modeled in v1? |
| --- | --- | --- |
| Taker fee | ~4 bps/side (VIP0; exact number is Amir’s to write) | Placeholder `commission_per_side` only |
| Maker fee | lower | Not distinguished |
| Slippage | 1 tick to many bps on thin gold | `slippage_ticks` field exists; engine must actually apply it |
| Funding | every 8h at 00:00/08:00/16:00 UTC; `notional × rate`; longs pay when rate > 0 | **Not modeled.** List it. A swing held over several funding prints is not a 4 bp problem. |
| Liquidation / mark price | leverage | Not modeled. v1 is 1 unit notional, unlevered. |

A strategy that looks fine on price PnL can be a loser after funding on a multi-day gold swing. That is why `execution_ready: false` stays until funding is either modeled or explicitly waived with a reason (“holds < 8h, funding ignored”).

### 2.6 Overfitting is an engine feature, not a report footnote

Bailey, Borwein, López de Prado, Zhu — *The Probability of Backtest Overfitting*; Bailey & López de Prado — *The Deflated Sharpe Ratio* (JoPM 2014):

- Trying many cousins on the same bars **inflates** the best Sharpe. After ~3 independent trials, an SR of 1 on a short sample is often not significant.
- Holdout used more than once is not holdout.
- Walk-forward efficiency: OOS / IS. Rule of thumb in practitioner notes: < 0.3 is curve-fit, > 0.5–0.7 is the interesting band. Not a Themis kill key in v1.
- Deflated Sharpe / PBO are **optional later**, not v1. What v1 already got right: declared `search_space`, new spec ids, floors that **refuse** `tune` on gold, `compare` must not claim “best” when `walkforward_eligible` is false.

Do not add `min_sharpe: 1` as a kill. Spec already forbids it. Short crypto windows produce trophy Sharpes from sparse trades (see §4.4).

---

## 3. Is Python a good option for EDA, hypothesis research, and backtest?

**Yes. It is the default desk language for this product. Use it.**

### 3.1 EDA and hypothesis (`ask`)

Python + pandas (optional polars) is the industry standard for:

- loading OHLCV, time zones, resampling, groupby session/weekday
- event tables (one row per swing / zone touch / session)
- rolling MAE/MFE, ATR, fractals
- binomial rates + CI
- matplotlib Agg for report SVG

Quant teams live here (Quantt, Jansen *ML for Trading*, Quantopian research). R/`PerformanceAnalytics` is historically strong for *ratio catalogs*; Python caught up via pandas + numpy + (optional) `empyrical`/`quantstats`. Themis should **not** import those libraries for v1 — they disagree on Sortino zeros, 252 vs 365, and cash-account assumptions. Compute §18 in `metrics.py` so the canon is ours.

Hypothesis research in Themis is not a t-test on a blog. It is:

1. Pin two explicit definitions (rivals).
2. Count `n` and rates with CI.
3. Look at MAE/MFE **before** inventing a stop.
4. Refuse to multiply hit-rate × R.

pandas is the right tool for (1)–(3). The failure mode is not “pandas is slow.” The failure mode is one English line → one definition → 72% in chat.

### 3.2 Backtest (`run`)

For **single-series swing/stop/target on 1h/4h/1d**, a Python bar-loop is the right engine:

- Enough speed.
- Fills and same-bar policy are visible in 80 lines (you already have them).
- YAML `implements` points at a hand-written module. The runner does not “execute YAML.”
- No AGPL surprise, no vectorbt PRO license, no C# LEAN ingest.

When Python/pandas is the *wrong* backtest tool:

| Situation | Wrong because | Themis v1? |
| --- | --- | --- |
| HFT / queue position | You need ticks and a book | No |
| 5 000 symbols × 10 years, daily rebalance | Vectorized (vectorbt/`bt`) wins | No. Five named perps. |
| Live parity, same code to broker | Nautilus / LEAN / Jesse | No live |
| Options / vol surface | QuantLib | No |

### 3.3 Library scorecard (for this repo, not the internet)

| Library | Use in Themis? | Why |
| --- | --- | --- |
| **pandas + numpy** | **Yes. Core.** | Ask, event tables, equity, metrics, reports. |
| **pyyaml** | Yes | Specs. |
| **matplotlib Agg** | Yes | Dual report SVG. |
| **stdlib urllib** | Yes | Vision zips. |
| **ccxt** | Optional | Live `fapi` is 451 here. |
| **backtesting.py** (kernc) | **Do not make it the source of truth.** Spec still names it as v1 `run` engine; the *actual* `run` is already a pandas loop. AGPL-3.0. Intra-bar SL/TP is explicitly dubious. No funding. Stats assume a cash broker, not 1-unit price pnl. Keep as optional later if a strategy author wants charts — do not compute canon metrics from it. |
| **vectorbt** | No for `run`. Tempting for `tune` sweeps later. | Vectorized fills. Source-available / PRO split. Easy to “optimize” gold into a lie. |
| **Backtrader** | No | Event-driven, slow, maintenance-only. Overkill. |
| **NautilusTrader / LEAN** | No | Live-shaped. DevOps. Not this product. |
| **zipline** | No | Equity calendar, 252-day brain. |
| **quantstats / empyrical** | No in v1 | Convenient, but they will fight §18 (252, Sortino subsample, rf). |
| **polars** | Optional | Faster groupbys if ask tables grow. Not required. |
| **R / MATLAB / C++** | No | Extra language for no gain at this scale. |

**Verdict:** Python 3.11+ is a good option for all three jobs (EDA, hypothesis, backtest) **if** ask stays pandas-event and run stays a causal bar-loop with Themis metrics. It is a bad option if “pandas backtest” means `entries * returns.shift(-1)` and a blog Sharpe.

### 3.4 Recommended engine shape (v1)

```
OHLC DataFrame (closed bars, UTC)
        │
        ▼
   knowable-at mask          ← fractal i+n, ATR from prior bars, no forming bar
        │
        ▼
   signal on bar i           ← zone touch, etc. Never the bounce.
        │
        ▼
   fill at open[i+1]         ← plus commission; plus slippage if written
        │
        ▼
   walk k = i+1 .. end
        high/low vs stop/target
        same-bar → tag ambiguous; pessimistic for kill
        gap through → fill at open, not at the level
        │
        ▼
   trades.csv  (one row per round trip)
        │
        ▼
   equity on the BAR index   ← not on the trade index
        │
        ▼
   metrics.py  (§18)
```

YAML is the contract. Python in `implements` is the strategy. `metrics.py` is shared. Chat quotes the folder.

---

## 4. How to calculate the metrics

Two families. Do not mix keys. Spec §18 is the canon; this section is the literature behind it and the implementation pitfalls.

### 4.1 Ask metrics (pandas, no pnl)

| Key | Formula | Notes |
| --- | --- | --- |
| `n` | event count | Always. Small n is a result. |
| rate (`target_rate`, `stop_rate`, `bounce`, …) | `k / n` | Mutually exclusive outcomes should sum to 1 (± neither). |
| `ci95` | see below | Required when n allows. |
| MAE / MFE | min/max adverse/favorable excursion **after** the event, in price or in ATR | Path stats. How the agent proposes a stop. Not expectancy. |
| bars-to-bounce / bars-to-fail | integer | Outcome timing. |

**CI on a rate.** Current code (`ask.ci95`) is the **Wald** interval:

```text
half-width = 1.96 * sqrt(p * (1-p) / n)
```

Wald is fine when `n` is large and `p` is not near 0 or 1. It is bad at the edges and at small n: zero-width when `p=0` or `1`, and overshoot outside [0, 1]. Wilson (1927) is the usual upgrade:

```text
z = 1.96
center = (p + z²/(2n)) / (1 + z²/n)
margin = z / (1 + z²/n) * sqrt(p(1-p)/n + z²/(4n²))
```

Wilson stays in (0, 1) and is the recommended interval for binomial rates at Themis sample sizes (gold asks: n ≈ 50–180; kill floor 30). Spec currently says “CI on rates when n allows” without naming Wald vs Wilson. **Recommendation for a later spec revision:** write Wilson as `ci95`, keep Wald as a footnote if you must match old folders. Until then, Wald is what the folders already contain — do not silently switch and compare old vs new CIs.

Do not use a t-test on bounce rates across overlapping events as “significance.” Events overlap; bars are dependent. Rival folders + CI overlap (already the ask screen) is the honest test.

### 4.2 Strategy ledger (before any ratio)

Spec equity model (keep it):

- **1 unit notional.** `E0` = first close of the loaded window.
- Each trade’s after-cost `pnl` is in **price** (points), added to equity at the **exit bar**.
- Intrabar mark-to-market: not modeled.
- Write `notional: 1_unit`, `pnl_unit: price`.
- Do **not** invent a $10,000 cash account.

Bar equity `E_i` lives on the **loaded bar index**:

```text
E_0 = first close
E_i = E_{i-1}                          if no trade exits on bar i
E_i = E_{i-1} + sum(pnl of trades that exit on i)
```

Simple returns (portfolio convention, spec):

```text
r_i = E_i / E_{i-1} - 1     if E_{i-1} > 0
```

**Do not** compute Sharpe from the vector of trade pnls. Trade pnls are not a time series: 10 trades on 1h and 10 trades on 1d would look the same. QuantStackExchange consensus: ratios that annualize need a clock. The clock is the bar.

**Current bug:** `runner.py` builds `equity` by appending one point per trade, then `_max_dd` on that. That is a trade-indexed equity curve. Drawdown *timing* and bar-return Sharpe are then wrong (too few points, no flat periods). Spec is explicit: walk the bar index; on bars with no exit, `E_i = E_{i-1}`.

Crypto year: **365** days, not 252. Perps trade weekends. Write `periods_per_year`:

| timeframe | periods_per_year |
| --- | ---: |
| 1h | 8760 |
| 4h | 2190 |
| 1d | 365 |
| other | `365 * 24 / hours_per_bar` |

```text
window_years = calendar_seconds / (365.25 * 86400)
short_window = window_years < 1
```

CAGR and Sharpe on `short_window` still write; HTML captions them. Gold 4h ~7.5 months is short_window. A Sharpe of 2 there is a red flag, not a trophy.

Risk-free `rf = 0` unless the spec names another (funding is already omitted). MAR for Sortino = 0 unless named. `rf_period = rf / periods_per_year`.

### 4.3 Must-write strategy keys (spec §18)

All after costs. Missing → `not_computed: {key: reason}`, never a silent skip.

Let `W` = winning trade pnls, `L` = losing (pnl < 0). Flat trades are neither win nor loss; they still count in `n_trades`.

| key | formula | missing when |
| --- | --- | --- |
| `n_trades` | `len(trades)` | — |
| `pnl` | `sum(trade.pnl)` | — |
| `net_return` | `(E_end - E0) / E0` | `E0 <= 0` |
| `max_drawdown_pct` | `max_i (peak_i - E_i) / peak_i * 100` with `peak_i = max(E_0..E_i)` | empty equity |
| `cagr` | `(E_end / E0) ** (1 / window_years) - 1` | `window_years < 1/365` or `E0 <= 0` or `E_end <= 0` |
| `calmar` | `cagr / (max_drawdown_pct / 100)` | dd is 0 (`reason: max_drawdown_pct=0`). Negative CAGR is a **valid** Calmar — write it. |
| `sharpe` | `((mean(r) - rf_period) / sample_std(r, ddof=1)) * sqrt(periods_per_year)` | `n_returns < 2` or `std=0` |
| `sortino` | `((mean(r) - mar) / downside_dev) * sqrt(periods_per_year)` | `n_returns < 2` or `downside_dev=0` |
| `profit_factor` | `sum(W) / abs(sum(L))` | no trades, or no losses (`reason: no_losses`) |
| `expectancy` | `mean(trade.pnl)` | no trades |
| `win_rate` | `n_win / n_trades` | no trades |
| `payoff_ratio` | `mean(W) / abs(mean(L))` | no wins or no losses |
| `kill_pass` | bool + `kill_failed: [keys]` | — |

**Sharpe details**

- Simple returns, not log. (Log is a research choice; spec picked portfolio convention.)
- Sample stdev `ddof=1` (unbiased). numpy `std(ddof=1)`.
- Annualize with `sqrt(T)`, T = `periods_per_year`. This assumes iid enough to scale. Lo, “The Statistics of Sharpe Ratios”: sqrt(T) **overstates** if returns are autocorrelated. Write the Sharpe anyway; do not “correct” it with a HAC estimator in v1. Caption short_window.
- **Never 252** on a 24/7 perp.

**Sortino details (this is where libraries lie)**

Frank Sortino / CME “A Sharper Ratio”: target downside deviation is RMS of underperformance vs MAR, **including the zeros** for periods that beat MAR.

```text
downside_dev = sqrt( mean( min(r_i - mar, 0)^2 ) )     # over ALL bars
```

Wrong (common): `std(r[r < mar])` — drops the zeros, inflates downside vol, deflates Sortino.

If Sortino << Sharpe on a positively skewed swing system, the code is probably dropping zeros. Spec already chose the full-sample definition. Keep it.

**Calmar details**

Young (1991, *Futures*): original Calmar is **trailing 36 months** of CTA returns / max DD over those 36 months. MAR ratio is inception-to-date.

Themis: **full-sample** Calmar. Write `calmar_window: full_sample`. A 7-month gold run is not a CTA Calmar. Caption it.

**Profit factor vs expectancy vs payoff**

```text
profit_factor = gross_profit / gross_loss          # total $ won / $ lost
expectancy    = mean(pnl)                          # $ per trade (price units)
payoff_ratio  = mean_win / abs(mean_loss)          # size, not frequency
```

Algebra: `expectancy = win_rate * mean_win + (1 - win_rate) * mean_loss` (flats aside).

**Never** compute “expectancy” as `win_rate * R` in chat. That is law 4.

One outlier winner inflates PF. Always look at `n_trades` and the PnL histogram (report HTML).

**Max drawdown**

Peak is a **running** max of equity, then trough after that peak. Percent of that peak, then take the worst (most negative) and store as a positive percent.

Do not use max drawdown of the *trade pnl list*. A +10 then −10 in price after a long grind is not the same as those two trades adjacent.

### 4.4 How each ratio lies (keep this in the HTML captions)

Copied in spirit from spec §18; expanded with the sparse-trade issue Themis will hit.

| metric | question | how it lies |
| --- | --- | --- |
| PnL / net_return | Did we make money on this window, 1 unit, after costs? | No path, no time, no risk. Lucky streak = edge. |
| n_trades / win_rate | How often, and how often green? | Win rate without payoff is not expectancy. |
| expectancy / PF / payoff | Per-trade edge after costs | Small n. One winner inflates PF. |
| max_drawdown_pct | Worst peak-to-trough pain | One number; no duration underwater. |
| CAGR | Compounded annualised growth | Noisy on short_window. Sensitive to start/end. |
| Sharpe | Return per unit of **total** bar vol, annualised | Penalises upside. sqrt(T) assumes iid. **Sparse trades → many zero bars → std collapses → trophy Sharpe.** A swing system with 40 trades on 2000 4h bars will look “high Sharpe” even when expectancy is modest. |
| Sortino | Return per unit of downside bar vol | Better for asymmetric swings. Unstable if few down bars. Should be ≥ Sharpe when skew is positive. |
| Calmar | CAGR per unit of worst DD | Built on **one** observation (the worst DD). Full-sample on 7 months is not 36-month CTA Calmar. |

Industry captions (HTML only, **not** a promotion gate) — same bands as spec:

| | poor | weak | acceptable | exceptional-or-overfit |
| --- | --- | --- | --- | --- |
| Sharpe (ann.) | < 0 | 0–1 | 1–2 | > 2 (verify path, n, costs, zeros) |
| Sortino (ann.) | < 0 | 0–1.5 | 1.5–3 | > 3 |
| Calmar | < 0 | 0–0.5 | 0.5–2 | > 2 |
| Profit factor | < 1 | 1–1.5 | 1.5–2.5 | > 2.5 (check one-trade dominance) |

Kill stays: `min_trades: 30`, `max_drawdown_pct: 40`, `min_net_return: 0` unless the family names other **existing** keys. `compare` ranks kill-survivors by after-cost `net_return`.

### 4.5 Optional keys (write if computed; omit if not)

Spec already listed:

| key | formula | interpret only if |
| --- | --- | --- |
| `sqn` | `sqrt(n_trades) * mean(trade_pnl) / std(trade_pnl)` | Van Tharp; `n_trades >= 30`. Ideally in R-multiples (pnl / initial risk). If risk is not in `trades.csv`, using raw pnl is a cousin of SQN — label `sqn_unit: price`. Tharp bands: <1.6 poor, 2–2.4 average, 2.5–2.9 good, 3–5 excellent, >7 on thin n = overfitting. |
| `omega` | `sum(max(r,0)) / abs(sum(min(r,0)))` on bar returns, threshold 0 | Keating & Shadwick. |
| `recovery_factor` | `pnl / abs(max_dd in price)` | |
| `ulcer_index` | RMS of percent drawdown over time | Depth **and** duration. Martin ratio = CAGR / UI, later. |

v1 may skip these. Do not block a run.

### 4.6 Worked numbers (so `metrics.py` cannot invent a second convention)

Tiny 5-bar 4h window. `E0 = 100`. One long: entry 100, exit 102, cost 0.08, `pnl = 1.92`, exits on bar 3.

```text
E = [100, 100, 100, 101.92, 101.92]
r = [     0,     0,  0.0192,      0  ]
n_trades = 1
pnl = 1.92
net_return = 0.0192
max_drawdown_pct = 0          → calmar not_computed (max_drawdown_pct=0)
window_years = (5 * 4) / (365.25 * 24) ≈ 0.00228  → short_window true
cagr = (101.92/100)**(1/window_years) - 1     # huge; caption short_window
periods_per_year = 2190
mean(r) ≈ 0.0048
sample_std(r, ddof=1) ≈ 0.0096
sharpe ≈ (0.0048 / 0.0096) * sqrt(2190) ≈ 23.4     # trophy on noise (sqrt(2190) ≈ 46.8)
expectancy = 1.92
win_rate = 1.0
profit_factor not_computed (no_losses)
payoff_ratio not_computed (no losses)
```

This is why one ratio is a liar, why gold cannot `kept`, and why Sharpe is not a kill key.

### 4.7 numpy sketch (implementation, not a patch)

```python
r = np.diff(E) / E[:-1]
r = r[np.isfinite(r)]
mu = r.mean()
sig = r.std(ddof=1)
sharpe = ((mu - rf_period) / sig) * np.sqrt(ppy) if sig > 0 and len(r) >= 2 else None

dd = np.minimum(r - mar, 0.0)
downside = np.sqrt(np.mean(dd * dd))          # ALL bars, zeros kept
sortino = ((mu - mar) / downside) * np.sqrt(ppy) if downside > 0 else None

peak = np.maximum.accumulate(E)
mdd = np.max((peak - E) / np.where(peak > 0, peak, np.nan))
max_drawdown_pct = float(mdd * 100.0)
```

---

## 5. What the repo does today vs what “good” is

| Piece | Today | Good / spec |
| --- | --- | --- |
| Ask | pandas, rivals, Wald CI, no pnl | Keep. Consider Wilson later. |
| Run fills | `_swing_trades` next-open, commission × 2, same-bar → close tagged ambiguous | Keep next-open. Apply slippage if written. Gap-through at open. Ambiguous count in metrics; pessimistic for kill. |
| Equity | Trade-indexed list | **Bar-indexed.** |
| Ratios | Hard-coded `not_computed` list | **Compute** via `metrics.py`. |
| `backtesting.py` | Named in spec/README, optional extra in pyproject, **not used by runner** | Align docs: pandas bar-loop *is* the engine. Optional dependency can stay unused. |
| Funding | listed not_modeled | Keep. |
| Holdout / WF / tune floors | eligibility.py | Keep. Gold must not theater. |
| Dual report | MD + HTML required by spec | Graphics from folder only. |

---

## 6. Recommendations (research → spec/build, not a stealth spec change)

1. **Keep Python + pandas as the desk.** It is the right language for EDA, rival asks, and v1 backtests on these five perps.
2. **Treat `ask` and `run` as two engines that share OHLC and YAML, not code paths.** Vectorized event tables vs sequential fills.
3. **Do not adopt vectorbt / Nautilus / LEAN / Backtrader for v1.** They solve a different product.
4. **Do not compute canon metrics from kernc `backtesting.py`.** Either drop it from the “v1 engine” sentence in a later spec revision, or keep it as an optional charting extra. The fill/metrics canon is ours.
5. **Implement `themis/metrics.py` exactly as §18** on bar equity. Delete the permanent `not_computed` list in `runner.py`.
6. **Same-bar policy:** keep the tag; count them; pessimistic for kill.
7. **Gap rule:** if the next open is through stop or target, fill at open.
8. **Wilson CI** for ask rates in a later revision; do not silently change existing folders.
9. **Never annualize 252.** Never Sharpe-from-trade-pnl. Never hit-rate × R.
10. **Funding remains not_modeled** until someone writes an 8h series. Reports must keep saying so. A multi-day gold swing is where this will bite first.

---

## 7. Sources (read, not cargo-culted)

**Engines and bias**

- QuantStackExchange: “Why do we need event-driven backtesters?” (2019)
- Interactive Brokers campus: “Vector-based vs event-based backtesting” (2025)
- systematicls: vectorised vs event-based, one-bar delay (2026)
- Quant Arb, *The Quant Stack*: “Why is my backtest wrong?” — resample lookahead
- Pomegra / look-ahead bias notes: next-bar execution
- kernc/backtesting.py issues #119, #242, #153 — intra-bar SL/TP
- ManifoldBT fill table: same-bar stop wins; gap fills at open
- CoinAPI / Coinbase perp primers: funding as a return driver, not a rounding error
- BullAlert: Nautilus vs Backtrader vs VectorBT (2026) — research vs production split

**Metrics**

- Sharpe (1966); Lo, “The Statistics of Sharpe Ratios” (sqrt(T) is not free)
- Sortino & van der Meer; CME “A Sharper Ratio” — **zeros stay in the denominator**
- Young, Calmar ratio, *Futures* (1991) — 36-month CTA original vs full-sample
- Van Tharp, System Quality Number — `sqrt(N) * mean / std`, n ≥ 30
- Bailey & López de Prado, “The Deflated Sharpe Ratio,” *JoPM* (2014)
- Bailey, Borwein, López de Prado, Zhu, “The Probability of Backtest Overfitting,” *J. Computational Finance* (2017)
- QuantStackExchange: 252 vs 365; CAGR calendar vs trading days — **365 for 24/7**
- Wilson (1927) score interval vs Wald — small-n binomial rates

**Python as the desk**

- pandas time series / resample docs (lookahead warning)
- Jansen, *Machine Learning for Trading* — exploration vs confirmation boundary
- Quantopian lecture: overfitting and abusing out-of-sample
- Practitioner scorecards 2026: vectorbt for sweeps, bar-loop/event-driven for fills

---

## 8. One-page verdict

Themis is not “a pandas backtester.” It is a **talkable research loop** whose measuring machines happen to be written in Python.

- **EDA / hypothesis:** pandas. Rival definitions. Rates + CI. MAE/MFE. No pnl.
- **Backtest:** a causal bar-loop over the same DataFrames. Next-open fill. Stated costs. Honest same-bar tag. Bar-indexed equity.
- **Metrics:** §18, computed, not wished. One ratio is a liar. Kill is not a Sharpe gate. Gold stays thin.
- **Python:** yes. It is the right option. The risk is not the language. The risk is using vectorized research as if it were a fill.

## 9. Landed (same day)

Vulcan/desk pass after this note:

- `themis/metrics.py` — §18 on bar-indexed equity. `not_computed` is a name→reason map. Year is 365.
- `runner.simulate_exit` — gap at open; same-bar both-hit fills the stop and tags `ambiguous_same_bar`; slippage applied when written.
- `run` writes `equity.csv` on the bar index. Permanent `not_computed` list is gone.
- Spec/README: pandas bar-loop is v1 `run`. kernc `backtesting.py` is not a dependency.

Wilson CI, funding, and dual HTML reports are still later. Not this pass.

End of note.
