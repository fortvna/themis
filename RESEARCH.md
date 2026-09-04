# RESEARCH.md — Themis

Minerva. 2026-09-01. Supports SPEC.md v0. Not a spike.

## Sources opened

- `docs/open-spec.md` 2026-08-28d especially §§17–20 (ideas, metrics, dual report, compiler prompt)
- `ADR/live-compile-named-stop.md`
- `research/python/pyproject.toml`, `themis/metrics.py`, `report.py`, `live.py`
- `COMPANY.md`, `WARROOM.md`

Not opened: Drive. argus/stake/university/ts-console/taap-taap source. Raw xAI prompt bytes.

## Operator ask (2026-09-01, WR-themis)

Speak an idea → YAML → pandas “is it worth it” → report MD **and** HTML with graphics → name the idea to bring back and improve → teach Themis Sharpe/Sortino/Calmar/PnL. Already specified in open-spec §§17–20. Folded into SPEC.md F-50+.

## Metrics (how they lie)

VERIFIED `docs/open-spec.md` §18. One number is a liar. Ask = path stats. Run = after-cost equity.

| metric | question | lie |
| --- | --- | --- |
| PnL / net_return | money on this window, 1 unit, after costs | ignores path and time |
| win_rate | how often green | useless without payoff |
| Sharpe | return / total vol, 365-day perp | penalises upside; short crypto window >2 is a red flag |
| Sortino | return / downside | better for swings; unstable if few down bars |
| Calmar | CAGR / worst DD | one observation; 7-month window is not a CTA 36-month Calmar |
| profit factor | gross win / gross loss | one outlier inflates it |

Kill stays min_trades 30 / max DD 40% / min_net_return 0. Do not kill on Sharpe in v1 (gold windows are short). VERIFIED §18.

“Worth it” = screen label from folders (`dead` / `weak` / `continue` then run `fail_kill` / `candidate`). Not `kept`. VERIFIED §17.

## As-is code vs SPEC

WIP already has `metrics.py`, HTML `report.py` (ask bars, hand-built SVG), idea HTML, short `LIVE_SYSTEM`. F-80 still needs full §20 prompt. F-72 equity/DD/hist is an M1 gap. Stack ADOPT: `ADR/stack-v1.md` (Python 3.11, pandas/numpy/pyyaml, inline SVG). matplotlib not runtime.

## Named-stop incident

English `low + 1 ATR` vs live YAML `low − ATR`. Both jobs fail. Do not mix. ADR stands.

## Competitors

UNKNOWN. No competitor files in this repo.
