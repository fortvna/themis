# Question bank

Example English for Themis. An agent turns a line into YAML (structure only), fetches the OHLC you named, and measures. This file is **not** a ship list.

How to read the last column:

- **ask** — behavior. pandas. A rate like “70% bounced” is not edge.
- **run** — you are asking for return, pnl, or a trade. Needs a strategy YAML + Python.
- **family** — “best” / optimize / several stops or targets. Several `run`s, then `compare`.
- **clarify** — pin **provider** (binance / bybit / bitget) if you omitted it, plus symbol/timeframe if still unnamed. Impulse, bounce, stop, and invalidation are pinned by **pandas asks**, not by interviewing you.
- **after kept** — indicator or alert. Not a first step.

**Providers: Binance, Bybit, Bitget.** Name the venue when you ask; optionally the symbol. “Gold on Binance” / “gold on Bybit” / “gold on Bitget” means that venue’s `XAUUSDT` perp — three different series. The YAML must still name provider + symbol + timeframe. Fetch that OHLC with ccxt (or a CSV). This is not spot FX and not a cash index.

---

## The conversation Themis is for

| Step | You say | Path |
|---|---|---|
| 1 | How many times has price bounced after a 75% retracement in gold, 4 hour, on Binance? | Named venue’s `XAUUSDT` 4h, then **ask** (and extra asks for rival bounce / impulse definitions) |
| 2 | If from that retracement I target 1:1 R, what is the return? | more **ask**s (MAE/MFE, where it dies) to choose a stop, then **run** — not 70% × 1R in chat |
| 3 | Create the strategy and backtest | **run** (or family if several versions) |
| 4 | Optimize | **family** — declared search space, new spec ids |
| 5 | Create the indicator / alert | **after kept** only |

---

## Behavior

| # | Ask this | Path |
|---|---|---|
| R1 | How many times has price bounced after a 75% retracement on this series, this timeframe? | ask — agent tries explicit rival definitions in pandas |
| R2 | After that zone is touched, how often do we get a reaction within N bars before invalidation? | ask — reaction is an outcome, not an entry |
| R3 | After the zone is touched, what is the MAE / MFE distribution? Where does a 1R stop usually sit? | ask — this is how the agent proposes `rules.stop` |
| U1 | How much does this series move on Monday? | ask |
| U2 | How does today behave given yesterday? Does Monday change that? | ask |
| U6 | After a break below the daily open, what % continues vs returns? | ask |
| S1 | Is Monday’s range different from Friday’s? | ask |
| S2 | After 3 down days, chance of an up day? | ask |
| S5 | After a top-decile range day, what is the next day’s range? | ask |
| S12 | What fraction of the daily range happens in each session? | ask |

---

## Sessions — Asia and London

| # | Ask this | Path |
|---|---|---|
| L1 | How do Asia and London behave on this series (range, trend vs fade, where high/low form)? | ask — define clock windows in YAML |
| L2 | What share of the daily range is Asia vs London vs NY? | ask |
| L3 | If Asia is narrow, what does London usually do? | ask |
| L4 | If London breaks Asia, how often does NY continue vs fade? | ask |
| L5 | Is the London open usually a continuation of Asia or a reversal? | ask |

---

## Return and “best” (must `run`)

| # | Ask this | Path |
|---|---|---|
| B0 | From the 75% retracement, 1:1 R — what is the return / pnl / drawdown? | run |
| B1 | What is the best PO3 scenario on this series? | clarify, family |
| B2 | What is the best A+ setup on this series? | clarify what A+ means, family |
| B3 | What is the best opening-range breakout on this series? | family |
| B4 | Does a high prior-day-range Monday ORB beat a normal Monday ORB? | family |
| B5 | Buy or sell the 61–75% pullback — is there edge after costs? | clarify, family |
| B6 | Optimize the kept retracement stop and target | family |

Do not answer B0–B6 with a bounce rate.

---

## Context (needs a calendar or a second named series)

| # | Ask this | Path |
|---|---|---|
| F1 | How does this series behave on CPI days? | ask — or refuse if no calendar |
| F2 | Monday stats excluding NFP-Friday follow-through | ask |
| F3 | How does this series behave on FOMC days? | ask |
| F4 | This series vs DXY divergence — what happens next? | ask — named DXY series |

---

## After a spec is kept

| # | Ask this | Path |
|---|---|---|
| A1 | Create the indicator for the winning spec | after kept |
| A2 | Create the alert for the winning spec | after kept |

---

## How to use this file

1. Say the English (or pick a row).
2. Name provider (binance / bybit / bitget). Pin symbol, timeframe, dates. Fetch that OHLC via ccxt. Never mix venues.
3. **ask** first — including extra asks that choose definitions, stop, and bounce. Quote only run folders.
4. **run** when you want return / pnl. The strategy YAML should cite the ask folders that chose its rules.
5. Optimize only inside a written search space.
6. Indicator / alert only after holdout validation.
