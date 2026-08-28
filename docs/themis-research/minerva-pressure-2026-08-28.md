# Pressure test: English-to-code trading harness

Minerva. 2026-08-28. Extra research. Not a spec. Not a build.

Target: ask → prove → metrics → backtest → walk-forward → auto-optimize
Books: Binance `XAUUSDT`, `BTCUSDT`, `SOLUSDT`, `SPYUSDT`, `QQQUSDT`.

Land in `fortvna/themis` with the other notes. Caesar: Themis only.

Prometheus's real gold ask (Vision 4h, 1396 bars, 2025-12-11 → 2026-07-31) is the sample this note uses. I did not rebuild it.

## Verdict

The *loop* is coherent. The *ladder on every symbol* is not.

Ask on gold is coherent. A first `run` on gold is barely coherent (thin n, no funding, optimistic 4h SL/TP). Walk-forward and auto-optimize on gold, SPY, and QQQ are wrong with the history we actually have. Those stages belong on BTC/SOL, or the CLI must refuse them until n and holdout clear a floor.

If the spec promises Amir's full ladder on gold, it will lie.
