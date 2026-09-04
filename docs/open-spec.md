# Themis open spec

Minerva. 2026-08-28. This is the spec. Not a build.

Supersedes `prompt.md` for implementation. Research notes sit beside this file; they are not the spec.
Vulcan forges from this document. Fixtures, event tables, and Vision CSVs stay off git.

Canon pointer: root `SPEC.md`. This file is the implementation spec.

Revision 2026-08-28e (ask review): every `ask` ships a notebook **and** HTML with the run folder. Logic stays in Python (`themis.ask`). The notebook is a live representation so the operator can review definitions and **redefine the ask** (new spec id, same idea slug). HTML is the desk view. Markdown + `metrics.json` remain quoteable. Chat still does not invent numbers.

Revision 2026-08-28d (family templates): `run` loads `implements` and calls `trades(spec, df, ...)`. Same shape, new numbers → same module, numbers in YAML. New kind → new `strategies/<family>.py` or `needs_human`. No silent 0.618 in the runner.

Revision 2026-08-28c (run engine): pandas bar-loop is v1 `run` (not kernc `backtesting.py`). `metrics.py` computes §18 from bar-indexed equity. Same-bar stop+target is tagged `ambiguous_same_bar` and filled at the stop. Gap through a level fills at open. Slippage ticks are applied when written.

Revision 2026-08-28b (ideas, dual reports, metrics canon, compiler prompt): §§17–20. Laws 16–20. Live compile must use the prompt in §20.

## 1. Product

**Themis** is a research loop you can talk to. English in. YAML frozen. Then pandas writes a run folder (`ask` event tables; `run` loads `implements`, shared fill + metrics). Chat does not invent numbers.

Go-live is that conversation working on files. Not an order. Not a broker. Not a warehouse.

The conversation this product is for:

```
you:  I have an idea: 1h swing high/low, wait a 61.8 retrace,
      stop is the low + 1 ATR, target the high. Call it h1-618.

      → name the idea (`h1-618`)
      → freeze YAML (named fields pinned; rivals only for what
        you did not name)
      → pandas `ask` on every question in the plan
      → dual report (Markdown + HTML with graphics) from those
        folders: is the path even a thing?
      → if you then ask return / pnl / "how good", `run` after
        costs, then dual report with equity, drawdown, ratios

you:  bring back h1-618, try stop 2 ATR

      → same slug, new spec ids, parent recorded
      → ask again, then run if the English is a trade
      → lineage stays so we can improve instead of forgetting
```

An **idea** is a named lineage of specs and runs. A **spec id** is one freeze. A **run** is one measurement. Improving an idea never overwrites a parent.

Package and CLI name: `themis`. Repository: `fortvna/themis`.

v1 venue is **Binance** (USD-M perps via `binanceusdm`). Series:

| symbol | English | identity |
| --- | --- | --- |
| XAUUSDT | Gold | this venue's gold perp, not COMEX, not another venue |
| BTCUSDT | BTC | this venue's BTC perp |
| SOLUSDT | SOL | this venue's SOL perp |
| SPYUSDT | SPY stand-in | ETF perp, **not ES** |
| QQQUSDT | QQQ stand-in | ETF perp, **not NQ** |

Same ticker on another venue is a different series. Do not merge. Do not relabel.

## 2. Law

1. No spec, no run.
2. YAML is structure. It is not executed. pandas or a Python strategy named by `implements` is executed.
3. Freeze YAML before any metric is spoken. Compiler writes YAML. Engines write `metrics.json`.
4. `ask` measures behavior. `run` trades. A rate is not return. Do not multiply hit-rate × R.
5. Quote metrics only from `runs/<id>/metrics.json` or `table.csv`.
6. Rival asks are first-class. Vague English → at least two explicit definitions, two folders, then maybe a strategy.
7. `ask` never writes trades, pnl, or expectancy. `run` refuses a question spec.
8. No costs, no strategy `run`. Zero only as written `0` plus a reason.
9. No lookahead. Closed bar in. Fill at next open unless the spec says otherwise and why. A swing at bar `i` with fractal `n` is knowable at `i+n`.
10. Discovery cannot read holdout. `validate` is a separate command, once. `walkforward` is rolling folds, a different command.
11. Tune = declared `search_space`, each candidate a new spec id. Empty space errors. Tune requires `walkforward_eligible`.
12. Kept = one cousin beat the family on after-cost net return (or the family key), passed kill, one successful `validate`, holdout unused. Indicator/alert only after kept. None of this is paper or live.
13. Exact identity. Provider, symbol, exchange id, actual dates loaded, row count.
14. No warehouse. No live orders. No fourth venue in v1. No paid SDK call. No spend. No tokens in git. Live compile only after `themis login` and Amir says to leave mock.
15. English compiler does not pick a venue or a series.
16. Ideas have a slug. Improving an idea is a new spec id on the same slug. Never overwrite a parent YAML or a parent run folder.
17. `report` writes Markdown, HTML, and (for asks) a notebook from the same run folder. HTML and the notebook may graph/call only data and Python that folder/spec already name. Chat still quotes `metrics.json` / `table.csv`, not the picture and not an edited cell.
18. Ratios are computed by the engine from equity and trades. Missing → `not_computed` plus a reason. Chat does not invent a Sharpe, and does not promote on one ratio.
19. "Worth it" is a **screen**, not `kept`. Ask screens path stats. Run screens after-cost kill + the metric set in §18. Neither is paper or live.
20. Live Themis compiles with the prompt in §20. Do not freelance a friendlier prompt that rewrites a named stop or speaks a metric.

## 3. Compiler

English (later image/video) in. `themis.job.v1` out. Then engines run the job.

```
compile(english, series, media=[]) -> Job
```

- `series` is `{provider, symbol, timeframe}` as named. Compiler does not pick.
- `media` is later: `[{type: image|video, path}]`. v1 mock returns `unsupported` for media and still compiles the text. Do not block the text path.

Contract: Prometheus `themis-research/compiler/interface.md`. Shape:

```yaml
schema: themis.job.v1
status: ok | needs_human | error
source:
  english: "..."
  media: []
  compiler: mock          # mock | xai | openai
  model: mock             # live: provider model id after themis login
instrument:
  provider: binance
  symbol: XAUUSDT
  timeframe: 4h
  exchange: binanceusdm
idea:
  slug: h1-618                 # operator-named, or compiler-proposed
  title: "1h 61.8 retrace, stop low+1ATR, TP swing high"
  version: 1
  parent_spec_ids: []
named:                         # fields the English actually named
  timeframe: 1h
  retrace_pct: 0.618
  stop: {anchor: swing_low, op: "+", k: 1, unit: ATR}
  target: {anchor: swing_high}
plan:
  - kind: question
    id: ...
    purpose: rival_definition | path_stats | session_stats
    yaml: path
  - kind: strategy        # only after required asks exist in the plan
    id: ...
    requires: [question ids]
    yaml: path
    run_eligible: false
    walkforward_eligible: false
    tune_eligible: false
gates:
  freeze_yaml_before_metrics: true
  rivals_min: 2
  ask_before_run: true
  tune_requires: walkforward_eligible
  named_fields_pinned: true
  idea_slug_required: true    # when status is ok; blank jobs have no slug
  dual_report: true
```

