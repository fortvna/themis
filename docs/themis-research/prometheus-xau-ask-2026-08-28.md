# Addendum: real Binance XAUUSDT 4h ask

Prometheus. 2026-08-28. Vision monthly zips, USD-M, 4h. Not a harness. Not a strategy. Do not quote as edge.

Series: Binance `XAUUSDT` 4h. 1396 bars, 2025-12-11 08:00 UTC to 2026-07-31 20:00 UTC.
Dec 2025 is thin (124 bars, volume median 81 vs 21745 after). Listing noise.

Same 75% retrace English, three definitions:

| id | n | bounce | 95% CI half-width | invalidated |
| --- | ---: | ---: | ---: | ---: |
| A 12-bar / through 50% | 58 | 53.5% | ±12.8% | 41.4% |
| B 8-bar / through 50% | 86 | 61.6% | ±10.3% | 30.2% |
| C 12-bar / 1×ATR reaction | 58 | 72.4% | ±11.5% | 24.1% |

Definition swing is 19 points. Sampling noise is ~11–13 points. On this gold window they are the same size. A 72% bounce in chat is a definition, not a market.

Implication for the harness Amir named (English → prove → metrics → backtest → walk-forward → auto-optimize):

- `ask` on gold is coherent. n is small. CI is wide.
- `run` is barely coherent. Kill `min_trades: 30` eats half the sample.
- Walk-forward and auto-optimize on gold 4h are wrong until the series is longer. Do them on BTC/SOL first, or refuse `tune` until n and holdout length pass a floor.
- English-to-code without mandatory rival asks will ship definition C as “72% gold bounce.”

Fixture stays off git. These Vision CSVs stay off git.
