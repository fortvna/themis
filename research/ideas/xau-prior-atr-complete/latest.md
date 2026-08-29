# xau-prior-atr-complete

Ask. Not a trade. Not pnl. Binance USD-M XAUUSDT perp, not COMEX.

English: *On Gold, for the last month, how many times the ATR is completed from the previous day*

Unnamed keys rivalled: ATR length 14 vs 20; complete = UTC daily range vs excursion from daily open. Window pinned: last calendar month of bars actually loaded.

Loaded: Vision 4h 2026-05-01 → 2026-07-31 (552 bars). August 2026 zip HTTP 404. Outcome month: **2026-07-01 → 2026-07-31**, n = 31 days. Prior ATR is knowable at the prior daily close (`shift(1)`).

Copied from run folders:

| definition | n | n complete | complete_rate | Wald 95% CI half-width | folder |
| --- | ---: | ---: | ---: | ---: | --- |
| ATR14 / day_range | 31 | 15 | 0.4839 | 0.1759 | `20260829T025701Z-xau-atr-complete-atr14-range-bdc0a206` |
| ATR20 / day_range | 31 | 14 | 0.4516 | 0.1752 | `20260829T025701Z-xau-atr-complete-atr20-range-0e82332a` |
| ATR14 / from_open | 31 | 10 | 0.3226 | 0.1646 | `20260829T025701Z-xau-atr-complete-atr14-fromopen-5f1402d5` |
| ATR20 / from_open | 31 | 10 | 0.3226 | 0.1646 | `20260829T025701Z-xau-atr-complete-atr20-fromopen-a8074693` |

Screen: **weak** (n=31, CIs overlap). Not `kept`. No `run`. Do not multiply these rates by R.

HTML: `research/ideas/xau-prior-atr-complete/latest.html`  
Notebook (Run All representation of `themis.ask`; no ATR math in cells): `research/ideas/xau-prior-atr-complete/latest.ipynb`
