"""v1 implements: SMA crossover. Next-open fill via backtesting.py (trade_on_close=False)."""

from __future__ import annotations

import pandas as pd
from backtesting import Strategy
from backtesting.lib import crossover


def SMA(s, n):
    return pd.Series(s).rolling(int(n)).mean()


class SmaCross(Strategy):
    n1 = 10
    n2 = 40

    def init(self):
        self.fast = self.I(SMA, self.data.Close, self.n1)
        self.slow = self.I(SMA, self.data.Close, self.n2)

    def next(self):
        if crossover(self.fast, self.slow):
            self.position.close()
            self.buy()
        elif crossover(self.slow, self.fast):
            self.position.close()
            self.sell()
