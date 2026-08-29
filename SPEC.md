# SPEC.md

Minerva canon. Not a second spec.

The implementation spec is [`docs/open-spec.md`](docs/open-spec.md). Vulcan forges from that file. This pointer exists so the repo has an opened SPEC.md; do not fork requirements here.

Opened 2026-08-28. Revision **2026-08-28d** (family templates): `run` loads `implements`; same shape / new numbers stay on YAML; new kind needs a new family module. See open-spec §6.

Revision **2026-08-28c** (run engine): pandas fill + `metrics.py` from bar equity; same-bar SL/TP fills the stop; gap fills at open. See open-spec header.

Revision **2026-08-28b** (Minerva) adds, in open-spec §§17–20:

1. **Ideas** — when you tell Themis you have an idea, she names it (a slug you can bring back), freezes YAML, runs pandas to screen whether the path is even a thing, and lets you `improve` the same slug without overwriting the parent.
2. **Dual reports** — Markdown stays the quoteable artifact. HTML is written too, with graphics (equity, drawdown, PnL hist, rival-rate bars) from the run folder only. No CDN.
3. **Metrics canon** — strategy runs compute PnL, net return, max drawdown, CAGR, Sharpe, Sortino, Calmar, profit factor, expectancy, win rate, payoff from equity/trades. Ask stays path stats. "Worth it" is a screen, not `kept`. One ratio is not a promotion.
4. **Compiler prompt** — live Themis uses the expert prompt in open-spec §20 so a model compiles like this desk: pin named stops, rival only the unnamed, never invent a number.

Law, venue, gated ladder, and the §9 bank are unchanged. See `docs/open-spec.md`.