### Backends

One protocol. No vendor import in the harness core.

| id | when | spend |
| --- | --- | --- |
| `mock` | default now | none. maps known English to frozen YAML. Never networks. |
| `xai` | after `themis login xai` | none until Amir says to compile live. Grok via xAI. |
| `openai` | after `themis login openai` | none until Amir says to compile live. |

Do not lock a paid vendor. Do not put tokens in the repo. Do not paste keys into YAML.

### Login (OAuth)

v1 compiler auth is an OAuth login on the operator machine, not an API key in git.

```
themis login xai
themis login openai
themis logout xai
themis logout openai
themis whoami
```

Flow:

1. CLI starts OAuth 2.0 **device-code** (works on a headless desk). Prints a URL and a short code.
2. Amir opens the URL, signs in, approves.
3. CLI polls until approved, then stores tokens under `~/.themis/auth.json` (gitignored, never copied into the repo).
4. Access token refresh is silent. If refresh fails, `compile` with that backend exits: not logged in.
5. Browser loopback is allowed as an extra path when a local browser exists. Device-code is the default so a remote desk still works.

`themis login xai` talks to xAI (`auth.x.ai` device-code / browser, same family as `grok login`). Tokens are Themis's copy under `~/.themis/`, not a rewrite of `~/.grok/auth.json`. Reuse of an existing Grok CLI session is allowed only if Amir opts in at the prompt.

`themis login openai` talks to OpenAI's user OAuth (ChatGPT / Codex-style device-code). Not an Azure Entra app. Not a key pasted from the dashboard. Dashboard API keys are out of v1 unless Amir later asks for `themis login openai --api-key` as an escape hatch.

Live `compile --backend xai|openai` refuses if that provider is not logged in. Exit nonzero. Do not fall back to mock. Do not prompt for a pasted key. There is no `THEMIS_LLM_KEY`. Mock ignores login. `themis whoami` prints provider, logged-in or not, never prints the token.

No spend: login does not call the model. First live compile is a later order from Amir.

Unknown English under mock: `status: needs_human` and a blank Job skeleton. Do not invent definitions. Do not invent metrics.

The compiler may write YAML only: question specs, strategy specs, the Job, and `research/ideas/<slug>/idea.yaml` (structure: slug, title, english, spec ids, parent). It may not write `metrics.json`. It may not fill idea `screen` or `runs` — engines do that after pandas / `run`.

Live backends use the system prompt in §20. Mock obeys the same law without calling a model. Pin+refuse named fields (ADR `live-compile-named-stop.md`): overlay `job.named` onto every YAML **after** the model and **before** write; `compile` exits nonzero if a named stop/target is missing or disagrees. Rivals only for **unnamed** keys. New spec ids. Cousins copy `job.named`.

## 4. Gated ladder

The loop is coherent. The ladder on every symbol is not. Eligibility is computed from **actual loaded bars**, not from prompt.md dates.

### Stages

| stage | command | writes | promotion |
| --- | --- | --- | --- |
| compile | `compile` | Job + YAML (+ idea.yaml structure) | never a metric |
| idea | `idea` | slug registry + ask (and run-if-trade) + dual reports | screen, never `kept` |
| ask | `ask` | `runs/<id>/` kind=question | never auto-promotes |
| run | `run` | `runs/<id>/` kind=strategy, discovery only | never auto-validates |
| validate | `validate` | holdout run, once | required for kept |
| walkforward | `walkforward` | fold runs | required for tune |
| tune | `tune` | new spec ids + runs | only if WF eligible |
| compare | `compare` | family table | lists failures; no "best" with one run |
| report | `report` | Markdown **and** HTML from a folder | artifacts only; HTML graphs folder data |
| kept | (status) | — | then indicator, not in v1 |

### Floors (CLI must enforce)

4h bars assumed for these numbers. Other timeframes: same calendar length.

| gate | rule | gold 4h today | SPY/QQQ 4h today | BTC/SOL 4h today |
| --- | --- | --- | --- | --- |
| `ask` | `n_bars >= 100` | yes (~1396, 2025-12-11→2026-07-31) | yes (~4 months from 2026-04) | yes (2022+) |
| `run` | costs written, rival asks done if definitions were unstated, `n_bars >= 200` | allowed, **thin** | allowed, **thin** | allowed |
| `thin` | `n_bars < 4000` or ask `n` that cannot clear `kill.min_trades` | yes | yes | no |
| `validate` | holdout unused, `holdout_n_bars >= 500` (~3 months of 4h) | **refuse** (cannot lock that tail without emptying discovery) | **refuse** | yes |
| `walkforward` | `n_bars >= 4000` and `n_folds >= 3` | **refuse** | **refuse** | yes |
| `tune` | `walkforward_eligible` and `search_space` nonempty | **refuse** | **refuse** | yes if space declared |
| `kept` | not thin, kill passed, one validate, family compare | **impossible today** | **impossible today** | possible |

`thin` runs may execute. They cannot reach `kept`. Reports must say `thin: true`.

Kill (for kept, not for asking): `min_trades: 30`, `max_drawdown_pct: 40`, `min_net_return: 0` unless the family YAML names other existing keys. Do not copy `min_trades: 30` onto gold as a reason to fake trades.

When Vision history grows, recompute eligibility from loaded bars. Do not hard-code "gold never validates" into the engine. Hard-code the floors.

### Default windows

Do not freeze 2022–2024 / 2025. Each spec records:

- `discovery.start/end` that fit bars that exist
- `holdout.start/end` or `null` plus why
- run `meta.json`: `actual_start`, `actual_end`, `n_bars`, `provider`, `source`

If English omits dates, use all loaded bars of that series, then apply floors. Do not invent missing years.

## 5. Data

`data.source`: `csv` | `vision` | `ccxt`

| source | job |
| --- | --- |
| `csv` | operator file or cached extract. Acceptance path. |
| `vision` | `data.binance.vision` USD-M monthly kline zips. First-class. |
| `ccxt` | optional. Live `fapi` is HTTP 451 from this desk. Must not be assumed. |

Cache: `research/.cache/binance/binanceusdm/<symbol>/<tf>.csv` (gitignored).

Fetch only the requested symbol + timeframe + range. If the venue returns a shorter history, the run records what actually loaded.

No DuckDB. No backfill farm. No yfinance. No silent fourth venue.

## 6. Specs

### Question YAML

Required: `id`, `kind: question`, `instrument`, `data`, `discovery`, `holdout` (may be null with note), `population`, `condition`, `outcome`, `definitions` (explicit; no `...`), `stats`, `forbidden`.

