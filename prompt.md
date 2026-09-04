# Prompt: build Themis

Copy everything below the line into a coding agent (Grok Build, OpenCode, Claude Code, Colab, etc.). Do not add a trading OS, live broker, warehouse, or ML search. The product is **Themis**, in this repository.

---

## Role

You are implementing **Themis** in the **themis** repo. The package and CLI are `themis`. Do not call this tree anything else.

The spec is the law. A named run is the verdict. YAML **structures** a question or a strategy; it is **not** an interpreter and not executable. You write YAML, then pandas or a Python `backtesting.py` strategy that implements that YAML, then a run folder. You do **not** invent market statistics. If you did not execute something that wrote a metric into a run folder, the metric is unknown.

## What “go live” means

The operator can have this conversation and get file-backed answers:

1. *“How many times has price bounced after a 75% retracement in gold, 4 hour?”*  
   → question YAML → fetch that OHLC → `ask` → e.g. bounce rate and `n` from the folder. A number like 70% is **behavior**, not edge.
2. *“If from that retracement I target 1:1 R, what is the return?”*  
   → not a chat multiply of 70% × 1R. If stop / impulse / bounce are unstated, **do not quiz and do not guess**. Write more question YAMLs, `ask` pandas (rival definitions, MAE/MFE, time-to-bounce vs time-to-fail), then freeze the strategy YAML **from those folders**. Write the Python, `run`. Return / pnl / drawdown come from the strategy folder.
3. *“Create the strategy and backtest.”*  
   → same as (2) if not already done; family of cousins if “best” or several stops/targets.
4. *“Optimize.”*  
   → declared `search_space` only; each candidate a new spec id; `compare`.
5. *“Create the indicator / alert.”*  
   → only after a hypothesis is **kept** (discovery winner + one holdout `validate`). Emit a visual/alert twin of **that** spec. Do not start here.

Do **not** place orders. Do **not** build a broker. Go-live is this loop working.

## Mission (do this, only this)

Build the smallest harness that can:

1. Take English (or a row from [`questions.md`](questions.md)) and freeze **question** YAML
2. `fetch` the OHLC the spec names from **Binance, Bybit, or Bitget via ccxt** (or a CSV)
3. `ask` with pandas and write a run folder
4. When the operator asks for return / 1:1 / a trade: use pandas `ask` to determine missing trade fields, then freeze **strategy** YAML, write Python that matches it, `run`
5. `tune` only inside `search_space`; `compare` the family
6. Report Markdown **only** from run folders
7. After kept: optional indicator/alert twin — stub or skip in the first pass if time is short; do not block `ask`/`run` on it

First concrete path if unspecified:

- Operator English: 75% retracement bounce on gold 4h. Operator names the **provider** (`binance` / `bybit` / `bitget`) and optionally the symbol. If they name a venue but not a ticker, that venue’s `XAUUSDT` perp. Write `data.provider` and the identity note.
- Question YAML + `ask` (bounce rate, `n`)
- If they then ask 1:1 return: more `ask`s to choose stop/invalidation from MAE/MFE and rival definitions, then strategy YAML + Python + `run`. Ask the operator only for provider (if omitted), timeframe/costs pandas cannot infer.

Colab is an allowed desk: same YAML, same cache/CSV, same run folders. Chat is not the record.

`docs/open-spec.md` supersedes this file. The conversation command is `themis idea`. Project skill: `.grok/skills/themis-loop/` (`/themis-loop`).

## What `questions.md` is

Example English for that conversation. Not a ship list. Not a compiler spec. Implement enough to run the retracement bounce ask (or U1). Grow YAML fields when a real question needs them.

## Question vs strategy vs family

| Kind | What it is | What runs |
| --- | --- | --- |
| Question YAML | Structure for pandas: population, condition, outcome | `ask` |
| Strategy YAML | Structure for a human/agent-written Python strategy | `run` (`backtesting.py`) |
| Family | Several strategy YAMLs from one “best / 1:1 / optimize” ask | `run` each, `compare` |

A bounce rate is `ask`. A 1:1 return is `run`. Never answer return by scaling a hit-rate.

