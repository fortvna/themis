"""Case builders for the mock compiler."""
from __future__ import annotations

from typing import Any


def build_case(cid: str, rec: dict[str, Any], series: dict[str, str], english: str):
    from themis.compiler import (
        BANK,
        _question,
        _strategy,
        _series_id,
        _sym_tag,
        _tf_tag,
    )
    path = rec["path"]
    tag = _sym_tag(series["symbol"])
    tf = _tf_tag(series["timeframe"])
    family = f"{cid.lower()}-{tag}-{tf}-v1"
    qs: list[dict] = []
    ss: list[dict] = []
    note = rec.get("why") or rec["english"]

    if path in ("needs_human", "error"):
        return qs, ss, path, rec.get("why") or path

    if cid == "G1":
        q5 = _question(
            _series_id("g1", "n5", series),
            "Touch 61.8-72.5 retrace of a confirmed swing, then target vs stop",
            series,
            measure="swing_retrace",
            extra={"question_ref": "G1", "family": family, "fractal_n": 5},
            definitions={
                "swing_high": "bar i is a swing high if high[i] is strictly the max of i-n..i+n, n=5. Knowable at i+n.",
                "swing_low": "bar i is a swing low if low[i] is strictly the min of i-n..i+n, n=5. Knowable at i+n.",
                "zone_long": "extreme - 0.725*range through extreme - 0.618*range",
                "entry_touch": "closed bar whose range first intersects the zone after the swing is knowable.",
            },
            condition=[{"kind": "retracement_zone", "pct_low": 0.618, "pct_high": 0.725, "of": "confirmed_swing", "fractal_n": 5}],
            outcome={"name": "target_before_stop", "kind": "flag", "target": "swing_extreme", "stop": "swing_origin"},
            stats=["n", "target_rate", "stop_rate", "neither_rate"],
        )
        q3 = _question(
            _series_id("g1", "n3", series),
            "Same as n5 cousin, fractal n=3",
            series,
            measure="swing_retrace",
            extra={"question_ref": "G1", "family": family, "fractal_n": 3},
            definitions={
                "swing_high": "fractal n=3. Knowable at i+3.",
                "swing_low": "fractal n=3. Knowable at i+3.",
            },
            condition=[{"kind": "retracement_zone", "pct_low": 0.618, "pct_high": 0.725, "of": "confirmed_swing", "fractal_n": 3}],
            outcome={"name": "target_before_stop", "kind": "flag", "target": "swing_extreme", "stop": "swing_origin"},
            stats=["n", "target_rate", "stop_rate", "neither_rate"],
        )
        st = _strategy(
            _series_id("g1", "n5-1r", series),
            "Enter 61.8-72.5 of confirmed n=5 swing, stop origin, target extreme",
            series,
            family=family,
            implements="strategies/retrace_swing.py",
            requires=[q5["id"], q3["id"]],
            rules={
                "fill": "next_open",
                "entry": "next open after closed-bar zone touch, swing already knowable",
                "stop": "beyond swing origin",
                "target": "swing extreme",
                "calc_on_closed_bar": True,
            },
            extra={"fractal_n": 5, "pct_low": 0.618, "pct_high": 0.725},
        )
        return [q5, q3], [st], path, "two swing fractals then strategy not eligible"

    if cid in ("G2", "L1", "L2", "S12"):
        clocks = [
            ("asia00-07-lon07-16", {"asia": [0, 7], "london": [7, 16], "ny": [16, 24]}),
            ("asia00-08-lon08-16", {"asia": [0, 8], "london": [8, 16], "ny": [16, 24]}),
        ]
        for suffix, win in clocks:
            qs.append(
                _question(
                    _series_id(cid, suffix, series),
                    f"{english} clocks {suffix}",
                    series,
                    measure="session_range",
                    population="session_days",
                    extra={"question_ref": cid, "family": family, "windows_utc": win},
                    definitions={
                        "asia": f"UTC hours {win['asia'][0]:02d}:00-{win['asia'][1]:02d}:00",
                        "london": f"UTC hours {win['london'][0]:02d}:00-{win['london'][1]:02d}:00",
                        "ny": f"UTC hours {win['ny'][0]:02d}:00-{win['ny'][1]:02d}:00",
                        "range_pts": "session high-low in price points",
                        "range_pct_prior": "session range / prior UTC day range",
                    },
                    condition=[{"kind": "session_clock", "windows_utc": win}],
                    outcome={"name": "session_range", "kind": "descriptive"},
                    stats=["n_days", "asia_median_pts", "london_median_pts", "ny_median_pts", "asia_share", "london_share"],
                )
            )
        return qs, ss, "ask", "two clock windows"

    if cid == "G3":
        for n_atr, react, suffix in (
            (14, "through", "atr14-through"),
            (20, "through", "atr20-through"),
            (14, "half_atr", "atr14-half"),
            (20, "half_atr", "atr20-half"),
        ):
            qs.append(
                _question(
                    _series_id("g3", suffix, series),
                    f"Prior-day ATR {n_atr}, ±33%, react={react}",
                    series,
                    measure="atr_react",
                    population="session_days",
                    extra={"question_ref": "G3", "family": family, "atr_n": n_atr, "react": react},
                    definitions={
                        "atr": f"daily ATR length {n_atr}, knowable at prior daily close",
                        "line_hi": "prior_close + 0.33 * prior_atr",
                        "line_lo": "prior_close - 0.33 * prior_atr",
                        "react": "close back through the line" if react == "through" else "0.5x ATR reaction",
                    },
                    condition=[{"kind": "atr_levels", "atr_n": n_atr, "pct": 0.33, "react": react}],
                    outcome={"name": "react_flag", "kind": "flag"},
                    stats=["n_days", "n_touch_plus33", "n_touch_minus33", "react_plus", "react_minus"],
                )
            )
        return qs, ss, "ask", "ATR 14 vs 20; react close-through vs 0.5 ATR"

    if cid == "R1":
        rivals = [
            ("imp12-through50", {"impulse_bars": 12, "impulse_atr": 1.5, "bounce": "through_50"}),
            ("imp8-atr", {"impulse_bars": 8, "impulse_atr": 1.2, "bounce": "atr"}),
        ]
        for suffix, cfg in rivals:
            qs.append(
                _question(
                    _series_id("r1", suffix, series),
                    f"Bounce after 75% retracement {suffix}",
                    series,
                    measure="bounce_retrace",
                    extra={"question_ref": "R1", "family": family, **cfg, "retrace_pct": 0.75},
                    definitions={
                        "impulse": f"{cfg['impulse_bars']}-bar move of {cfg['impulse_atr']} ATR",
                        "zone": "75% retrace of that impulse",
                        "bounce": "close back through 50%" if cfg["bounce"] == "through_50" else "1x ATR reaction",
                    },
                    condition=[{"kind": "retracement_zone", "pct_low": 0.75, "pct_high": 0.75, **cfg}],
                    outcome={"name": "bounced", "kind": "flag"},
                    stats=["n", "bounce_rate"],
                )
            )
        return qs, ss, "ask", "impulse 12 vs 8; bounce through-50 vs ATR"

    if cid == "R2":
        for nbar in (6, 12):
            qs.append(
                _question(
                    _series_id("r2", f"n{nbar}", series),
                    f"Reaction within {nbar} bars before invalidation",
                    series,
                    measure="bounce_retrace",
                    extra={"question_ref": "R2", "family": family, "horizon_bars": nbar, "impulse_bars": 12, "impulse_atr": 1.5, "bounce": "through_50", "retrace_pct": 0.75},
                    definitions={
                        "reaction": "an outcome, not an entry",
                        "horizon": f"N={nbar} bars after zone touch",
                        "invalidation": "close through impulse origin",
                    },
                    condition=[{"kind": "reaction_horizon", "n": nbar}],
                    outcome={"name": "reacted_before_invalidation", "kind": "flag"},
                    stats=["n", "p_reaction", "p_invalidated"],
                )
            )
        return qs, ss, "ask", "N=6 vs N=12"

    if cid == "R3":
        rivals = [
            ("imp12", {"impulse_bars": 12, "impulse_atr": 1.5}),
            ("imp8", {"impulse_bars": 8, "impulse_atr": 1.2}),
        ]
        for suffix, cfg in rivals:
            qs.append(
                _question(
                    _series_id("r3", suffix, series),
                    f"MAE/MFE after 75% zone touch {suffix}",
                    series,
                    measure="bounce_retrace",
                    extra={"question_ref": "R3", "family": family, "want_mae_mfe": True, "retrace_pct": 0.75, **cfg, "bounce": "through_50"},
                    definitions={
                        "mae": "max adverse excursion in price points after touch; path, not pnl",
                        "mfe": "max favorable excursion in price points after touch; path, not pnl",
                        "impulse": f"{cfg['impulse_bars']}-bar {cfg['impulse_atr']} ATR",
                    },
                    condition=[{"kind": "retracement_zone", "pct_low": 0.75, "pct_high": 0.75, **cfg}],
                    outcome={"name": "path_mae_mfe", "kind": "distribution"},
                    stats=["n", "median_mae", "median_mfe"],
                )
            )
        return qs, ss, "ask", "path stats after 75% touch"

    if cid in ("U1", "S1"):
        for cal, suffix in (("utc", "utc"), ("exchange", "exchange")):
            qs.append(
                _question(
                    _series_id(cid, suffix, series),
                    rec["english"] + f" calendar={cal}",
                    series,
                    measure="weekday_range",
                    population="session_days",
                    extra={"question_ref": cid, "family": family, "calendar": cal},
                    definitions={
                        "monday": "weekday=0 in named calendar",
                        "friday": "weekday=4 in named calendar",
                        "calendar": cal,
                    },
                    condition=[{"kind": "weekday", "calendar": cal}],
                    outcome={"name": "range_pts_pct", "kind": "descriptive"},
                    stats=["n_mon", "median_mon_pts", "n_fri", "median_fri_pts"] if cid == "S1" else ["n_mondays", "median_range_pts", "median_range_pct"],
                )
            )
        return qs, ss, "ask", "weekday window UTC vs exchange"

    if cid == "U2":
        for split, suffix in ((False, "no-monday-split"), (True, "monday-split")):
            qs.append(
                _question(
                    _series_id("u2", suffix, series),
                    rec["english"] + f" monday_split={split}",
                    series,
                    measure="day_condition",
                    population="session_days",
                    extra={"question_ref": "U2", "family": family, "monday_split": split, "day_kind": "given_yesterday"},
                    definitions={"up": "daily close > daily open", "monday_split": str(split)},
                    condition=[{"kind": "given_yesterday", "monday_split": split}],
                    outcome={"name": "p_up_given_up", "kind": "rate"},
                    stats=["n", "p_up_given_up", "p_up_given_up_monday"] if split else ["n", "p_up_given_up"],
                )
            )
        return qs, ss, "ask", "with vs without Monday split"

    if cid == "U6":
        for how, suffix in (("close_still_below", "close"), ("range_extension", "extension")):
            qs.append(
                _question(
                    _series_id("u6", suffix, series),
                    rec["english"] + f" continue={how}",
                    series,
                    measure="day_condition",
                    population="session_days",
                    extra={"question_ref": "U6", "family": family, "day_kind": "break_daily_open", "continue_def": how},
                    definitions={
                        "break": "daily low < daily open",
                        "continue": how,
                    },
                    condition=[{"kind": "break_daily_open", "continue_def": how}],
                    outcome={"name": "continue_vs_return", "kind": "rate"},
                    stats=["n_breaks", "continue_rate", "return_rate"],
                )
            )
        return qs, ss, "ask", "continue = close still below vs range extension"

    if cid == "S2":
        for how, suffix in (("close_to_close", "c2c"), ("close_vs_prior_low", "vs-prior-low")):
            qs.append(
                _question(
                    _series_id("s2", suffix, series),
                    rec["english"] + f" {how}",
                    series,
                    measure="day_condition",
                    population="session_days",
                    extra={"question_ref": "S2", "family": family, "day_kind": "three_down", "up_def": how},
                    definitions={"three_down": "three prior days close < open", "up": how},
                    condition=[{"kind": "three_down", "up_def": how}],
                    outcome={"name": "p_up", "kind": "rate"},
                    stats=["n", "p_up"],
                )
            )
        return qs, ss, "ask", "close-to-close vs close vs prior low"

    if cid == "S5":
        for look, suffix in ((20, "decile20"), (60, "decile60")):
            qs.append(
                _question(
                    _series_id("s5", suffix, series),
                    rec["english"] + f" lookback={look}",
                    series,
                    measure="day_condition",
                    population="session_days",
                    extra={"question_ref": "S5", "family": family, "day_kind": "top_decile", "lookback": look},
                    definitions={"top_decile": f"prior-day range in top decile of {look} sessions"},
                    condition=[{"kind": "top_decile_range", "lookback": look}],
                    outcome={"name": "next_range", "kind": "descriptive"},
                    stats=["n", "next_median_pts", "typical_median_pts"],
                )
            )
        return qs, ss, "ask", "decile of 20 vs 60 sessions"

    if cid == "L3":
        for how, suffix in (("bottom_quartile", "q25"), ("half_atr", "half-atr")):
            qs.append(
                _question(
                    _series_id("l3", suffix, series),
                    rec["english"] + f" narrow={how}",
                    series,
                    measure="session_condition",
                    population="session_days",
                    extra={"question_ref": "L3", "family": family, "session_kind": "asia_narrow", "narrow": how, "windows_utc": {"asia": [0, 7], "london": [7, 16]}},
                    definitions={"narrow": how, "asia": "00:00-07:00 UTC"},
                    condition=[{"kind": "asia_narrow", "narrow": how}],
                    outcome={"name": "london_range_given_narrow_asia", "kind": "descriptive"},
                    stats=["n_narrow", "london_median_if_asia_narrow", "london_median_otherwise"],
                )
            )
        return qs, ss, "ask", "narrow = bottom quartile vs < 0.5xATR"

    if cid == "L4":
        for how, suffix in (("close", "close"), ("wick", "wick")):
            qs.append(
                _question(
                    _series_id("l4", suffix, series),
                    rec["english"] + f" break={how}",
                    series,
                    measure="session_condition",
                    population="session_days",
                    extra={"question_ref": "L4", "family": family, "session_kind": "london_breaks_asia", "break_def": how, "windows_utc": {"asia": [0, 7], "london": [7, 16], "ny": [16, 24]}},
                    definitions={"break": "close beyond Asia high/low" if how == "close" else "wick beyond Asia high/low"},
                    condition=[{"kind": "london_breaks_asia", "break_def": how}],
                    outcome={"name": "ny_continue_vs_fade", "kind": "rate"},
                    stats=["n_london_breaks_asia", "ny_continue", "ny_fade"],
                )
            )
        return qs, ss, "ask", "break = close beyond Asia high/low vs wick"

    if cid == "L5":
        for open_h, suffix in ((7, "open07"), (8, "open08")):
            qs.append(
                _question(
                    _series_id("l5", suffix, series),
                    rec["english"] + f" london open {open_h:02d}:00",
                    series,
                    measure="session_condition",
                    population="session_days",
                    extra={"question_ref": "L5", "family": family, "session_kind": "london_open", "london_open_hour": open_h, "windows_utc": {"asia": [0, open_h], "london": [open_h, 16]}},
                    definitions={"london_open": f"{open_h:02d}:00 UTC", "continuation": "London session direction matches Asia"},
                    condition=[{"kind": "london_open", "hour": open_h}],
                    outcome={"name": "continuation_vs_reversal", "kind": "rate"},
                    stats=["n", "p_london_up_given_asia_up", "p_london_up_given_asia_down"],
                )
            )
        return qs, ss, "ask", "open window 07:00 vs 08:00"

    if cid == "B0":
        r1q, _, _, _ = build_case("R1", BANK["R1"], series, BANK["R1"]["english"])
        r3q, _, _, _ = build_case("R3", BANK["R3"], series, BANK["R3"]["english"])
        qs = r1q + r3q
        st = _strategy(
            _series_id("b0", "1r", series),
            "From the 75% retracement, 1:1 R",
            series,
            family=family,
            implements="strategies/retrace_swing.py",
            requires=[q["id"] for q in qs],
            rules={
                "fill": "next_open",
                "entry": "next open after 75% retrace touch of named impulse",
                "stop": "beyond impulse origin (1R)",
                "target": "1R toward impulse extreme",
            },
            extra={"retrace_pct": 0.75, "fractal_n": 5},
        )
        return qs, [st], "run", "requires R1+R3 asks; gold thin; no pandas return"

    def _family_pair(def_a: dict, def_b: dict, impl: str = "strategies/retrace_swing.py") -> tuple[list[dict], list[dict]]:
        q_a = _question(
            _series_id(cid, "def-a", series),
            def_a["title"],
            series,
            measure=def_a.get("measure", "generic"),
            extra={"question_ref": cid, "family": family, **def_a.get("extra", {})},
            definitions=def_a["definitions"],
            condition=def_a["condition"],
            outcome=def_a.get("outcome", {"name": "flag", "kind": "flag"}),
            stats=def_a.get("stats", ["n"]),
        )
        q_b = _question(
            _series_id(cid, "def-b", series),
            def_b["title"],
            series,
            measure=def_b.get("measure", "generic"),
            extra={"question_ref": cid, "family": family, **def_b.get("extra", {})},
            definitions=def_b["definitions"],
            condition=def_b["condition"],
            outcome=def_b.get("outcome", {"name": "flag", "kind": "flag"}),
            stats=def_b.get("stats", ["n"]),
        )
        st_a = _strategy(
            _series_id(cid, "cousin-a", series),
            def_a["title"] + " cousin a",
            series,
            family=family,
            implements=impl,
            requires=[q_a["id"]],
            rules=def_a.get("rules", {"fill": "next_open", "entry": "named", "stop": "named", "target": "named"}),
        )
        st_b = _strategy(
            _series_id(cid, "cousin-b", series),
            def_b["title"] + " cousin b",
            series,
            family=family,
            implements=impl,
            requires=[q_b["id"]],
            rules=def_b.get("rules", {"fill": "next_open", "entry": "named", "stop": "named", "target": "named"}),
        )
        if cid == "B6":
            st_a["search_space"] = {"stop_atr": [1.0, 1.5], "target_r": [1.0, 2.0]}
            st_b["search_space"] = {"stop_atr": [1.0, 1.5], "target_r": [1.0, 2.0]}
            st_a["note"] = "tune on this series still requires walkforward_eligible from loaded bars"
            st_b["note"] = st_a["note"]
        return [q_a, q_b], [st_a, st_b]

    if cid in ("G4", "B1"):
        qs, ss = _family_pair(
            {
                "title": "Po3 3-bar displacement, sweep of prior wick",
                "measure": "generic",
                "definitions": {
                    "po3": "3-bar pattern: accumulation, manipulation (wick sweep), displacement candle",
                    "displacement": "the third candle body",
                    "sweep": "wick through prior 3-bar high/low",
                },
                "condition": [{"kind": "po3", "bars": 3}],
            },
            {
                "title": "Po3 5-bar / FVG 50% fill vs full fill",
                "measure": "generic",
                "definitions": {
                    "po3": "5-bar displacement",
                    "fvg": "3-candle imbalance",
                    "fill": "50% vs full fill; continuation vs fade as cousins later",
                },
                "condition": [{"kind": "po3", "bars": 5}],
            },
        )
        note = "rival asks plus family; refuse a single-winner on a thin series; tune refused until WF eligible"
        return qs, ss, "family", note

    if cid == "B2":
        qs, ss = _family_pair(
            {
                "title": "A+ = session extreme + displacement close",
                "measure": "generic",
                "definitions": {"a_plus": "A+ pinned as London extreme plus displacement close through prior high/low. Not an interview."},
                "condition": [{"kind": "a_plus", "def": "displacement"}],
            },
            {
                "title": "A+ = FVG hold + session VWAP reclaim",
                "measure": "generic",
                "definitions": {"a_plus": "A+ pinned as FVG hold plus reclaim. Rival of displacement definition."},
                "condition": [{"kind": "a_plus", "def": "fvg_hold"}],
            },
        )
        return qs, ss, "family", "needs A+ definition asks; no winner on gold"

    if cid == "B3":
        qs, ss = _family_pair(
            {
                "title": "ORB first 1h London",
                "measure": "generic",
                "definitions": {"orb": "opening range = first 1h of London 07:00-08:00 UTC"},
                "condition": [{"kind": "orb", "hours": 1}],
                "rules": {"fill": "next_open", "entry": "break of 1h OR", "stop": "other side of OR", "target": "1R"},
            },
            {
                "title": "ORB first 2h London",
                "measure": "generic",
                "definitions": {"orb": "opening range = first 2h of London 07:00-09:00 UTC"},
                "condition": [{"kind": "orb", "hours": 2}],
                "rules": {"fill": "next_open", "entry": "break of 2h OR", "stop": "other side of OR", "target": "1R"},
            },
        )
        return qs, ss, "family", "ORB family; gold not WF"

    if cid == "B4":
        qs, ss = _family_pair(
            {
                "title": "High prior-day-range Monday ORB",
                "measure": "generic",
                "definitions": {"high_range": "prior day in top quartile of 20-session range", "orb": "London first 1h"},
                "condition": [{"kind": "monday_orb", "filter": "high_prior_range"}],
            },
            {
                "title": "Normal Monday ORB",
                "measure": "generic",
                "definitions": {"normal": "Monday not in top-quartile prior-day range", "orb": "London first 1h"},
                "condition": [{"kind": "monday_orb", "filter": "normal"}],
            },
        )
        return qs, ss, "family", "two cousins, compare after run; still not best on gold"

    if cid == "B5":
        qs, ss = _family_pair(
            {
                "title": "Buy/sell 61% pullback",
                "measure": "swing_retrace",
                "extra": {"fractal_n": 5, "pct_low": 0.61, "pct_high": 0.61},
                "definitions": {"zone": "61% retrace of confirmed n=5 swing"},
                "condition": [{"kind": "retracement_zone", "pct_low": 0.61, "pct_high": 0.61, "fractal_n": 5}],
                "rules": {"fill": "next_open", "entry": "61% zone touch", "stop": "swing origin", "target": "swing extreme"},
            },
            {
                "title": "Buy/sell 75% pullback",
                "measure": "swing_retrace",
                "extra": {"fractal_n": 5, "pct_low": 0.75, "pct_high": 0.75},
                "definitions": {"zone": "75% retrace of confirmed n=5 swing"},
                "condition": [{"kind": "retracement_zone", "pct_low": 0.75, "pct_high": 0.75, "fractal_n": 5}],
                "rules": {"fill": "next_open", "entry": "75% zone touch", "stop": "swing origin", "target": "swing extreme"},
            },
        )
        return qs, ss, "family", "zone 61 vs 75; costs required before any run"

    if cid == "B6":
        qs, ss = _family_pair(
            {
                "title": "Kept retracement stop/target cousin A (tighter stop)",
                "measure": "swing_retrace",
                "definitions": {"note": "tune enumerates search_space; each candidate a new spec id. gold WF floor errors."},
                "condition": [{"kind": "retracement_zone", "pct_low": 0.618, "pct_high": 0.725, "fractal_n": 5}],
            },
            {
                "title": "Kept retracement stop/target cousin B (wider target)",
                "measure": "swing_retrace",
                "definitions": {"note": "BTC/SOL may tune this family when bars clear the WF floor."},
                "condition": [{"kind": "retracement_zone", "pct_low": 0.618, "pct_high": 0.725, "fractal_n": 5}],
            },
        )
        return qs, ss, "family", "tune refuse: not WF eligible on thin series"

    q = _question(
        _series_id(cid, "a", series),
        rec["english"],
        series,
        measure="generic",
        definitions={"pinned": rec["english"]},
        condition=[{"kind": "generic"}],
        outcome={"name": "descriptive", "kind": "descriptive"},
        stats=["n"],
    )
    q2 = _question(
        _series_id(cid, "b", series),
        rec["english"] + " rival b",
        series,
        measure="generic",
        definitions={"pinned": "rival definition b"},
        condition=[{"kind": "generic", "rival": "b"}],
        outcome={"name": "descriptive", "kind": "descriptive"},
        stats=["n"],
    )
    return [q, q2], ss, path, "generic"
