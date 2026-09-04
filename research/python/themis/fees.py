"""Binance venue fee law. Python freezes numbers; YAML only records them.

Published 2026-09-03 from Binance Regular / VIP0 pages, no BNB unless named.
USD-M crypto: https://www.binance.com/en/fee/futureFee
  maker 0.0200% = 0.0002, taker 0.0500% = 0.0005
TradFi: https://www.binance.com/en/fee/tradFiFee
  maker 0.0000, taker 0.0400% = 0.0004
BNB 10% off exists on those tables; default bnb_discount=False.

Product class:
- usd_m_crypto: BTCUSDT, SOLUSDT, and any *USDT not in the tradfi set.
- tradfi: XAUUSDT and other TradFi-style books already in Themis.
  Prefixes XAU, XAG, SPY, QQQ go tradfi.
  SPYUSDT and QQQUSDT are Binance ETF perps (not ES / not NQ). They are
  classified tradfi by assumption because they sit on the TradFi-style
  books already in this harness, not because Binance labels them COMEX/CME.

Unknown symbols are classified by those suffix/prefix rules. This module
never silently emits a placeholder 0.0004.

next_open fills use taker on both sides. Named maker uses maker. Do not
average. No funding is modeled. Ask never charges these fees.
"""
from __future__ import annotations

from typing import Any

AS_OF_UTC = "2026-09-03"
USD_M_SOURCE = "https://www.binance.com/en/fee/futureFee"
TRADFI_SOURCE = "https://www.binance.com/en/fee/tradFiFee"
BNB_DISCOUNT_FACTOR = 0.9

# Regular / VIP0, no BNB. Fractions of price.
USD_M_MAKER = 0.0002
USD_M_TAKER = 0.0005
TRADFI_MAKER = 0.0
TRADFI_TAKER = 0.0004

# Exact books plus prefix stems. SPY/QQQ = ETF perps treated as tradfi.
TRADFI_SYMBOLS = frozenset({"XAUUSDT", "XAGUSDT", "SPYUSDT", "QQQUSDT"})
TRADFI_PREFIXES = ("XAU", "XAG", "SPY", "QQQ")
_QUOTE_SUFFIXES = ("USDT", "BUSD", "USDC", "USD")


class FeeError(ValueError):
    pass


def _norm_symbol(symbol: str | None) -> str:
    s = (symbol or "").strip().upper()
    if not s:
        raise FeeError("symbol is required to classify Binance fees")
    return s


def _base(symbol: str) -> str:
    s = _norm_symbol(symbol)
    for suf in _QUOTE_SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            return s[: -len(suf)]
    return s


def product_class(symbol: str) -> str:
    """Return usd_m_crypto or tradfi. Never a silent placeholder."""
    s = _norm_symbol(symbol)
    if s in TRADFI_SYMBOLS:
        return "tradfi"
    base = _base(s)
    if any(base == p or base.startswith(p) for p in TRADFI_PREFIXES):
        return "tradfi"
    return "usd_m_crypto"


def _norm_vip(vip: str) -> str:
    v = (vip or "regular").strip().lower().replace(" ", "")
    if v in ("regular", "vip0"):
        return "regular"
    raise FeeError(f"only Binance Regular/VIP0 is in this table; got vip={vip!r}")


def _applied_rate(maker: float, taker: float, fill: str, bnb_discount: bool) -> float:
    kind = (fill or "next_open").strip().lower()
    if kind == "maker":
        rate = maker
    else:
        # next_open, taker, and any other named fill: taker both sides. Do not average.
        rate = taker
    if bnb_discount:
        rate = round(rate * BNB_DISCOUNT_FACTOR, 8)
    return rate


def fee_schedule(
    symbol: str,
    *,
    vip: str = "regular",
    bnb_discount: bool = False,
    fill: str = "next_open",
) -> dict[str, Any]:
    """Venue fees for one symbol. YAML records this; it does not invent it."""
    product = product_class(symbol)
    vip_n = _norm_vip(vip)
    if product == "tradfi":
        maker, taker = TRADFI_MAKER, TRADFI_TAKER
        source_url = TRADFI_SOURCE
        product_note = (
            "Binance TradFi Futures Regular/VIP0. "
            "SPY/QQQ ETF perps classified tradfi by assumption."
        )
    else:
        maker, taker = USD_M_MAKER, USD_M_TAKER
        source_url = USD_M_SOURCE
        product_note = "Binance USD-M Futures Regular/VIP0."
    fill_s = fill or "next_open"
    commission = _applied_rate(maker, taker, fill_s, bool(bnb_discount))
    fill_note = (
        "maker fill uses maker."
        if (fill_s or "").strip().lower() == "maker"
        else "next_open fill uses taker both sides."
    )
    bnb_note = "BNB 10% off applied." if bnb_discount else "No BNB discount."
    notes = (
        f"{product_note} Published {AS_OF_UTC}. {fill_note} {bnb_note} "
        "No funding modeled. Ask does not apply this."
    )
    return {
        "product": product,
        "source_url": source_url,
        "as_of_utc": AS_OF_UTC,
        "vip": vip_n,
        "maker": maker,
        "taker": taker,
        "bnb_discount": bool(bnb_discount),
        "fill": fill_s,
        "commission_per_side": commission,
        "cost_unit": "fraction_of_price",
        "notes": notes,
    }


def costs_for_symbol(
    symbol: str,
    *,
    vip: str = "regular",
    bnb_discount: bool = False,
    fill: str = "next_open",
    slippage_ticks: int | float = 1,
    tick_size: float | None = None,
) -> dict[str, Any]:
    """Full strategy costs block: fee law plus slippage_ticks / tick_size."""
    block = dict(fee_schedule(symbol, vip=vip, bnb_discount=bnb_discount, fill=fill))
    block["slippage_ticks"] = slippage_ticks
    if tick_size is not None:
        block["tick_size"] = tick_size
    return block


def resolve_costs(spec: dict[str, Any], *, symbol: str | None = None) -> dict[str, Any]:
    """Use written spec costs, else freeze from fee_schedule. Never a constant 0.0004."""
    costs = dict(spec.get("costs") or {})
    if costs.get("commission_per_side") is not None:
        return costs
    inst = spec.get("instrument") or {}
    sym = symbol or inst.get("symbol")
    fill = (spec.get("rules") or {}).get("fill") or costs.get("fill") or "next_open"
    vip = costs.get("vip") or "regular"
    bnb = bool(costs.get("bnb_discount") or False)
    law = fee_schedule(sym, vip=vip, bnb_discount=bnb, fill=fill)
    out = {**law, **costs}
    out["commission_per_side"] = law["commission_per_side"]
    out.setdefault("product", law["product"])
    out.setdefault("source_url", law["source_url"])
    out.setdefault("as_of_utc", law["as_of_utc"])
    out.setdefault("maker", law["maker"])
    out.setdefault("taker", law["taker"])
    out.setdefault("cost_unit", law["cost_unit"])
    out.setdefault("notes", law["notes"])
    out.setdefault("fill", law["fill"])
    return out
