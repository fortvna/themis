# SPEC.md — Themis v0

Minerva. 2026-09-01. Canon for WR-themis. Folded GitHub `docs/open-spec.md` 2026-08-28d §§17–20 plus named-stop ADR.

Sources opened: `docs/open-spec.md`, `ADR/live-compile-named-stop.md`, `questions.md`, `WARROOM.md`, `README.md`, `research/python/pyproject.toml`, `research/python/themis/report.py`, `metrics.py`, `live.py`, `/workspace/fortuna/COMPANY.md`, `PEOPLE.md`, `decisions.md`.
Claims: VERIFIED | ASSUMED | UNKNOWN.

Detail law stays in `docs/open-spec.md` (formulas, prompt text, bank rows). This file is what Caesar accepts and Vulcan implements. Do not invent behavior missing a MUST here.

Opened 2026-08-28. Revision **2026-08-28e** (ask review): `ask` / `report` write Markdown + HTML + a Python notebook. The notebook represents `themis.ask`; use it to redefine the ask (new spec id). See open-spec §19.

Revision **2026-08-28d** (family templates): `run` loads `implements`; same shape / new numbers stay on YAML; new kind needs a new family module. See open-spec §6.

## 1. Context and problem

Themis is a **local research harness**. Operator speaks English (an idea). Themis names the idea, freezes YAML, runs pandas to screen the path, and writes **Markdown + HTML** from the run folder. Chat does not invent numbers. Go-live is that loop on files, not an order. VERIFIED `docs/open-spec.md` §1, §17–19.

Problem already hit: live xAI rewrote `low + 1 ATR` to `low − ATR`. Named fields must pin. VERIFIED ADR.

## 2. Users and jobs

| user | job | source |
| --- | --- | --- |
| Arafat | Owner. Approves spend, remotes, deletes. | VERIFIED `COMPANY.md` |
| Operator | Speak an idea, get a named slug, folder-backed MD+HTML. Bring it back to improve. | VERIFIED §17; imported docs still say “Amir” — ASSUMED same human as Arafat |
| War Room | Spec / spike / build / review | VERIFIED `PEOPLE.md` |

JTBD: (1) name the idea (2) YAML freeze (3) pandas screen (4) dual report with charts (5) recall / improve without overwriting the parent (6) `run` only when English is a trade and screen is not `dead`.

## 3. As-is / to-be

**As-is (VERIFIED GitHub WIP `6310abd`):** CLI under `research/python/`. Mock + live compile, named-stop gate, `metrics.py`, `report.py` MD+HTML with hand-built SVG (ask bars). Short `LIVE_SYSTEM`. pandas bar-loop `run`, not backtesting.py.

**To-be (this v0):** operator loop is `themis idea`. Dual MD+HTML with required charts. Metrics canon §18 keys. `LIVE_SYSTEM` is the full §20 prompt. Screens are not `kept`.

## 4. Constraints

- Venue v1: Binance USD-M `binanceusdm`. Series `XAUUSDT` (not COMEX), `BTCUSDT`, `SOLUSDT`, `SPYUSDT` (not ES), `QQQUSDT` (not NQ). VERIFIED §1.
- Data: `csv` \| `vision` \| optional `ccxt`. VERIFIED §5.
- No warehouse, live broker, fourth venue, tokens in git, spend until Arafat leaves mock. VERIFIED §2.14.
- Stack (Prometheus ADOPT, `ADR/stack-v1.md`): Python ≥3.11, pandas, numpy, pyyaml, pandas bar-loop `run`, inline SVG HTML. matplotlib Agg TRIAL / not runtime. ccxt optional. Package path `research/python/`.
- Edge: geo-blocked `fapi`, Vision zips, headless OAuth, offline from cache/CSV, no chart CDN (HTML must view offline). VERIFIED §5, §19.
- Disk: this repo only. VERIFIED `WARROOM.md`.

## 5. Success metrics