**Pandas decides the missing pieces.** Vague English is a stack of question YAMLs, not a questionnaire. The agent proposes 2–4 explicit definitions, `ask`s each, quotes the folders, and only then writes `rules.stop` / `rules.entry` / `definitions.bounce`. If the asks tie, keep cousins and let `compare` after `run` pick. Chat may not invent a stop “that feels right.”

A forward label (bounce, 1R touch, fill) is an **outcome**. It cannot be `rules.entry`.

## Data

**Providers: Binance, Bybit, Bitget.** ccxt is the client. This is not a warehouse. The operator names the venue (and usually the symbol).

- `data.provider`: `binance` | `bybit` | `bitget` (required; the venue that produced the bars)
- `data.source`: `ccxt` | `csv`
- `data.exchange`: ccxt id for that venue
  - Binance: `binance` (spot) or `binanceusdm` (USD-M / TradFi perps). Default for Binance `XAUUSDT`: `binanceusdm`
  - Bybit: `bybit` (spot) or `bybit` linear USDT perps (stock / ETF / commodity as tagged)
  - Bitget: `bitget` (spot) or Bitget USDT-M (including RWA-tagged perps). Bitget **MT5 CFD** is not this exchange id
- Spec must name `symbol` and `timeframe`
- Fetch only the requested range into `research/.cache/<provider>/<exchange>/<symbol>/<tf>.csv` (gitignored)
- If that venue returns a shorter history than `discovery`/`holdout`, the run records the **actual** start/end and row count. Do not label missing years as present
- “Gold” + a named provider → that venue’s `XAUUSDT` perp. Refuse to merge Binance / Bybit / Bitget `XAUUSDT`, or `XAUT` / `PAXG` / `GC=F`
- Same ticker on two providers is two series. Never concatenate or compare as one book
- Forex spot and cash/futures indices are out of these three books unless the operator named that venue’s own perp (still labeled as that perp). Do not pretend Binance `EURUSDT` is EUR/USD or that a crypto index perp is CME NQ
- Long 5m/15m: paginate ccxt. Optional later venue-specific bulk zip (e.g. `binance_vision`) is not week-one unless needed

No downloader farm. No DuckDB. No backfill-everything. No silent fourth venue.

## Non-goals (refuse these)

- Warehouses, historical backfill farms, DuckDB, Parquet lakes
- Live execution, broker APIs, Docker trading OS
- Strategy grammar, genetic search, “AI make it profitable”
- ML models inside `ask` or `run`
- Treating YAML as a program that runs itself
- Answering return / “best” from an `ask` table
- Multiplying a bounce rate by R in chat
- Building extra skill directories beyond `.grok/skills/themis-loop/`
- Starting with indicator/alert before a kept spec

Allowed stack: `ccxt` (Binance, Bybit, Bitget only in v1), `pandas`, `numpy`, `pyyaml`, `backtesting.py`. Optional: `polars`. Do not add yfinance in this pass.

## Hard rules you must implement

1. **No spec, no run.** Missing required fields → exit nonzero.
2. **No costs, no strategy run.** Zero only as written `0` plus a reason. `ask` does not take costs.
3. **No lookahead.** Closed bar in, fill at **next open** unless the spec says otherwise and why.
4. **Holdout lock.** Every spec has `discovery` and `holdout`. Default `ask` / `run` load only discovery. `validate` is holdout, only after a discovery folder exists.
5. **Trial accounting.** Every attempt gets a run id. Families store child run ids.
6. **Quote rule.** Cite only `runs/<id>/metrics.json` or `table.csv`. Never estimate.
7. **Tune / cousin = new spec id.** Never overwrite a parent.
8. **Question ≠ strategy.** `ask` never writes trades, pnl, or expectancy. `run` refuses a question spec.
9. **Exact identity.** Provider is `binance`, `bybit`, or `bitget` as named. Symbol + ccxt exchange id. Same ticker, different venue = different series.
10. **Price-ready ≠ execution-ready.**
11. **Knowable-at.** The retracement zone used as a condition must be knowable at the signal bar. The bounce/1R is the outcome.
12. **Promotion.** `run` = discovery. `validate` = holdout. Indicator/alert only after kept. None of these say paper or live.
13. **Offline without AI.** CLI or Colab runs from spec + cache/CSV.
14. **Family honesty.** `compare` lists every cousin. No “best” with one run.
15. **YAML is structure.** The runner does not “execute YAML.” It loads YAML, then calls pandas or a Python strategy module named by the spec (or derived from `id`).

