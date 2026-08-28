# Themis open spec

Minerva. 2026-08-28. This is the spec. Not a build.

Supersedes `prompt.md` for implementation. Research notes sit beside this file; they are not the spec.
Vulcan forges from this document. Fixtures, event tables, and Vision CSVs stay off git.

## 1. Product

**Themis** is a research loop you can talk to. English in. YAML frozen. Then pandas or `backtesting.py` writes a run folder. Chat does not invent numbers.

Go-live is that conversation working on files. Not an order. Not a broker. Not a warehouse.

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

The compiler may write YAML only. It may not write `metrics.json`.

## 4. Gated ladder

The loop is coherent. The ladder on every symbol is not. Eligibility is computed from **actual loaded bars**, not from prompt.md dates.

### Stages

| stage | command | writes | promotion |
| --- | --- | --- | --- |
| compile | `compile` | Job + YAML | never a metric |
| ask | `ask` | `runs/<id>/` kind=question | never auto-promotes |
| run | `run` | `runs/<id>/` kind=strategy, discovery only | never auto-validates |
| validate | `validate` | holdout run, once | required for kept |
| walkforward | `walkforward` | fold runs | required for tune |
| tune | `tune` | new spec ids + runs | only if WF eligible |
| compare | `compare` | family table | lists failures; no "best" with one run |
| report | `report` | markdown from a folder | artifacts only |
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

`ask` writes `runs/<utc>-<spec-id>-<short-hash>/` with `spec.yaml`, `meta.json` (`kind: question`, `stage: discovery|validation`, `execution_ready: false`), `metrics.json`, `table.csv`, `engine.log`, `status.json`. No `trades.csv`. No pnl keys. Print CI on rates when `n` allows.

### Strategy YAML

Required: `id`, `kind: strategy`, `family`, `implements`, `requires_asks`, `instrument`, `data`, `discovery`, `holdout`, `costs`, `rules` (fill, entry, stop, target), `forbidden`, `kill`, `search_space`, `run_eligible`, `walkforward_eligible`, `tune_eligible`.

`implements` points at the Python that is the real strategy. If YAML and Python disagree, the run is invalid.

`run` loads discovery bars only, stated costs, next-open fill. Writes trades, `net_return`, `pnl`, `max_drawdown_pct`, trade count, and any ratio the engine actually computed. Missing ratios go in **not computed**. Always list **not modeled**: perp funding, intra-bar stop/target path. `execution_ready: false` until Amir writes real costs.

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
```

Default `--backend` is `mock`. `xai` / `openai` require a successful `themis login` for that provider. If not logged in, `compile` exits nonzero and does not fall back to mock.

`compile` writes Job + YAML and stops. It does not ask or run.

`ask` rejects strategy specs and rejects "what is the return" with no strategy spec.

`run` rejects missing costs, missing `requires_asks` folders, `run_eligible: false` unless `--thin` is passed (still cannot keep).

`validate` / `walkforward` / `tune` exit nonzero when floors fail. Message names the floor and the actual `n_bars`.

`compare` reads every discovery run in the family. Must not claim validation. Must not claim "best" on gold while `walkforward_eligible` is false.

## 8. Gold-path conversations

Default series for these four: Binance `XAUUSDT` 4h, Vision dates that exist (today: 2025-12-11 to 2026-07-31, 1396 bars). `walkforward_eligible: false`. `tune_eligible: false`. `kept` impossible. Compiler still emits strategy YAML when the English is a trade, marked not eligible.

Mock must map these four. Unknown gold English → `needs_human`.

### G1. Swing retrace 61.8–72.5

English: *4h swing high/low, enter retrace 61.8–72.5, stop swing low, target swing high.*

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

Allowed: Python 3.11+, `pandas`, `numpy`, `pyyaml`, `ccxt` (optional), `backtesting.py`, stdlib urllib for Vision zips. Optional `polars`.

`backtesting.py` is the v1 `run` engine. It does not accrue perp funding. 4h SL/TP from OHLC is optimistic. Costs are placeholders until Amir writes fees. Net return is not a live claim.

No skill directory this pass. No Colab required (optional twin later). No Docker trading OS.

## 12. Tree (when implemented)

```
research/
  questions/
  specs/
  python/
    pyproject.toml
    themis/
      spec.py
      data.py          # csv | vision | ccxt
      compiler.py      # mock | xai | openai
      auth.py          # themis login xai|openai (OAuth device-code)
      runner.py        # fetch ask run validate walkforward compare tune report
      ask.py
      report.py
      eligibility.py   # floors
    strategies/
  notebooks/           # optional
  runs/                # gitkeep only
  reports/
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

Stop when: mock-compile the §9 bank → YAML first → ask-rows write folders → B0/G1/G4 freeze without pnl → F1–F4 `needs_human` → A1–A2 error → and a BTC or SOL `run` can write after-cost metrics from a folder. Indicator waits.

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

## 16. Authority

Caesar routes. Minerva owns this spec until a later revision. Prometheus owns compiler trials. Vulcan forges after this file exists. Amir: no external messages, no money, no account changes, no deletes without him. No spend on the SDK.