- Idea English → slug + YAML + pandas ask folders + MD and HTML. VERIFIED §17.
- HTML graphs folder data; tables remain if images fail. VERIFIED §19.
- Strategy folder writes PnL, net return, max DD, CAGR, Sharpe, Sortino, Calmar (or `not_computed` + reason). Ask has no pnl keys. VERIFIED §18.
- Named stop cannot compile as the opposite sign. VERIFIED ADR.
- One ratio is not `kept`. Screen ≠ kept. VERIFIED §17, law 12.

## 6. Requirements

### Loop and law

| ID | pri | requirement | source |
| --- | --- | --- | --- |
| F-01 | MUST | English → YAML freeze → engine writes run folder. Compiler never writes `metrics.json`. | §2.3 |
| F-02 | MUST | YAML is structure. pandas or `implements` Python runs. | §2.2 |
| F-03 | MUST | `ask` never writes pnl keys (including Sharpe/Sortino/Calmar). `run` refuses a question spec. | §2.7, §18 |
| F-04 | MUST | Quote metrics only from `metrics.json` / `table.csv`. | §2.5 |
| F-05 | MUST | Vague English → ≥2 rival asks on **unnamed** fields only. Cousins copy named fields. | §2.6, ADR |
| F-06 | MUST | No costs → no strategy `run`. Zero only as `0` plus a reason. | §2.8 |
| F-07 | MUST | No lookahead. Next-open fill. Swing at `i` with fractal `n` knowable at `i+n`. | §2.9 |
| F-08 | MUST | Discovery cannot read holdout. `validate` ≠ `walkforward`. | §2.10 |
| F-09 | MUST | `tune` needs nonempty `search_space` and WF eligible. New spec ids. | §2.11 |
| F-10 | MUST | Compiler does not pick venue/series. Bybit/Bitget → `needs_human`. | §2.15 |
| F-11 | MUST | CLI includes compile/fetch/ask/run/validate/walkforward/compare/tune/report/login/logout/whoami **and** `idea` commands in F-50. Default `--backend mock`. | §7, §17 |
| F-12 | MUST | `questions.md` is the compile test bank. | §9 |

### Named stop

| ID | pri | requirement | source |
| --- | --- | --- | --- |
| F-20 | MUST | Parse English into `job.named` (`side`, `entry`, `stop`, `target`, `retrace_pct`, `timeframe`, `symbol` when present). | ADR 1 |
| F-21 | MUST | Overlay `job.named` after the model returns, before write. | ADR 2 |
| F-22 | MUST NOT | Rewrite a named stop/target. Sign is part of the name. | ADR 3 |
| F-23 | MUST | Rivals only for unnamed keys; new spec ids. | ADR 4 |
| F-24 | MUST | Compile exits nonzero if named field disagrees. No mock fallback. | ADR 5 |
| F-25 | MUST | Same pin+refuse on mock, xai, openai. | ADR 6 |
| F-26 | MUST NOT | Mix folders or tune a named-stop failure into a different stop. | ADR 7 |
| F-27 | MUST NOT | “Fix” a geometrically tight named stop. | ADR 8 |

### Ideas (Arafat: name, recall, improve)

| ID | pri | requirement | source |
| --- | --- | --- | --- |
| F-50 | MUST | `themis idea --english "..."`: compile → register slug → `ask` every question in the plan → dual report → write `screen` from folders. Auto-`run` only if English asked return/pnl/"how good"/"backtest". | §17 |
| F-51 | MUST | Slug: `[a-z0-9-]{2,48}`. Operator `--name` / “call it X”, else `{sym}-{tf}-{retrace}-{stop-tag}`. Bank rows keep stable slugs. Collision on a **new** idea errors; do not silent-suffix. | §17 |
| F-52 | MUST | Registry `research/ideas/<slug>/idea.yaml` schema `themis.idea.v1` as in §17. Engines append `versions[].runs` and `screen`. Chat may not. | §17 |
| F-53 | MUST | `idea list`, `idea show --name`, `idea improve --name --english`, `report --idea`. Improve = new version, new spec ids, parent preserved. | §17 |
| F-54 | MUST | Ask screen labels `dead` \| `weak` \| `continue` from folder rates/CIs as §17 table. Run screen `fail_kill` \| `weak` \| `candidate`. Screens are not `kept`. | §17 |
| F-55 | MUST | Unknown English with named trade fields is an idea, not `needs_human`. No named fields and no bank match → `needs_human`. | §17 |

