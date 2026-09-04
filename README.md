# Themis

**Themis** is a research loop you can talk to. You ask in English. It freezes a YAML, pulls the OHLC you named, measures, and only then lets a trade exist. The spec is the law. A named run is the verdict.

This repository is **Themis**. The package and CLI name is `themis`.

The implementation spec is [`docs/open-spec.md`](docs/open-spec.md). It supersedes [`prompt.md`](prompt.md) for implementation. Research notes sit under [`docs/themis-research/`](docs/themis-research/).

Go-live means **this conversation works**, not that an order is sent:

```
you:  how many times has price bounced after a 75% retracement
      on gold, 4 hour?

      → question YAML → fetch that OHLC → pandas ask
      → run folder: e.g. 70% of events bounced (n = …)

you:  if from that retracement I target 1:1 R, what is the return?

      → if stop / bounce / impulse are still vague, the agent does
        more pandas asks (MAE/MFE, where price dies, rival definitions)
      → those folders decide the strategy YAML — not a guess, not a quiz
      → then pandas bar-loop + metrics.py
      → run folder: return, pnl, drawdown, calmar, cagr, sortino, …

you:  create the strategy and backtest
you:  optimize
you:  create the indicator / alert

      → only after a hypothesis is kept
```

v1 venue is **Binance USD-M** (`binanceusdm`). Series: `XAUUSDT` (gold perp, not COMEX), `BTCUSDT`, `SOLUSDT`, `SPYUSDT` (ETF perp, not ES), `QQQUSDT` (ETF perp, not NQ). Same ticker on another venue is a different series.

## What this is

| Layer | Job |
| --- | --- |
| Talk | English. Examples in [`questions.md`](questions.md). |
| YAML | Structure only: what to measure, or what the trade is. |
| Data | **v1: Binance USD-M.** csv, Vision (first-class), optional ccxt. You name the series. Gold 4h → this venue’s `XAUUSDT` perp. |
| `ask` | pandas on the YAML. Counts, bounce rates, percentiles. No pnl. Then **HTML + notebook** so you can review and redefine the ask. |
| `run` | Load `implements` (family template). Shared fill + `metrics.py`. YAML is not executed. |
| `compare` / `tune` | Several cousins. Optimize = new spec ids, same family. |
| Indicator / alert | After a spec is **kept**. Visual or alert twin of that spec. Not a shortcut around the backtest. |
| Runs | Only numbers anyone may quote. |

An agent may turn English into YAML and point `implements` at a family module. It must not invent a 70%, a return, or “this looks profitable.” If a metric is not in a run folder, it is unknown. YAML is **not** executable. Same shape, new numbers → same `implements`, numbers on the YAML. New kind (ORB, FVG, Po3) → a new family module, or `needs_human`. Not a new `.py` per chat line. Not a silent 0.618 in the runner.

## How the agent fills in the gaps

You will often omit the hard parts: what counts as an impulse, what a bounce is, where the stop lives, which session. **The agent should not quiz you as the default, and must not invent those fields.**

It writes extra **question** YAMLs and runs pandas until the folders can support a choice:

- rival definitions (61% vs 75%, bounce = close back through 50% vs a 1×ATR reaction)
- path stats after the event (MFE / MAE, bars to bounce, bars to invalidation)
- session / weekday splits if the English mentioned them

Then it proposes the strategy YAML **citing those ask folders** (stop beyond typical MAE, target 1R, and so on). You can override. If two definitions are still tied, it keeps both as cousins and `compare`s after `run`.

Ask once only for things pandas cannot know: which **provider** if you omitted it, whether costs are zero on purpose, or whether you meant a different timeframe. v1 is locked to Binance. Bybit or Bitget in English is `needs_human`. “Gold on Binance” is Binance `XAUUSDT`.

## Questions vs edge

- **Ask** answers behavior: `n`, bounce rate, range, MAE/MFE, “70% of the time.” That is not expectancy and not a reason to size a position. It **is** how the agent chooses definitions and a stop/target to try.
- **1:1 from the zone** is a trade. Entry, stop, target, session, and costs go in a **strategy** YAML **after** the asks that justified them, then `run`. Do not fake a return by multiplying 70% × 1R in chat.
- **Optimize** enumerates a declared `search_space`. Each candidate is a new spec id. `compare` ranks the family.
- **Worth trading / kept** = one cousin beat the rest on the strategy metrics after costs, passed kill rules, holdout was unused in discovery, then `validate` once.
- Do not promote an `ask` table into a strategy by renaming it.