Optional: `idea` (slug). Set when this YAML was frozen from a named idea so runs roll up.

`ask` writes `runs/<utc>-<spec-id>-<short-hash>/` with `spec.yaml`, `meta.json` (`kind: question`, `stage: discovery|validation`, `execution_ready: false`), `metrics.json`, `table.csv`, `engine.log`, `status.json`. No `trades.csv`. No pnl keys. Print CI on rates when `n` allows.

Then `report` (also run at the end of `ask`) writes **Markdown + HTML + notebook** for that folder. HTML is the review surface (rival rates). The notebook is the live walk of `themis.ask.measure` / family helpers so the operator can see definitions and redefine the ask. Numbers quoted in chat still come from the folder, not from a cell the operator edited.

### Strategy YAML

Required: `id`, `kind: strategy`, `family`, `implements`, `requires_asks`, `instrument`, `data`, `discovery`, `holdout`, `costs`, `rules` (fill, entry, stop, target), `forbidden`, `kill`, `search_space`, `run_eligible`, `walkforward_eligible`, `tune_eligible`.

Optional: `idea` (slug), `named` (pinned English fields). `family` stays the cousin-group; `idea` is the human lineage you recall.

`implements` points at the Python that is the real strategy. `run` **loads that module** and calls `trades(spec, df, *, commission, slip)`. YAML is not executed. If YAML and Python disagree (missing `implements`, missing required keys, or a silent 0.618 default), the run is invalid. Shared fill (`themis.fill`) and `metrics.py` are not a family.

#### Family templates

`implements` is a **family engine**, not a per-idea script and not a notebook.

| English | Writes | Executes |
| --- | --- | --- |
| Same shape, new numbers (75% vs 61.8, stop 2 ATR) | New spec id, same `implements` | That module reads YAML fields. No silent default. |
| New kind (ORB, FVG, Po3, session fade) | New `strategies/<family>.py` with `trades(...)` | Runner loads it |
| Unknown kind | `needs_human` until a module exists | Do not run `retrace_swing` as a stand-in |

Contract: `trades(spec, df, *, commission=0.0, slip=0.0) -> DataFrame`. Optional `REQUIRED_SPEC_KEYS`. Loader: `themis.implements.load_implements`. v1 family: `strategies/retrace_swing.py`. `sma_cross.py` is a stub and must not run as retrace.

A later GUI (Harness) chats like a normal LLM with projects / sessions / ideas. That UI drives `compile` / `idea` / `ask` / `run` / `report`. It is not a second engine. Mapping: project = desk, session = thread, hypothesis = idea slug, freeze = spec id, measurement = run folder. After `ask`, the operator reviews **HTML + notebook**, then may redefine the ask (new spec id, same slug). The notebook calls Python; it does not reimplement ATR, fill, or metrics.

`run` loads discovery bars only, stated costs, next-open fill via `themis.fill` (not kernc `backtesting.py`). Writes `trades.csv`, `equity.csv` on the **bar** index, and the metric set in §18. Missing ratios go in **not_computed** as a map of name → reason. Always list **not modeled**: perp funding, intra-bar stop/target path. `execution_ready: false` until Amir writes real costs. Do not leave Sharpe / Sortino / Calmar in a permanent `not_computed` list if equity has two or more points — compute them.

Fill policy (OHLC): if the next open gaps through stop or target, fill at **open**, not at the level (`why: stop_gap` / `target_gap`). If the same bar prints both stop and target, tag `ambiguous_same_bar` and fill at the **stop** (pessimistic). Count both in `metrics.json`. Apply `slippage_ticks` × `tick_size` (written, or the v1 symbol default recorded in `costs_applied`) adversely on entry and exit.

## 7. CLI

```
themis login   xai|openai
themis logout  xai|openai
themis whoami
themis compile --english "..." --provider binance --symbol XAUUSDT --timeframe 4h [--backend mock|xai|openai]
themis fetch   --spec <yaml>
themis ask     --spec <yaml>
themis run     --spec <yaml>
themis validate --spec <yaml> --from-run runs/<discovery-id>
themis walkforward --spec <yaml>
themis compare --family <id>
themis tune    --spec <yaml>
themis report  --run runs/<id>
themis idea    --english "..." [--name <slug>] [--provider ...] [--symbol ...] [--timeframe ...]
themis idea    list
themis idea    show   --name <slug>
themis idea    improve --name <slug> --english "..."
themis report  --idea <slug>
```

Default `--backend` is `mock`. `xai` / `openai` require a successful `themis login` for that provider. If not logged in, `compile` exits nonzero and does not fall back to mock.

`compile` writes Job + YAML (and registers the idea if English is an idea) and stops. It does not ask or run.

`idea` is the conversation command. It compiles, names/registers the idea, runs pandas `ask` on every question in the plan, writes dual reports, and fills `idea.yaml` screens from those folders. It auto-`run`s a strategy only when the English is a return / pnl / "how good" / "backtest" request **and** costs are written **and** (`run_eligible` or `--thin`). Same law as talking through `ask` then `run`. Improving an idea is `idea improve`: new spec ids, same slug, parent recorded.

`ask` rejects strategy specs and rejects "what is the return" with no strategy spec.

`run` rejects missing costs, missing `requires_asks` folders, `run_eligible: false` unless `--thin` is passed (still cannot keep).

`validate` / `walkforward` / `tune` exit nonzero when floors fail. Message names the floor and the actual `n_bars`.

`compare` reads every discovery run in the family. Must not claim validation. Must not claim "best" on gold while `walkforward_eligible` is false.

## 8. Gold-path conversations

Default series for these four: Binance `XAUUSDT` 4h, Vision dates that exist (today: 2025-12-11 to 2026-07-31, 1396 bars). `walkforward_eligible: false`. `tune_eligible: false`. `kept` impossible. Compiler still emits strategy YAML when the English is a trade, marked not eligible.

Mock must map these four. Unknown gold English → `needs_human`.

### G1. Swing retrace 61.8–72.5

English: *4h swing high/low, enter retrace 61.8–72.5, stop swing low, target swing high.*

Idea slug (stable): `g1-retrace-618-725`. Operator may override with `call it …`.

Compiler emits ≥2 rival **asks** (fractal `n=5` vs `n=3`; swing at `i` knowable at `i+n`; zone touch after that) plus one **strategy** (`run_eligible: false`).

Tried 2026-08-28 on real Vision gold 4h (Prometheus). Path stats, not pnl:

| rival | n | target first | stop first |
| --- | ---: | ---: | ---: |
| n=5 | 116 | 28.5% | 63.8% |
| n=3 | 178 | 31.5% | 60.1% |

Stop hits first about twice as often as target. Do not promote. Frozen YAML: `compiler/example-1/`.

### G2. Asia and London, points and percent

English: *Gold points and percent in Asian and London sessions.*

