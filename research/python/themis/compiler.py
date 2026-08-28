"""Mock compiler: English in, themis.job.v1 out. Never networks. No spend."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from themis import auth
from themis.paths import jobs_dir, questions_dir, repo_root, specs_dir
from themis.spec import dump_yaml

SCHEMA = "themis.job.v1"
GATES = {
    "freeze_yaml_before_metrics": True,
    "rivals_min": 2,
    "ask_before_run": True,
    "tune_requires": "walkforward_eligible",
}

# §9 bank. path: ask | run | family | needs_human | error
BANK: dict[str, dict[str, Any]] = {
    "G1": {
        "path": "run",
        "english": "4h swing high/low, enter retrace 61.8-72.5, stop swing low, target swing high",
        "needles": [("61.8", "72.5", "swing"), ("retrace 61.8",), ("61.8-72.5", "swing")],
    },
    "G2": {
        "path": "ask",
        "english": "Gold points and percent in Asian and London sessions",
        "needles": [("points and percent", "asian"), ("points and percent", "london"), ("gold points", "session")],
    },
    "G3": {
        "path": "ask",
        "english": "Prior-day ATR, lines at -33% and +33%, does price react",
        "needles": [("prior-day atr",), ("prior day atr",), ("-33%", "+33%"), ("atr", "33%")],
    },
    "G4": {
        "path": "family",
        "english": "Find the best Po3, or the best FVG",
        "needles": [("best fvg",), ("find the best po3",), ("best po3, or",), ("or the best fvg",)],
    },
    "R1": {
        "path": "ask",
        "english": "How many times has price bounced after a 75% retracement on this series, this timeframe?",
        "needles": [("75%", "retracement"), ("75% retracement",), ("bounced after a 75",)],
    },
    "R2": {
        "path": "ask",
        "english": "After that zone is touched, how often do we get a reaction within N bars before invalidation?",
        "needles": [("reaction within n bars",), ("before invalidation", "reaction")],
    },
    "R3": {
        "path": "ask",
        "english": "After the zone is touched, what is the MAE / MFE distribution? Where does a 1R stop usually sit?",
        "needles": [("mae", "mfe"), ("1r stop",)],
    },
    "U1": {
        "path": "ask",
        "english": "How much does this series move on Monday?",
        "needles": [("move on monday",), ("how much", "monday")],
    },
    "U2": {
        "path": "ask",
        "english": "How does today behave given yesterday? Does Monday change that?",
        "needles": [("today", "yesterday"), ("monday change that",)],
    },
    "U6": {
        "path": "ask",
        "english": "After a break below the daily open, what % continues vs returns?",
        "needles": [("break below the daily open",), ("daily open", "continues")],
    },
    "S1": {
        "path": "ask",
        "english": "Is Monday's range different from Friday's?",
        "needles": [("monday", "friday", "range"), ("monday's range",)],
    },
    "S2": {
        "path": "ask",
        "english": "After 3 down days, chance of an up day?",
        "needles": [("3 down days",), ("three down days",)],
    },
    "S5": {
        "path": "ask",
        "english": "After a top-decile range day, what is the next day's range?",
        "needles": [("top-decile",), ("top decile range",)],
    },
    "S12": {
        "path": "ask",
        "english": "What fraction of the daily range happens in each session?",
        "needles": [("fraction of the daily range",), ("daily range happens in each session",)],
    },
    "L1": {
        "path": "ask",
        "english": "How do Asia and London behave on this series (range, trend vs fade, where high/low form)?",
        "needles": [("asia and london behave",), ("where high/low form",)],
    },
    "L2": {
        "path": "ask",
        "english": "What share of the daily range is Asia vs London vs NY?",
        "needles": [("share of the daily range", "asia"), ("asia vs london vs ny",)],
    },
    "L3": {
        "path": "ask",
        "english": "If Asia is narrow, what does London usually do?",
        "needles": [("asia is narrow",), ("if asia is narrow",)],
    },
    "L4": {
        "path": "ask",
        "english": "If London breaks Asia, how often does NY continue vs fade?",
        "needles": [("london breaks asia",), ("ny continue vs fade",)],
    },
    "L5": {
        "path": "ask",
        "english": "Is the London open usually a continuation of Asia or a reversal?",
        "needles": [("london open", "continuation"), ("london open", "reversal")],
    },
    "B0": {
        "path": "run",
        "english": "From the 75% retracement, 1:1 R — what is the return / pnl / drawdown?",
        "needles": [("1:1", "return"), ("75% retracement", "pnl"), ("75% retracement", "return")],
    },
    "B1": {
        "path": "family",
        "english": "What is the best PO3 scenario on this series?",
        "needles": [("best po3",), ("best po3 scenario",)],
    },
    "B2": {
        "path": "family",
        "english": "What is the best A+ setup on this series?",
        "needles": [("best a+",), ("a+ setup",)],
    },
    "B3": {
        "path": "family",
        "english": "What is the best opening-range breakout on this series?",
        "needles": [("opening-range breakout",), ("opening range breakout",), ("best orb",)],
    },
    "B4": {
        "path": "family",
        "english": "Does a high prior-day-range Monday ORB beat a normal Monday ORB?",
        "needles": [("monday orb",), ("prior-day-range monday",)],
    },
    "B5": {
        "path": "family",
        "english": "Buy or sell the 61-75% pullback — is there edge after costs?",
        "needles": [("61-75%", "pullback"), ("61–75%", "edge"), ("buy or sell the 61",)],
    },
    "B6": {
        "path": "family",
        "english": "Optimize the kept retracement stop and target",
        "needles": [("optimize the kept",), ("optimize", "retracement stop")],
    },
    "F1": {"path": "needs_human", "english": "How does this series behave on CPI days?", "needles": [("cpi days",), ("on cpi",)], "why": "no event calendar"},
    "F2": {"path": "needs_human", "english": "Monday stats excluding NFP-Friday follow-through", "needles": [("nfp",), ("nfp-friday",)], "why": "no event calendar"},
    "F3": {"path": "needs_human", "english": "How does this series behave on FOMC days?", "needles": [("fomc",)], "why": "no event calendar"},
    "F4": {"path": "needs_human", "english": "This series vs DXY divergence — what happens next?", "needles": [("dxy",)], "why": "no named DXY series"},
    "A1": {"path": "error", "english": "Create the indicator for the winning spec", "needles": [("create the indicator",), ("indicator for the winning",)], "why": "after kept only"},
    "A2": {"path": "error", "english": "Create the alert for the winning spec", "needles": [("create the alert",), ("alert for the winning",)], "why": "after kept only"},
}
