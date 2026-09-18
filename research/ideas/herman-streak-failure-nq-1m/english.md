# English — Streak Failure Reversal [Herman] control (author defaults)

Measure, do not optimize. Status: research control before any improve-backlog knob.

Instrument: **NQ** (CME Nasdaq futures), **1-minute** standard candles, America/New_York clocks.
Series class: **yahoo / Databento / uploaded Orb tape pack** — **not** Binance. Do **not** substitute QQQUSDT or call it NQ.

Question: Under author-faithful defaults, what are trade count n, win rate, profit factor, and expectancy **after real round-trip costs**, on a **long out-of-sample** window that **excludes** the author marketing slice (approx 2026-08-23 → 2026-09-11)?

Frozen defaults:
- Signal TF = chart 1m; streak = 5 consecutive bullish/bearish **bodies** (close vs open)
- After a completed bullish streak, arm SHORT; bearish streak arms LONG
- Confirm: within the next 15 signal bars, a bar **closes** beyond the terminal streak extreme (SHORT below terminal low; LONG above terminal high). Wicks alone do not confirm.
- Entry: market next 1m open after confirm
- SL: terminal streak candle extreme; TP: 1.0R from fill to SL
- Session: 09:45–12:00 ET for setup completion and confirm; hard flat 16:00 ET
- One position; no pyramid
- Costs: model CME-style commission + 1 tick slip each way (record schedule in YAML); execution_ready: false

Honesty:
- Author claim n=41 WR 75.6% PF~3.5 on short NQ window is **marketing** — distrust; author says longer windows degrade.
- needs_human: Themis binanceusdm fetch cannot supply NQ 1m. Control measure runs when NQ 1m tape is available (Orb fortvna.tape.v0 pack or future yahoo/databento bridge). Until then do not invent metrics.

Improve backlog (try later, walk-forward / embargo — never tune on Aug–Sep screenshot window): min streak range ≥ k×ATR; TP 1.5–2R; session sub-buckets / first-N arms/day; confirm body quality; optional sweep-map / IB / PDH-PDL confluence.