This is **ask**, not a trade. No strategy YAML unless Amir asks for a session fade/breakout.

Rivals (clock windows in UTC, explicit):

- Asia `00:00–07:00` vs `00:00–08:00`
- London `07:00–16:00` vs `08:00–16:00`

Stats: session range in price points and in percent of prior-day range (or ATR). `population: session_days`. Outcome is descriptive. No pnl.

If English later says "fade London" that is a new job: extra asks, then a strategy marked not WF/tune eligible on gold.

### G3. Prior-day ATR, ±33%

English: *Prior-day ATR, lines at -33% and +33%, does price react.*

**Ask.** Rivals:

- ATR length 14 vs 20 (daily ATR, applied to the next day's 4h path)
- react = close back through the line vs 0.5×ATR reaction within N bars (N=6 and N=12)

Condition is knowable at the daily close. Lines are `prior_close ± 0.33 * prior_atr`. Outcome is a flag, not an entry. No pnl.

A later "trade the ±33%" job cites those folders for stop/target, then strategy YAML `run_eligible` from the gold floors (thin / not WF).

### G4. Best Po3, or best FVG

English: *Find the best Po3* or *find the best FVG*.

"Best" is a **family after `run`**, then `compare`. It is not an ask table and not a `tune` on gold.

Compiler must:

1. Refuse a single-winner claim on XAU.
2. Emit rival **asks** that pin definitions (Po3: which candle is the displacement, which wick is the sweep, 3-bar vs 5-bar. FVG: 3-candle imbalance, fill 50% vs full fill, continuation vs fade).
3. Emit a **family** of strategy YAMLs, each `requires_asks` set, `run_eligible` from floors, `walkforward_eligible: false`, `tune_eligible: false` on gold.
4. If Amir says optimize: CLI errors on gold with the WF floor. Point at BTC/SOL as the series that can `tune` the same family.

These four plus every row in root `questions.md` are compiler test cases. See §9. Ask stays ask. Return stays run. Family stays family.

## 9. Compiler test bank (`questions.md`)

Root `questions.md` is a **test bank**, not a cut and not a ship list of extra engines.

v1 mock must compile every row below (plus G1–G4). Default test series: Binance `XAUUSDT` 4h, Vision dates that exist. Venue is locked; the compiler does not pick a book. Naming Bybit/Bitget in English is `needs_human`.

Path law:

| path | compile writes | then | never |
| --- | --- | --- | --- |
| **ask** | ≥1 question YAML; ≥2 rivals if definitions were unstated | pandas `ask`; CI on rates | pnl, trades, "edge" |
| **run** | rival asks + one strategy YAML | freeze. `run` only if eligible (gold: `--thin`, cannot keep) | quoting return from the ask |
| **family** | rival asks + ≥2 strategy YAMLs in one family | freeze. `compare` after `run`s. gold: no "best", no `tune` | a single-winner claim on a thin series |
| **needs_human** | Job skeleton, `status: needs_human` | stop | inventing a calendar, a DXY series, or a venue |
| **after kept** | `status: error` until a spec is kept | stop | indicator/alert as a first step |

### Rows

Ids are from `questions.md`. G1–G4 are Amir's gold-path English (see §8). Tried 2026-08-28 by Prometheus on the mock: 32 rows, no network, no spend.

**Ask** (pandas on gold 4h is in-scope):

| id | English | rivals (pin in YAML, do not quiz) |
| --- | --- | --- |
| R1 | bounce after 75% retracement | impulse 12-bar 1.5 ATR vs 8-bar 1.2 ATR; bounce close-through 50% vs 1×ATR reaction |
| R2 | reaction within N bars before invalidation | N=6 vs N=12; reaction is an outcome |
| R3 | MAE/MFE after zone touch; where 1R stop sits | same impulse rivals as R1; stats are path, not pnl |
| U1 | how much does this series move on Monday | weekday window UTC vs exchange |
| U2 | today given yesterday; does Monday change that | with vs without Monday split |
| U6 | break below daily open: continue vs return | continue = close still below vs range extension |
| S1 | Monday range vs Friday range | session-day vs 24h UTC day |
| S2 | after 3 down days, chance of an up day | close-to-close vs close vs prior low |
| S5 | after a top-decile range day, next day's range | decile of 20 vs 60 sessions |
| S12 | fraction of daily range in each session | Asia/London/NY clock rivals as L1 |
| L1 | Asia and London: range, trend vs fade, where high/low form | Asia 00–07 vs 00–08; London 07–16 vs 08–16 UTC |
| L2 | share of daily range Asia vs London vs NY | same clock rivals |
| L3 | if Asia is narrow, what London does | narrow = bottom quartile vs < 0.5×ATR |
| L4 | if London breaks Asia, NY continue vs fade | break = close beyond Asia high/low vs wick |
| L5 | London open: continuation of Asia or reversal | open window 07:00 vs 08:00 |
| G2 | gold points and percent in Asian and London sessions | same clocks as L1 |
| G3 | prior-day ATR, lines at −33% and +33%, does price react | ATR 14 vs 20; react close-through vs 0.5×ATR |

**Run** (freeze strategy YAML; do not answer with a bounce rate; gold `run_eligible: false`):

| id | English | notes |
| --- | --- | --- |
| B0 | from the 75% retracement, 1:1 R, what is the return / pnl / drawdown | requires R1+R3 asks; then strategy YAML; gold thin |
| G1 | swing high/low, enter 61.8–72.5, stop swing low, target swing high | see §8; already measured, stop-first ~2× target |

**Family** (freeze a family; gold: no `tune`, no single-winner):

| id | English | notes |
| --- | --- | --- |
| B1 | best PO3 on this series | same as G4 Po3; rival displacement/sweep definitions |
| B2 | best A+ setup | rival asks must pin what A+ means (do not interview); then family |
| B3 | best opening-range breakout | ORB window rivals (first 1h vs first 2h London) |
| B4 | high prior-day-range Monday ORB vs normal Monday ORB | two cousins, `compare`; still not "best" on gold |
| B5 | buy or sell the 61–75% pullback — edge after costs | zone 61 vs 75; direction as cousins; costs required before any `run` |
| B6 | optimize the kept retracement stop and target | `tune` on gold errors the WF floor; BTC/SOL may tune this family |
| G4 | find the best Po3, or the best FVG | see §8 |

**needs_human** (v1 has no calendar and no second series):

| id | English | why |
| --- | --- | --- |
| F1 | behave on CPI days | no event calendar |
| F2 | Monday stats excluding NFP-Friday follow-through | no event calendar |
| F3 | behave on FOMC days | no event calendar |
| F4 | this series vs DXY divergence | no named DXY series |

**after kept** (v1 errors until kept):

| id | English |
| --- | --- |
| A1 | create the indicator for the winning spec |
| A2 | create the alert for the winning spec |

Mock mapping is required for every id in this table. Unknown English still returns `needs_human`. pandas runs only on **ask** rows (and on the ask half of run/family jobs). Event tables stay off git.

Conversation steps 1–5 in `questions.md` are R1 → B0 → run/family → B6 → A1/A2. Do not count them as extra rows.


## 10. Window-proof series

BTCUSDT and SOLUSDT 4h are where `run` → `validate` → `walkforward` → `tune` is proven.

A gold ask does not become a BTC strategy by renaming the symbol. A BTC-tuned spec is not gold. Copying a family across symbols is a new spec id and a new job.

SPYUSDT / QQQUSDT: same thin gates as gold. Reports must say ETF perp, not e-mini.

## 11. Tooling

Allowed: Python 3.11+, `pandas`, `numpy`, `pyyaml`, `ccxt` (optional), stdlib urllib for Vision zips, `matplotlib` (Agg) for report SVG. Optional `polars`. HTML reports embed SVG; they do not fetch a chart CDN.

**Env:** all Python deps install into `research/python/.venv` (or another tool aimed at that directory: uv, poetry). `pyproject.toml` is the list. Bootstrap: `research/python/bootstrap.sh`. Never `pip install --user`. Never `sudo pip`. Never the system / Command Line Tools interpreter. A leftover user-site package is not the desk.

The v1 `run` path is: load `implements` → family `trades()` → shared `themis.fill` → `metrics.py`. The runner does not own a retrace. It does not accrue perp funding. Same-bar SL/TP is tagged and filled at the stop; a gap through a level fills at open. Costs are placeholders until Amir writes fees. Net return is not a live claim. kernc `backtesting.py` is not canon and is not a dependency.

No skill directory this pass. No Colab required (optional twin later). No Docker trading OS.

## 12. Tree (when implemented)

```
research/
  questions/
  specs/
  ideas/               # <slug>/idea.yaml + latest.html (registry, not metrics)
  python/
    pyproject.toml   # deps; install only into .venv here
    bootstrap.sh     # creates .venv, pip install -e ".[dev]"
    README.md        # venv law
    themis/
      spec.py
      data.py          # csv | vision | ccxt
      compiler.py      # mock | xai | openai; live prompt = open-spec §20
      auth.py          # themis login xai|openai (OAuth device-code)
      runner.py        # fetch ask run validate walkforward compare tune report idea
      implements.py    # load spec.implements; YAML is not executed
      fill.py          # shared next-open / gap / same-bar stop
      ask.py
      report.py        # Markdown + self-contained HTML (inline SVG)
      metrics.py       # §18 formulas; strategy runs only
      eligibility.py   # floors
      named.py         # pin English-named trade fields
      ideas.py         # slug registry, recall, improve
    strategies/        # family templates; retrace_swing.py is v1
  notebooks/           # optional replay of a run folder; not the record
  runs/                # gitkeep only
  reports/             # <run>.md and <run>.html
docs/                  # landed research notes
```

Keep root README. User-facing name is Themis / `themis` only.

## 13. v1 order of work (Vulcan)

Not tonight's build until Caesar releases the hammer. When released, local layout then push to `fortvna/themis` once good.

1. Scaffold + schemas + reject-invalid + `eligibility.py` floors.
2. `data.py`: csv + Vision + optional ccxt; actual dates; cache.
3. `compiler.py` mock: G1–G4 + every `questions.md` id in §9. `themis.job.v1`. No network.
4. `ask` on all **ask** rows (fixture CSV acceptance + real XAU Vision). Rival folders. CI. Run/family rows freeze YAML and stop on gold.
5. `run` + one `implements` on a series that is not thin if we need a kept-path proof (BTC/SOL). Gold `run` only with `--thin`.
6. `report` + `validate` + `walkforward` (refuse gold) + `tune` stub (refuse gold, empty space errors).
7. `compare` on two cousins.
8. `metrics.py` on every strategy `run`: PnL, net return, max DD, CAGR, Sharpe, Sortino, Calmar, profit factor, expectancy, win rate, payoff (§18). Missing names get a reason, not a silent skip.
9. Dual `report`: Markdown stays the quoteable artifact; HTML embeds equity / underwater / PnL hist / rival-rate bars from that folder only.
10. Idea registry: `themis idea` names a slug, asks, screens, recalls, improves without overwriting parents. Compiler prompt in live.py is the §20 text.

Stop when: mock-compile the §9 bank → YAML first → ask-rows write folders → B0/G1/G4 freeze without pnl → F1–F4 `needs_human` → A1–A2 error → and a BTC or SOL `run` can write after-cost metrics from a folder → `report` writes `.md` and `.html` with graphics → an idea slug can be listed and improved. Indicator waits.

## 14. Cut

Indicator/alert as a first step, skill package, warehouse, live/broker, yfinance, genetic search, answering return from an ask table, freezing prompt.md dates, calling a paid SDK, spending, putting fixtures or Vision CSVs on git, putting OAuth tokens in git. `questions.md` is a compile test bank, not extra product to invent.

## 15. Acceptance

1. Root README is Themis-only.
2. `compile` maps every §9 id (questions.md + G1–G4) with no network and no spend.
3. Ask-rows write ≥2 rival question YAMLs when definitions were unstated, then pandas folders with rates, no pnl.
4. Run-rows (B0, G1) freeze strategy YAML and do not print return from the ask. Gold `run_eligible: false`.
5. Family-rows (B1–B6, G4) freeze a family, refuse a single-winner on gold, refuse `tune` on gold.
6. F1–F4 compile to `needs_human`. A1–A2 compile to `error` until kept.
7. `ask` refuses a return question with no strategy spec.
8. `run` on gold without `--thin` exits nonzero. With `--thin`, `kept` still impossible.
9. `walkforward` and `tune` on XAU/SPY/QQQ exit nonzero naming the floor.
10. `walkforward` is not refused on BTC/SOL 4h solely for being those symbols (bars decide).
11. No metric printed except from a run folder.
12. Mock compiler never networks. Live backends never run without `themis login` for that provider. Tokens never enter git.
13. SPY/QQQ reports never say ES/NQ.
14. No skill directory. No fixtures in git.
15. Strategy `run` writes Sharpe, Sortino, Calmar, CAGR, profit factor, expectancy from equity/trades, or lists each missing name with a reason. Ask folders still have no pnl keys.
16. `themis report --run` writes `research/reports/<run>.md` and `research/reports/<run>.html`. HTML contains at least one graphic built from that folder (ask: rival rates; strategy: equity curve). No CDN. Ask folders also write `research/reports/<run>.ipynb` (Themis .venv kernel, calls Python, does not reimplement the measure). `themis report --idea <slug>` writes `latest.md`, `latest.html`, and `latest.ipynb` under `research/ideas/<slug>/`.
17. `themis idea --english "I have an idea: ..."` (or equivalent) compiles, registers a slug, runs pandas ask, writes dual reports, and does not invent a metric in chat.
18. `themis idea improve --name <slug> --english "..."` writes new spec ids on that slug and refuses to overwrite parent YAML.
19. `themis idea list` / `show` recall slugs, spec ids, run folders, and the last screen from files.
20. Live `compile --backend xai` uses the §20 system prompt. Named stop `low + 1 ATR` is not rewritten to `low − ATR`.
21. `run` loads `implements` and calls `trades`. Missing module or missing required YAML keys exits nonzero. `runner.py` has no `0.618` default and no `_swing_trades`.

## 16. Authority

Caesar routes. Minerva owns this spec until a later revision. Prometheus owns compiler trials. Vulcan forges after this file exists. Amir: no external messages, no money, no account changes, no deletes without him. No spend on the SDK.

This revision (2026-08-28e) makes HTML + notebook part of the **ask** product so the operator can review and redefine definitions. 2026-08-28d remains family templates. ADR `live-compile-named-stop.md` stays baked into §3.

## 17. Ideas (name, recall, improve)

A spoken hypothesis is not a one-off YAML. It is a **named idea** you can bring back.

### Slug

- Lowercase `[a-z0-9-]`, length 2–48, no leading/trailing hyphen, no `--`.
- Operator names it when English says `call it X`, `name this X`, `call this X`, or `--name X`.
- Else the compiler proposes from pinned fields, e.g. `xau-1h-618-low-plus-1atr` (`{sym}-{tf}-{retrace}-{stop-tag}`).
- Bank rows use a stable slug: `g1-retrace-618-725`, `r1-bounce-75`, etc. Do not regenerate a new slug for the same English.
- Collision on a **new** idea: error and list the existing slug. Do not silently suffix. Improve is how you version.

### Registry

`research/ideas/<slug>/idea.yaml` is structure, like a spec. Engines may append `versions[].runs` and `versions[].screen` after folders exist. Chat may not.

```yaml
schema: themis.idea.v1
slug: h1-618
title: 1h 61.8 retrace, stop swing low + 1 ATR, TP swing high
english_origin: "find highs and lows of the 1h and wait retrace until 61.8 percent, ..."
created_utc: 2026-08-28T18:14:43Z
instrument:
  provider: binance
  symbol: XAUUSDT
  timeframe: 1h
  exchange: binanceusdm
current:
  version: 1
  spec_ids: [xau_1h_named_n5_atr14, xau_1h_named_retrace]
  job: research/jobs/20260828T181443Z-live/job.yaml
versions:
  - version: 1
    english: "..."
    parent: null
    named: {retrace_pct: 0.618, stop: "swing_low + 1*ATR", target: swing_high}
    spec_ids: [...]
    job: research/jobs/.../job.yaml
    runs: []          # filled by ask/run, not by compile
    screen: null      # dead | weak | continue | fail_kill | candidate
```

Also write `research/ideas/<slug>/latest.html` as a rollup of the current version's reports (still artifacts only).

### Commands

| command | does | never |
| --- | --- | --- |
| `themis idea --english "..."` | compile → register slug → `ask` every question in the plan → dual report → write `screen` from folders | invent metrics; auto-`run` unless English asked for return/pnl/"how good"/"backtest" |
| `themis idea list` | print slugs, titles, current screen, last version | rank "best idea" |
| `themis idea show --name <slug>` | print idea.yaml + linked spec ids + run folders | retell numbers except by quoting those folders |
| `themis idea improve --name <slug> --english "..."` | new version, new spec ids, same slug, parent = current spec ids, then same ask (and run-if-trade) path | overwrite parent YAML or parent runs |
| `themis report --idea <slug>` | md + html + notebook rollup from the idea's current runs | mix two slugs |

English that is already a §9 bank row still gets a slug (the stable bank slug). Unknown English with named trade fields (stop/target/retrace) is an idea, not `needs_human`. Unknown English with **no** named trade fields and no bank match stays `needs_human`.

### Screen (not kept)

Filled only from folders. Printed in HTML and MD as a label, not a live claim.

**Ask screen** (path stats, after rival asks):

| label | when (from `metrics.json`) | next |
| --- | --- | --- |
| `dead` | `n >= 30` and stop-first rate CI does not overlap target-first, and stop-first is higher | do not `run`. Improving the idea is allowed (new version). |
| `weak` | CIs overlap, or `n < 30` | freeze strategy YAML if English is a trade; `run` only if asked, report `thin` / small-n |
| `continue` | `n >= 30` and target-first CI does not overlap stop-first, target-first higher | eligible to `run` when English is a trade and costs exist |

G1 on gold 4h (stop-first ~2× target) is `dead` on path stats. That is the point of pandas-before-backtest.

**Run screen** (after-cost, strategy folder only):

| label | when | next |
| --- | --- | --- |
| `fail_kill` | any kill key fails (`min_trades`, `max_drawdown_pct`, `min_net_return`) | not a candidate. Improve is allowed. |
| `weak` | kill passes but `thin: true` or `short_window: true` | iterate only. Cannot `kept`. |
| `candidate` | kill passes, not thin, not short window | may `validate` once. Still not kept until that validate. |

A Sharpe of 2 on a thin gold window does not override `dead` or `fail_kill`. Screens are not `kept`. `kept` stays law 12.

### Improve

`improve` copies `job.named` from the parent, then overlays **new** named fields from the new English. Unnamed keys still get rivals (new spec ids). Example: "bring back h1-618, stop 2 ATR" pins `stop: swing_low + 2*ATR`, keeps retrace 0.618 and target swing high, rivals fractal n again. Parent YAML stays on disk.

## 18. Metrics canon

Ask answers **behavior**. Run answers **after-cost trade results**. Do not mix the keys.

### Ask keys (pandas)

Required when the measure produces them: `n`, rates (`target_rate` / `stop_rate` / `neither_rate` or `bounce` etc.), `ci95` on each rate when `n` allows, definition tags (`fractal_n`, `atr_n`, …), identity.

Forbidden: every pnl key (`pnl`, `net_return`, `expectancy`, `equity`, `sharpe`, `sortino`, `calmar`, `cagr`, `profit_factor`, trades).

MAE/MFE, bars-to-bounce, bars-to-fail are path stats, still ask.

### Strategy keys (engine)

Equity model for v1: **1 unit notional**. Starting equity `E0` = first close of the loaded discovery (or validation) window. Each trade's `pnl` is added to a running equity series at the **exit bar**. Intrabar mark-to-market is **not modeled** (same as the fill). Reports must say `notional: 1_unit` and `pnl_unit: price`. Do not silently switch to a $10,000 cash account in this revision.

Bar-return series for ratios: walk the equity curve on the **loaded bar index**. On bars with no exit, `E_i = E_{i-1}`. Simple return `r_i = E_i / E_{i-1} - 1` when `E_{i-1} > 0`. Do not compute Sharpe from the trade-pnl vector alone (that is not comparable across timeframes).

Crypto year: **365** days. `periods_per_year`:

| timeframe | periods_per_year |
| --- | ---: |
| 1h | 8760 |
| 4h | 2190 |
| 1d | 365 |
| other | `365 * 24 / hours_per_bar` |

Write `periods_per_year` into `metrics.json`. Risk-free `rf = 0` unless the spec names another (perps already omit funding). MAR for Sortino = `0` unless named.

`window_years = calendar_seconds / (365.25 * 86400)`. If `window_years < 1`, set `short_window: true`. Ratios still write; HTML captions them as short-window.

#### Must write (or `not_computed` + reason)

| key | formula | reason if missing |
| --- | --- | --- |
| `n_trades` | len(trades) | — |
| `pnl` | sum of after-cost trade pnl | — |
| `net_return` | `(E_end - E0) / E0` | `E0 <= 0` |
| `max_drawdown_pct` | max peak-to-trough of equity, percent, peak from running max | empty equity |
| `cagr` | `(E_end / E0) ** (1 / window_years) - 1` | `window_years < 1/365` or `E0 <= 0` or `E_end <= 0` |
| `calmar` | `cagr / (max_drawdown_pct / 100)` | dd is 0 (write reason `max_drawdown_pct=0`); negative CAGR is a valid Calmar, write it |
| `sharpe` | `((mean(r) - rf_period) / sample_std(r, ddof=1)) * sqrt(periods_per_year)` | `n_returns < 2` or `std=0` |
| `sortino` | `((mean(r) - mar) / downside_dev) * sqrt(periods_per_year)` where `downside_dev = sqrt(mean(min(r_i - mar, 0)^2))` over **all** bars (upside contributes 0) | `n_returns < 2` or `downside_dev=0` |
| `profit_factor` | `sum(winning pnl) / abs(sum(losing pnl))` | no losing trades (`reason: no_losses`) or no trades |
| `expectancy` | `mean(trade pnl)` after costs | no trades |
| `win_rate` | `n_win / n_trades` | no trades |
| `payoff_ratio` | `mean(win pnl) / abs(mean(loss pnl))` | no wins or no losses |
| `kill_pass` | bool, plus `kill_failed: [keys]` | — |

`rf_period` = `rf / periods_per_year` (0 when rf is 0). Use **simple** returns, not log, for this Sharpe (portfolio convention). Sample stdev `ddof=1`. Calmar is **full-sample** (not a 36-month CTA Calmar); write `calmar_window: full_sample`.

Never invent a ratio. Never annualize by 252 on a 24/7 perp.

#### Optional (write if computed, do not block the run)

`sqn` (Van Tharp: `sqrt(n_trades) * mean(trade_pnl) / std(trade_pnl)`; interpret only if `n_trades >= 30`), `omega` (threshold 0 on bar returns: sum of gains / abs(sum of losses)), `recovery_factor` (`pnl / abs(max_dd in price)`), `ulcer_index`. Missing optional keys are omitted, not listed as a failure.

### What each ratio is for (Themis must know this)

One number is a liar. The engine writes the set. The report shows the set. `compare` still ranks kill-survivors by **after-cost `net_return`** unless the family YAML names another **existing** key.

| metric | question it answers | how it lies |
| --- | --- | --- |
| **PnL / net_return** | Did we make money on this window, after costs, at 1 unit? | Ignores path, time, and risk. A lucky streak looks the same as an edge. |
| **n_trades / win_rate** | How often, and how often green? | Win rate without payoff is not expectancy. Do not multiply by R in chat. |
| **expectancy / profit_factor / payoff** | Per-trade edge after costs | Silent if n is small. One outlier winner inflates PF. |
| **max_drawdown_pct** | Worst peak-to-trough pain on this equity | One number; says nothing about how long you sat there. |
| **CAGR** | Compounded annualised growth | Noisy on `short_window`. Sensitive to start/end. |
| **Sharpe** | Return per unit of **total** volatility, annualised | Penalises upside the same as downside. Assumes iid enough to scale by sqrt(T). Overstates if returns are autocorrelated. A Sharpe > 2 on a short crypto window is a red flag, not a trophy. |
| **Sortino** | Return per unit of **downside** deviation | Better for asymmetric trades (trend, swing). Still ignores drawdown depth/duration. Denominator is unstable if few down bars. Sortino should be ≥ Sharpe when skew is positive; if Sortino << Sharpe, check the code. |
| **Calmar** | CAGR per unit of worst drawdown | Built on **one** observation (the worst DD). Full-sample on 7 months is not a CTA 36-month Calmar. Label the window. |

Industry captions (HTML only, never a promotion gate):

| | poor | weak | acceptable | exceptional-or-overfit |
| --- | --- | --- | --- | --- |
| Sharpe (ann.) | < 0 | 0–1 | 1–2 | > 2 (verify path, n, costs) |
| Sortino (ann.) | < 0 | 0–1.5 | 1.5–3 | > 3 |
| Calmar | < 0 | 0–0.5 | 0.5–2 | > 2 |
| Profit factor | < 1 | 1–1.5 | 1.5–2.5 | > 2.5 (check one-trade dominance) |

Kill stays the only hard gate for `candidate`: `min_trades: 30`, `max_drawdown_pct: 40`, `min_net_return: 0` unless the family names other existing keys. Do not add `min_sharpe: 1` as a kill in v1 — Sharpe is descriptive, and gold windows are short.

`compare` prints only keys that exist in every cousin row. It does not invent a Calmar for a folder that listed it `not_computed`.

### Not modeled (always list on strategy reports)

- perp funding
- intra-bar stop/target path (OHLC cannot order high vs low). Same-bar both-hit is tagged `ambiguous_same_bar` and filled at the **stop**. Gap through a level fills at **open**.
- real fees until Amir writes them (`execution_ready: false`)

## 19. Ask review (Markdown + HTML + notebook)

`themis report --run runs/<id>` writes:

- `research/reports/<run>.md` — quoteable artifact. Spec id, family, idea slug if any, hypothesis, exact series, actual dates, `n_bars`, `thin`, `short_window`, metrics that exist, kill status, screen, family rank, link to folder, **not_computed** with reasons, **not_modeled**. No "take this live." SPY/QQQ never say ES/NQ.
- `research/reports/<run>.html` — same facts, **plus graphics**. Self-contained. Inline CSS + inline SVG. No chart CDN. No network to view. File must still make sense if images fail: tables of the JSON remain.
- `research/reports/<run>.ipynb` (ask/question folders) — live representation of Python. Kernel: Themis (.venv). Cells `import themis` and call `measure` / `atr_complete_rivals` / the family module. No second ATR. Used to **review and redefine the ask** (change `definitions` / `condition` on a **new** spec id, same idea slug). Not where chat quotes numbers.

Redefine loop: English → freeze YAML → `ask` → HTML + notebook → operator changes an unnamed key → new spec id → `ask` again. Do not edit a metric in a cell and treat it as a run.

HTML **must** graph folder data. Minimum:

| kind | required figures | source |
| --- | --- | --- |
| question / ask | grouped bars: rival or single-spec rates (target vs stop vs neither, or bounce vs fail) with CI error bars when present | `metrics.json` (+ sibling rival folders if `report --idea` or compare) |
| strategy | (1) equity curve vs bar time (2) underwater / drawdown % (3) trade PnL histogram | `trades.csv` + reconstructed equity; timestamps from the trades |
| compare | bar chart of `net_return` (and any other shared key) per cousin | `table.csv` |
| walkforward | fold PnL / n_trades bars | `table.csv` |

Banners on every HTML: `thin`, `short_window`, `execution_ready: false`, `kept: false` unless true, `notional: 1_unit`. Idea slug and version in the header when known.

`themis report --idea <slug>` writes `research/ideas/<slug>/latest.md`, `latest.html`, and `latest.ipynb`: current-version asks stacked, rival-rate chart, notebook walk of the Python. Improve the idea from that review; never overwrite a parent YAML.

Markdown remains the record you can grep. HTML is the desk view. The notebook is how you inspect and redefine the ask. Chat still cites JSON/CSV.

## 20. Compiler prompt (Themis)

This is the live system prompt. `themis/live.py` (`LIVE_SYSTEM`) **must** be this text (or a strict superset that does not weaken a rule). Mock does not call a model; it still obeys every rule. Do not replace this with a "helpful trading copilot" that invents a 70% or a stop that "fits."

```
You are Themis, a research compiler — not a tipster, not a broker, not an optimizer.

Output ONLY themis.job.v1 YAML or JSON. No markdown fences required. No commentary. No metrics.

ROLE
- English in. Structure out. pandas ask and the pandas bar-loop run engine will measure later.
- You freeze a hypothesis so it can be named, asked, run, recalled, and improved.
- You do not pick a venue or a series. The series is passed in.
- You do not invent n, rates, pnl, bounce_rate, return, drawdown, expectancy, Sharpe, Sortino, Calmar, CAGR, profit factor, or "this looks profitable."

LAW
- schema: themis.job.v1
- source.compiler is xai (or openai). source.english is the operator text verbatim.
- Freeze YAML before any metric. You never write metrics.json.
- Vague English → at least two rival question specs with explicit definitions, then a strategy spec if the English is a trade.
- Rivals only for UNNAMED keys (fractal n, ATR length if unstated, clock windows, impulse definitions). New spec ids. Cousins COPY named fields.
- Named fields in the English (side, entry, stop, target, retrace_pct, timeframe, symbol) are pinned. Do not rewrite them.
- "low + 1 ATR" as stop is not "low − ATR". Sign is part of the name. A geometrically tight stop is the hypothesis; measure it; do not "fix" it.
- Swing at bar i with fractal n is knowable at i+n. Fill next_open. No lookahead. No forming-bar signals. A bounce / 1R touch / fill is an OUTCOME, never rules.entry.
- Question measure for retrace-style English: swing_retrace. Outcome: target_first vs stop_first (path stats, not pnl).
- Strategy: costs placeholder with a written reason (commission_per_side 0.0004 is a placeholder, not a live claim). Zero only as 0 plus a reason.
- run_eligible, walkforward_eligible, tune_eligible default false (floors come from loaded bars, not from you).
- execution_ready is false. Do not claim kept. Do not claim best. Do not claim live.
- "Best Po3 / best FVG / optimize" is a FAMILY of strategy YAMLs, not one winner and not a tune on a thin series.

IDEAS
- Every trade hypothesis gets idea.slug.
- If the English says "call it X" / "name this X", X is the slug (lowercase hyphen).
- Else propose {sym}-{tf}-{retrace}-{stop-tag}, e.g. xau-1h-618-low-plus-1atr.
- If the English says "bring back X" / "improve X", set idea.slug = X and idea.parent_spec_ids if you know them; still emit NEW spec ids.
- Include idea.title, idea.version (1 if new).

IDENTITY
- data.source: vision. provider binance. exchange binanceusdm unless the series says otherwise.
- Identity notes: XAUUSDT is this venue's gold perp, not COMEX. SPYUSDT/QQQUSDT are ETF perps, never ES/NQ.
- Naming Bybit/Bitget → status: needs_human, empty plan.
- CPI / NFP / FOMC / DXY without a calendar or a named second series → status: needs_human.
- Indicator / alert before kept → status: error.

SHAPE
- Include questions[] and strategies[] as full spec mappings plus plan[].
- Spec ids: lowercase, include symbol and timeframe tags, unique per rival.
- implements: strategies/retrace_swing.py for retrace-swing English. Same shape, new numbers → same module, put the numbers on the YAML (pct_low/pct_high or retrace_pct, fractal_n). New kind (ORB, FVG, Po3, session) → a different strategies/<family>.py that already exists, or needs_human. Never point FVG/Po3 at retrace_swing. Never invent 0.618 when they named 75%. Never emit a new .py per chat line.
- Fields when relevant: fractal_n, pct_low, pct_high, atr_n, stop_atr_mult.
- Question required: id, kind: question, instrument, data, discovery, holdout, population, condition, outcome, definitions (explicit, no "..."), stats, forbidden.
- Strategy required: id, kind: strategy, family, implements, requires_asks, instrument, data, discovery, holdout, costs, rules (fill, entry, stop, target), forbidden, kill, search_space, run_eligible, walkforward_eligible, tune_eligible.
- discovery/holdout: do not invent years. If dates were omitted, start/end null plus a note to use all loaded bars.
- forbidden always includes forming_bar_signals. Questions also forbid quoting_pnl_from_this_ask.

TRADING EXPERTISE YOU MUST APPLY (structure, not numbers)
- Path first, trade second. If they said "I have an idea" without asking return, emit rival asks; emit strategy YAML only if the English already is a trade (entry+stop+target, or "backtest", or "what's the pnl").
- Stops belong beyond typical adverse path (MAE is an ASK, not a guess). If they named the stop, you still ASK rivals for the unnamed swing definition.
- 1R from a zone is a strategy, not hit-rate × R.
- Sessions are clock windows in UTC, always rivalled if unstated (Asia 00–07 vs 00–08, London 07–16 vs 08–16).
- Fractal rivals default 5 vs 3 (or 5 vs 2 on 1h if 2 was already in play). ATR rivals 14 vs 20 when length is unstated.
- Do not quiz the operator. Pin what they named; rival what they did not; status needs_human only when pandas cannot know (venue, calendar, second series).

OUTPUT
- Emit themis.job.v1 now. No metrics. No fences. No apology.
```

End of prompt. Vulcan copies this into `LIVE_SYSTEM`. Tests must fail if live.py's prompt drops: named-stop sign, no-metrics, rivals-only-unnamed, idea.slug, or next_open / knowable-at-i+n.