## Target tree

```text
research/
  README.md
  questions/
    _template.yaml
    retrace-75-bounce-xau-4h-v1.yaml
  specs/
    _template.yaml
    <hypothesis-id>.yaml
  python/
    pyproject.toml or requirements.txt
    themis/
      spec.py
      data.py          # binance | bybit | bitget via ccxt | csv; date clamp; cache
      runner.py        # fetch | ask | run | validate | report | compare | tune
      ask.py           # pandas
      report.py
    strategies/
      <hypothesis-id>.py    # hand-written from the YAML
  notebooks/
    themis.ipynb
  runs/
    .gitkeep
  reports/
    .gitkeep
```

Keep the root [`README.md`](README.md). User-facing name is **Themis** / `themis` only.

## Question spec (required fields)

```yaml
id: retrace-75-bounce-xau-4h-v1
kind: question
title: Bounce after 75% retracement
question_ref: R1
hypothesis: >
  After a confirmed 75% retracement on this 4h series, price often
  bounces before invalidation.
instrument:
  symbol: XAUUSDT
  venue: binance
  timeframe: 4h
  timezone: UTC
data:
  provider: binance            # binance | bybit | bitget — as the operator named
  source: ccxt
  exchange: binanceusdm        # bybit linear or bitget USDT-M when those are named
  csv_path: null
  identity_note: "This venue's XAUUSDT perp is not spot XAUUSD and not another venue's XAUUSDT"
discovery:
  start: 2022-01-01
  end: 2024-12-31
holdout:
  start: 2025-01-01
  end: 2025-12-31
population: events                # event rows, not every bar
condition:
  - kind: retracement
    pct: 0.75
    # agent must pin: impulse definition, confirmation, invalidation
outcome:
  name: bounce
  kind: flag
horizon: 10                       # bars; outcome only
groupby: []
stats: [n, rate]
definitions:                      # required when English is vague
  impulse: ...
  bounce: ...
  invalidation: ...
forbidden:
  - forming_bar_signals
  - future_as_condition
  - unlabeled_substitute_series
```

Reject if required fields are missing. If `definitions` are still `...`, do not ask the operator to invent them. Write one question YAML per candidate definition (small, explicit), `ask` them, then fill `definitions` from those folders. Ask the operator only when the **provider**, symbol, or timeframe is unnamed, or costs are missing for a `run`. Do not pick a venue.

`ask` writes `runs/<utc>-<spec-id>-<short-hash>/` with `spec.yaml`, `meta.json` (`kind: question`, `stage: discovery|validation`, `execution_ready: false`), `metrics.json`, `table.csv`, `engine.log`, `status.json`. No `trades.csv`. No pnl keys.

## Strategy spec (required fields)

```yaml
id: retrace-75-1r-xau-4h-v1
kind: strategy
title: 75% retrace, 1R target
family: retrace-75-xau-4h-v1
implements: strategies/retrace-75-1r-xau-4h-v1.py
hypothesis: >
  Enter on next open after the 75% zone is touched, stop beyond
  invalidation, target 1R, after costs on the named venue's XAUUSDT 4h.
instrument:
  symbol: XAUUSDT
  venue: binance
  timeframe: 4h
  timezone: UTC
data:
  provider: binance            # binance | bybit | bitget — as named
  source: ccxt
  exchange: binanceusdm
  csv_path: null
  identity_note: "This venue's XAUUSDT perp is not COMEX gold and not another venue's XAUUSDT"
discovery:
  start: 2022-01-01
  end: 2024-12-31
holdout:
  start: 2025-01-01
  end: 2025-12-31
costs:
  commission_per_side: 0.0004
  slippage_ticks: 1
  cost_unit: fraction_of_price
  notes: "Placeholder until operator sets real fees"
rules:
  fill: next_open
  calc_on_closed_bar: true
  entry: next open after 75% zone touch
  exit: target or stop
  stop: beyond invalidation
  target: 1R
  size: 1
  filters: []
forbidden:
  - forming_bar_signals
  - same_bar_fill
  - future_pivots
kill:
  min_trades: 30
  max_drawdown_pct: 40
  min_net_return: 0
search_space: {}
```

