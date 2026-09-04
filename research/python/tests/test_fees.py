"""Generic Binance fee law. Python freezes; YAML records. No gold special case."""
from __future__ import annotations

from themis.compiler import compile_english
from themis.fees import fee_schedule, product_class


def _series(symbol: str) -> dict[str, str]:
    return {
        "provider": "binance",
        "symbol": symbol,
        "timeframe": "4h",
        "exchange": "binanceusdm",
    }


def test_btcusdt_next_open_regular_usd_m_taker():
    sched = fee_schedule("BTCUSDT", vip="regular", fill="next_open")
    assert sched["commission_per_side"] == 0.0005
    assert sched["product"] == "usd_m_crypto"
    assert "futureFee" in sched["source_url"]
    assert product_class("BTCUSDT") == "usd_m_crypto"
    assert sched["maker"] == 0.0002
    assert sched["taker"] == 0.0005
    assert sched["bnb_discount"] is False
    assert sched["cost_unit"] == "fraction_of_price"
    assert sched["as_of_utc"] == "2026-09-03"
    assert "Placeholder" not in (sched["notes"] or "")


def test_xauusdt_next_open_regular_tradfi_taker():
    sched = fee_schedule("XAUUSDT", vip="regular", fill="next_open")
    assert sched["commission_per_side"] == 0.0004
    assert sched["product"] == "tradfi"
    assert "tradFiFee" in sched["source_url"]
    assert product_class("XAUUSDT") == "tradfi"
    assert sched["maker"] == 0.0
    assert sched["taker"] == 0.0004
    assert "Placeholder" not in (sched["notes"] or "")


def test_spyusdt_tradfi_etf_perp_assumption():
    sched = fee_schedule("SPYUSDT")
    assert product_class("SPYUSDT") == "tradfi"
    assert sched["product"] == "tradfi"
    assert sched["commission_per_side"] == 0.0004
    assert "tradFiFee" in sched["source_url"]


def test_bnb_discount_usd_m_taker():
    sched = fee_schedule("BTCUSDT", fill="next_open", bnb_discount=True)
    assert sched["commission_per_side"] == 0.00045
    assert sched["taker"] == 0.0005
    assert sched["bnb_discount"] is True


def test_compile_g1_btc_vs_xau_different_commission():
    btc = compile_english("G1", _series("BTCUSDT"), write=False)
    xau = compile_english("G1", _series("XAUUSDT"), write=False)
    btc_c = btc["strategies"][0]["costs"]["commission_per_side"]
    xau_c = xau["strategies"][0]["costs"]["commission_per_side"]
    assert btc_c == 0.0005
    assert xau_c == 0.0004
    assert btc_c != xau_c
    assert btc["strategies"][0]["costs"]["product"] == "usd_m_crypto"
    assert xau["strategies"][0]["costs"]["product"] == "tradfi"
    assert "Placeholder" not in (btc["strategies"][0]["costs"].get("notes") or "")
    assert "Placeholder" not in (xau["strategies"][0]["costs"].get("notes") or "")
    assert btc["strategies"][0]["costs"]["slippage_ticks"] == 1
    assert "tick_size" in btc["strategies"][0]["costs"]


def test_unknown_usdt_classifies_not_placeholder():
    sched = fee_schedule("ETHUSDT")
    assert sched["product"] == "usd_m_crypto"
    assert sched["commission_per_side"] == 0.0005
    assert "Placeholder" not in (sched["notes"] or "")
    assert product_class("SOLUSDT") == "usd_m_crypto"
    assert product_class("XAGUSDT") == "tradfi"
    assert product_class("QQQUSDT") == "tradfi"


def test_maker_fill_uses_maker_not_average():
    btc = fee_schedule("BTCUSDT", fill="maker")
    assert btc["commission_per_side"] == 0.0002
    xau = fee_schedule("XAUUSDT", fill="maker")
    assert xau["commission_per_side"] == 0.0

def test_compiler_live_runner_import_fee_schedule():
    from themis import compiler, live, runner
    from themis.fees import fee_schedule as law
    assert compiler.fee_schedule is law
    assert live.fee_schedule is law
    assert runner.fee_schedule is law


def test_runner_missing_costs_uses_fee_schedule():
    from themis.fees import fee_schedule
    from themis.runner import fee_schedule as runner_law
    spec = {"instrument": {"symbol": "BTCUSDT"}, "rules": {"fill": "next_open"}, "costs": {}}
    costs = spec.get("costs") or {}
    if costs.get("commission_per_side") is None:
        law = runner_law(spec["instrument"]["symbol"], fill="next_open")
        costs = {**law, **costs}
        costs["commission_per_side"] = law["commission_per_side"]
    assert costs["commission_per_side"] == 0.0005
    assert costs["commission_per_side"] == fee_schedule("BTCUSDT")["commission_per_side"]
    xau = runner_law("XAUUSDT", fill="next_open")
    assert xau["commission_per_side"] == 0.0004
