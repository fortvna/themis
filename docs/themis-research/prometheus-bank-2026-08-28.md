# Addendum: mock compiler on questions.md + G1–G4

Prometheus. 2026-08-28. YAML first, then pandas on asks. No SDK. No spend. No git fixtures.

Jobs: `compiler/bank/jobs.json`
Ask numbers: `compiler/bank/metrics.json`
Per-id YAML stubs: `compiler/bank/<id>.yaml`

Series: Binance XAUUSDT 4h Vision, 1396 bars, 2025-12-11 → 2026-07-31.

## Compile

| class | ids | mock |
| --- | --- | --- |
| ask | G1 G2 G3 R1 R2 R3 U1 U2 U6 S1 S2 S5 S12 L1–L5 | `ok`, ≥2 rivals in the job |
| run | B0 | `ok`, strategy `run_eligible: false` |
| family | G4 B1–B6 | `ok`, cousins, `tune_eligible: false` |
| refuse | F1–F4 | `needs_human` (no calendar / no DXY) |
| refuse | A1 A2 | `error` (after kept) |

Ask stays ask. Return stays run. Family stays family. No pandas pnl on B* or G4.

## Pandas (gold 4h, not edge)

- **G1** n=5: 116 events, target first 28%, stop first 64%.
- **G2 / L2 / S12** 232 days. London median range 48 pts, Asia 43, NY 37. Shares overlap because 4h clocks are coarse.
- **G3** ATR14: touch +33% 111 days, close back through 45%. Touch −33% 105 days, through 48%. Half-ATR “react” on the high side drops to 31%. Definition moves the number.
- **L3** Asia narrow (n=116): London median 20 pts. Otherwise 68. Quiet Asia, quiet London. Not a breakout cue.
- **S5** after top-decile range (n=24): next day median 167 pts vs typical 83. Range persists. Small n.
- **S2** after 3 down days (n=33): P(up) 48% ±17%. Coin flip.
- **U6** break below daily open (n=231): continue 48%, return 52%.
- **U1** 33 Mondays, median range 97 pts (2.1%). **S1** Friday 88 pts.

R1 rivals still 53 / 62 / 72. Do not promote any of this.

## Spec hole this closes

`questions.md` is a compiler test bank. Mock maps every row. pandas runs only `ask`. `run`/`family` emit YAML and stop on gold. F* and A* refuse.
