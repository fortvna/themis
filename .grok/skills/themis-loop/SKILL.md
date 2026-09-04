---
name: themis-loop
description: >
  Run the Themis research loop with the operator: English → frozen YAML →
  pandas ask → HTML + notebook + idea slug. Use when the user has a trading
  idea, wants to ask a path question on gold/BTC/SOL/SPY/QQQ, says "run the
  loop", "themis idea", "screen this", "bring back" an idea, or runs
  /themis-loop. Do not invent bounce rates, pnl, or Sharpe in chat.
---

# Themis loop

The operator speaks English. You run **`themis idea`**. Python writes folders. You quote those folders. You do not compute the answer in chat.

Canon: `docs/open-spec.md` §17–19. Screens and metrics live there — do not restate the tables here.

## Binary

Always:

```
research/python/.venv/bin/themis
```

If that file is missing: `cd research/python && ./bootstrap.sh`. Never `pip install --user`. Never system Python.

## Do this

1. Name the series from English. Pass **all four** flags every time (do not rely on CLI defaults):

   | English | `--symbol` | never say |
   | --- | --- | --- |
   | gold / xau | `XAUUSDT` | COMEX |
   | btc / bitcoin | `BTCUSDT` | |
   | sol | `SOLUSDT` | |
   | spy | `SPYUSDT` | ES / e-mini |
   | qqq | `QQQUSDT` | NQ / e-mini |

   `--provider binance --exchange binanceusdm`. Timeframe from English, else `--timeframe 4h`.

2. Run **one** conversation command:

   ```
   research/python/.venv/bin/themis idea --english "…" \
     --provider binance --symbol <SYM> --timeframe <TF> --exchange binanceusdm
   ```

   Optional: `--name <slug>` when they name it; `--csv <path> --offline` when they hand you bars; `--thin` only if they asked return **and** the series is gold/SPY/QQQ (still cannot `kept`).

3. Subcommands, same binary:

   | they say | you run |
   | --- | --- |
   | list ideas | `idea list` |
   | show / open `<slug>` | `idea show --name <slug>` then `report --idea <slug>` |
   | bring back / try a new stop / redefine | `idea improve --name <slug> --english "…" --provider … --symbol … --timeframe … --exchange …` |

4. After the CLI returns, open `research/ideas/<slug>/idea.yaml` and `latest.md` / `latest.html` / `latest.ipynb`. Quote `n`, rates, pnl **only** from `research/runs/<id>/metrics.json` (or the report that cites that folder). Screen labels are not `kept`.

## Stop

- `status: needs_human` → ask them to name stop / target / retrace, or pick a `questions.md` row. Do not invent those fields.
- `already exists` → `idea improve` or ask for a new `--name`. Do not suffix the slug.
- Auto-`run` happens only when English asked return / pnl / "how good" / "backtest". A bounce/ATR/session question is **ask only**.
- Same shape, new numbers → same `implements`, new spec id. New kind (ORB, FVG, Po3) → `needs_human` unless a family module exists. Never a new `.py` per chat line.
- YAML is not executable. Chat is not the record.
