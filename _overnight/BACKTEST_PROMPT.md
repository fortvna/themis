You are hardening the Themis v1 **backtest / run engine** overnight. Repo cwd: themis root.

## Product law
- pandas bar-loop is v1 `run` (NOT kernc backtesting.py). Path: load `implements` → `trades()` → `themis.fill` → `metrics.py`.
- Fees from `themis.fees` (Binance Regular). YAML only records what Python froze. Never invent PnL in chat.
- Use ONLY `research/python/.venv`. Never pip --user.
- Canon: docs/open-spec.md run path, §18 metrics, family templates, fees module.

## Goal (ship-ready run engine)
1. Audit `runner.py`, `fill.py`, `metrics.py`, `fees.py`, `implements.py`, `strategies/retrace_swing.py` vs open-spec.
2. Close real gaps so `themis run --spec <yaml>` writes honest folders:
   - trades.csv, equity.csv (bar index), metrics.json with Sharpe/Sortino/Calmar/CAGR/PF/expectancy/winrate/payoff when equity has ≥2 points
   - missing ratios → not_computed map with reasons
   - always list not modeled: perp funding, intra-bar path
   - same-bar SL+TP → ambiguous_same_bar, fill at stop; gap through level → fill at open
   - no silent 0.618 in runner; costs required; requires_asks enforced; --thin for gold discovery
3. Add/fix tests under research/python/tests/ (metrics, run, implements) — keep green.
4. Prove offline if possible: find or compile a strategy YAML (B0/G1 family with costs) that has requires_asks pointing at existing ask folders OR create minimal fixture; run:
   `research/python/.venv/bin/themis run --spec … --offline` (or equivalent CLI flags)
   Quote metrics ONLY from the run folder.
5. Write `/workspace/fortuna/projects/themis/_overnight/MORNING.md` with:
   - what's ready
   - commands to demo idea loop + run
   - remaining gaps (esp. live xai compile if still open)
   - pytest summary

Do not redesign ask/idea loop unless a run blocker forces a tiny fix. Prefer not to push. Local commit OK if tests pass and message is clear.