### Metrics canon

| ID | pri | requirement | source |
| --- | --- | --- | --- |
| F-60 | MUST | Ask keys: `n`, rates, `ci95` when n allows. Forbidden: all pnl/ratio keys. | §18 |
| F-61 | MUST | Strategy equity: 1 unit notional; `E0` = first close; pnl at exit bar; bar returns on loaded index; crypto year 365; write `periods_per_year`. Formulas **exactly** the §18 “Must write” table (n_trades, pnl, net_return, max_drawdown_pct, cagr, calmar, sharpe, sortino, profit_factor, expectancy, win_rate, payoff_ratio, kill_pass). Else `not_computed` + reason. | §18 |
| F-62 | MUST | Never annualize by 252 on a 24/7 perp. Never invent a ratio. `rf=0`, Sortino MAR=0 unless spec names otherwise. | §18 |
| F-63 | MUST | If `window_years < 1`, `short_window: true`. Ratios still write. | §18 |
| F-64 | MUST | Kill stays `min_trades: 30`, `max_drawdown_pct: 40`, `min_net_return: 0` unless family names other **existing** keys. Do not add `min_sharpe` as kill in v1. | §18, `eligibility.py` |
| F-65 | MUST | `compare` ranks kill-survivors by after-cost `net_return` unless family names another existing key. Prints only keys present in every cousin. | §18 |
| F-66 | MUST | Strategy reports always list not-modeled: perp funding, intra-bar SL/TP (same-bar both-hit fills **stop**; gap fills **open**), placeholder fees (`execution_ready: false`). | §18 |
| F-67 | SHOULD | Optional keys sqn / omega / recovery_factor / ulcer_index if computed; omit if not. | §18 |

### Dual report

| ID | pri | requirement | source |
| --- | --- | --- | --- |
| F-70 | MUST | `themis report --run` writes `research/reports/<run>.md` **and** `<run>.html`. MD is the grepable record. Chat cites JSON/CSV. | §19 |
| F-71 | MUST | HTML self-contained: inline CSS + inline SVG. No chart CDN. No network to view. If images fail, JSON tables remain. | §19, `ADR/stack-v1.md` |
| F-72 | MUST | Ask HTML: grouped bars of rates with CI error bars when present (as-is). Strategy HTML: equity curve, underwater DD %, trade PnL histogram (M1 gap). Compare: net_return bars. Walkforward: fold pnl / n_trades. Draw with inline SVG; do not add a chart library unless polyline SVG fails. | §19, `ADR/stack-v1.md` |
| F-73 | MUST | Banners: `thin`, `short_window`, `execution_ready: false`, `kept: false` unless true, `notional: 1_unit`. Idea slug + version in header when known. SPY/QQQ never say ES/NQ. No “take this live.” | §19 |
| F-74 | MUST | `report --idea <slug>` writes `research/ideas/<slug>/latest.md` and `latest.html`. | §19 |

### Compiler prompt

| ID | pri | requirement | source |
| --- | --- | --- | --- |
| F-80 | MUST | `LIVE_SYSTEM` in `research/python/themis/live.py` is the §20 prompt text (or a strict superset that does not weaken a rule). | §20 |
| F-81 | MUST | Tests fail if that prompt drops: named-stop sign, no-metrics, rivals-only-unnamed, idea.slug, next_open / knowable-at-i+n. | §20 |

### Floors (bars decide)

| ID | pri | rule | source |
| --- | --- | --- | --- |
| F-30 | MUST | ask `n_bars >= 100` | `eligibility.py` |
| F-31 | MUST | run: costs + `n_bars >= 200` | same |
| F-32 | MUST | thin if `n_bars < 4000`; thin may run, cannot kept | same |
| F-33 | MUST | validate: unused holdout `>= 500` bars | same |
| F-34 | MUST | walkforward: `n_bars >= 4000` and `n_folds >= 3` | same |
| F-35 | MUST | refuse messages name the floor and actual `n_bars` | §7 |

