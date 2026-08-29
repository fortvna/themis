"""SMA crossover family stub. Not a v1 run engine."""
from __future__ import annotations

from typing import Any

import pandas as pd

REQUIRED_SPEC_KEYS = ("n_fast", "n_slow")
FILL = "next_open"


def trades(spec: dict[str, Any], df: pd.DataFrame, *, commission: float = 0.0, slip: float = 0.0) -> pd.DataFrame:
    raise NotImplementedError(
        "strategies/sma_cross.py is a stub family. "
        "v1 retrace-swing English uses strategies/retrace_swing.py. "
        "Do not run this implements until a real SMA module exists."
    )
