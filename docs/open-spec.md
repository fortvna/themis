# Themis open spec

Minerva. 2026-08-28. This is the spec. Not a build.

Supersedes `prompt.md` for implementation. Research notes sit beside this file; they are not the spec.
Vulcan forges from this document. Fixtures, event tables, and Vision CSVs stay off git.

## 1. Product

**Themis** is a research loop you can talk to. English in. YAML frozen. Then pandas or `backtesting.py` writes a run folder. Chat does not invent numbers.

Go-live is that conversation working on files. Not an order. Not a broker. Not a warehouse.

Package and CLI name: `themis`. Repository: `fortvna/themis`.

V1 venue is **Binance** (USD-M perps via `binanceusdm`). Series:

| symbol | English | identity |
| --- | --- | --- |
| XAUUSDT | Gold | this venue's gold perp, not COMEX, not another venue |
| BTCUSDT | BTC | this venue's BTC perp |
| SOLUSDT | SOL | this venue's SOL perp |
| SPYUSDT | SPY stand-in | ETF perp, **not ES** |
| QQQUSDT | QQQ stand-in | ETF perp, **not NQ** |

Same ticker on another venue is a different series. Do not merge. Do not relabel.