### Auth

| ID | pri | requirement | source |
| --- | --- | --- | --- |
| F-40 | MUST | No `THEMIS_LLM_KEY`. Tokens `~/.themis/`, gitignored. | §3, `.gitignore` |
| F-41 | MUST | Live compile refuses if not logged in. No mock fallback. No pasted key. | §3 |
| F-42 | MUST | Mock never networks. Login does not call the model. | §3 |
| F-43 | SHOULD | Real OAuth device-code when Arafat leaves mock. | `auth.py` |
| F-44 | LATER | Image/video on the same compiler. | §3 |

### NFR

| ID | pri | requirement | source |
| --- | --- | --- | --- |
| NFR-01 | MUST | Offline ask/run from spec + cache/CSV. | §2 |
| NFR-02 | MUST | No secrets in git. | `COMPANY.md` |
| NFR-03 | SHOULD | Headless device-code OAuth. | §3 |
| NFR-04 | MUST | M1 stack is `ADR/stack-v1.md`. Further stack change only via a new Prometheus ADR. | `ADR/stack-v1.md` |
| NFR-05 | SHOULD | matplotlib Agg only if a spike shows string SVG cannot draw F-72 equity/DD/hist. Not a runtime MUST. | `ADR/stack-v1.md` |

## 7. Non-goals

Live broker; warehouse; yfinance; fourth venue; indicator before kept; skill package; genetic “make it profitable”; answering return from an ask table; `min_sharpe` kill; ES/NQ labels on SPY/QQQ; fixtures/tokens in git; silent slug suffix; overwriting parent idea YAML. VERIFIED §14, §17.

## 8. Data and privacy

Cache gitignored. Auth off repo (`SECRETS.md` names only). Idea registry and reports are research artifacts, not customer dumps. VERIFIED `.gitignore`, `WARROOM.md`.

## 9. Interfaces

| interface | contract | source |
| --- | --- | --- |
| Human | English + named series. `themis idea`. | §17 |
| Job | `themis.job.v1` + `job.named` | §3, ADR |
| Idea | `themis.idea.v1` | §17 |
| Reports | MD + HTML paths in §19 | §19 |
| Live model | §20 prompt | §20 |

## 10. Milestone slices

**M0 (imported / GitHub WIP):** mock CLI, bank, floors, named-stop gate commit, partial HTML/metrics. VERIFIED tree.

**M1 (after Caesar accepts):** F-50–F-55 ideas; F-70–F-74 dual reports; F-72 strategy equity/DD/hist (ask bars already exist); F-60–F-66 metrics; F-80–F-81 full §20 prompt. Inline SVG, no matplotlib runtime.

**M2:** F-43 real OAuth when Arafat leaves mock. No spend until then.

**M3 LATER:** media compile; indicator after kept.

Vulcan does not start M1 until Caesar accepts this SPEC. Stack is already named (`ADR/stack-v1.md`).

## 11. Open questions

1. Operator name Amir vs Arafat — ASSUMED one human. Does not change MUST.
2. Stack — closed. ADOPT `ADR/stack-v1.md`. matplotlib not runtime.
3. F-72 strategy figures (equity/DD/hist) — M1 gap. Ask bars exist. VERIFIED Prometheus 2026-09-01.

## 12. Acceptance ideas

- `themis idea --english "1h gold retrace 61.8 stop low+1 ATR TP high"` writes a slug, ≥2 rival asks, `idea.yaml`, MD+HTML. No pnl on ask folders.
- Same English with YAML stop `low − ATR` → compile error (F-24).
- Strategy HTML has equity, DD, PnL hist. Ask HTML has rate bars.
- `metrics.json` has sharpe/sortino/calmar or `not_computed` reasons. Ask JSON has none of those keys.
- `idea improve --name <slug>` keeps parent files.
- `LIVE_SYSTEM` contains the named-stop sign sentence from §20.
- Bank 32 rows unchanged: F* needs_human, A* error until kept.

Caesar accepts or rejects. Stack is named. Vulcan implements M1 after accept.