`implements` points at the Python that is the real strategy. YAML is the contract that Python must match. If they disagree, the run is invalid.

## Strategy metrics (write these when the engine has them)

Required to attempt: `n` / trade count, `net_return`, `pnl`, `max_drawdown_pct`.

Write if `backtesting.py` (or a small post-pass) actually computed them: `cagr`, `calmar`, `sortino`, `sharpe`, `profit_factor`.

Never invent a ratio. Put missing names in the report **not computed** list.

`compare` ranks cousins that pass `kill` by `net_return` unless the family names another existing key.

## Runner CLI

```text
fetch --spec questions/retrace-75-bounce-xau-4h-v1.yaml
ask --spec questions/retrace-75-bounce-xau-4h-v1.yaml
run --spec specs/retrace-75-1r-xau-4h-v1.yaml
validate --spec specs/retrace-75-1r-xau-4h-v1.yaml --from-run runs/<discovery-id>
compare --family retrace-75-xau-4h-v1
tune --spec specs/retrace-75-1r-xau-4h-v1.yaml
report --run runs/<id>
```

`fetch` uses whatever symbol/timeframe the spec names.

`ask` rejects strategy-shaped specs and rejects “what is the return / expectancy” with no strategy spec.

`run` loads the Python in `implements`, discovery bars only, stated costs.

`tune` refuses an empty `search_space`. Each trial is a new spec id + run.

`compare` reads every discovery run in `family`. Must not claim validation.

## Report

From artifacts only: spec id, family, hypothesis, exact series, actual dates loaded, sample quality, metrics that exist, kill status, family rank, link to folder, **not computed**. No “take this live.”

## Environment

- Python 3.11+
- Pin `backtesting`, `pandas`, `numpy`, `pyyaml`, `ccxt`
- Optional: `polars`, `yfinance`
- Cache: `research/.cache/`, gitignored
- Colab notebook may call the same functions

## Desk

Themis is files. Any terminal agent may compile English → YAML → Python. Do not add a new LLM login. Grok Build runs the loop via `.grok/skills/themis-loop/`.

## Acceptance checks

1. Root README is Themis-only.
2. One real question YAML (retracement bounce or U1) + one real strategy YAML + matching Python (can be a tiny fixture strategy).
3. `fetch` can pull a named Binance / Bybit / Bitget symbol/timeframe via ccxt **or** load CSV if offline. `meta.json` records `provider` as named.
4. `ask` refuses missing holdout and refuses a return question with no strategy spec.
5. `run` refuses missing costs or holdout; writes a folder on zero trades.
6. Discovery loads no holdout timestamps.
7. `report` works offline from a folder.
8. No rate, return, or pnl printed except from `metrics.json` / `table.csv`.
9. Question folder has no `trades.csv` and no pnl keys.
10. `compare` on two fixture cousins lists both.
11. Project skill `.grok/skills/themis-loop/SKILL.md` exists.

## Order of work

1. Scaffold + both spec schemas + reject-invalid tests
2. `data.py`: named provider (binance | bybit | bitget) via ccxt + CSV + clamp + cache
3. `ask` + retracement-bounce or U1 fixture
4. `run` + one strategy Python linked by `implements`
5. Report + `validate`
6. `compare` + `tune` stub (error if `search_space` empty)
7. Optional Colab twin

Stop when the operator conversation through **backtest** works on one series. Indicator/alert can wait until something is kept. Do not implement the whole question bank. The shipped name is **Themis**.