## Strategy metrics

Every strategy run should write whatever the engine actually computed, and aim for this set:

- return (net, after costs)
- pnl
- max drawdown
- trade count
- and, when computed: calmar, cagr, sortino (sharpe, profit factor if present)

`compare` prints only keys that exist. It does not invent a Calmar. Rank survivors of `kill` by **after-cost net return** unless the family YAML names another key.

## Data

**v1 venue: Binance** (`binanceusdm` USD-M). **Vision** is first-class (`data.binance.vision` monthly kline zips). **csv** is the acceptance path. **ccxt** is optional and must not be assumed (live `fapi` may be HTTP 451).

Do not build a warehouse. Do not backfill every venue in advance. Do not merge the same ticker across venues.

1. Name **provider** in the ask. v1 is `binance`. If you also name the symbol, that is the series. If you say “gold” and Binance but no ticker, `XAUUSDT` perp. If you omit the venue, the agent asks once — it does not pick one. Naming Bybit/Bitget is `needs_human` in v1.
2. Pull Vision or csv into `research/.cache/binance/binanceusdm/<symbol>/<tf>.csv` (gitignored). CSV is allowed if you already have the file.
3. Fetch only the requested symbol + timeframe + range. If that venue cannot give 2022–2024, the run states the dates **actually** loaded.
4. A lookalike is still that venue’s product. Binance `XAUUSDT` ≠ another venue’s `XAUUSDT` ≠ `XAUT` ≠ `PAXG` ≠ COMEX. Do not relabel. SPY/QQQ reports say ETF perp, never ES/NQ.
5. Forex spot and cash/futures indices are **not** this book (except a venue’s own named perp, which must stay labeled). Do not fetch Yahoo/`EURUSD=X` / `NQ=F`.

After every `ask`, Themis writes Markdown (quoteable), **HTML** (review), and a **notebook** (live call of `themis.ask`, Themis .venv kernel). Use HTML + notebook to redefine definitions — new spec id, same idea slug. Do not edit a number in a cell and quote it. The run folder is still the record. Families / fill / metrics stay shared Python.

## Hard rules

1. No spec, no run.
2. No stated costs, no **strategy** run. `ask` does not invent costs.
3. Discovery cannot read the locked holdout. Validation is a separate command, once.
4. Record every cousin, including failures and zero trades.
5. Quote metrics only from `runs/<id>/`.
6. Name the exact instrument. v1 provider is **binance**. Same ticker on two venues is two series.
7. Bars in cache are price-ready, not execution-ready.
8. A forward value (bounce, 1R touch) is an outcome, never an input and never `rules.entry`.
9. `ask` measures. `run` trades. Edge is a backtest comparison.
10. Indicator / alert comes **after** kept. Paper and live are never implied by a backtest.

## Tooling

| Stage | Tool |
| --- | --- |
| English → YAML | `themis compile` (default backend `mock`). Live `xai`/`openai` after `themis login`. Skill file later. |
| Bars | Binance USD-M via Vision or CSV (optional ccxt) |
| Behavior | pandas (polars optional) |
| Trade / optimize | `implements` family + `themis.fill` + `metrics.py` (§18) + declared search space |
| Indicator / alert | After kept — e.g. a Pine twin of the winning spec |
| Where | local Python 3.11+ **inside `research/python/.venv`** (Colab optional) |

Python packages live **only** in that repo env. Bootstrap: `cd research/python && ./bootstrap.sh`. Do not `pip install --user`, do not sudo pip, do not use Apple’s Command Line Tools interpreter as the desk.

No DuckDB warehouse. No “download everything first.”

## Layout (when implemented)

```text
research/
  questions/      question YAML (structure for ask)
  specs/          strategy YAML (structure for the Python port)
  python/         themis + .venv (never global pip); strategies/ = family templates
  notebooks/      idea + report notebooks (representation of Python; redefine the ask from here)
  runs/           one folder per attempt
  reports/        Markdown from runs
docs/             open-spec.md and research notes
```

## Build brief

Start with [`docs/open-spec.md`](docs/open-spec.md). That is the implementation spec. It supersedes [`prompt.md`](prompt.md).

Example English lives in [`questions.md`](questions.md). Compiler contract: [`docs/themis-research/compiler/interface.md`](docs/themis-research/compiler/interface.md).
