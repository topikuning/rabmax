"""Unit tests HSP calculator (Known Issue #1: formula modifier dihitung)."""

from app.services.builder.hsp_calculator import (
    PricedComponent,
    apply_modifier,
    compute_hsp,
)


def test_apply_modifier_divisor():
    # Known Issue #1: '/1400' untuk unit conversion JANGAN di-strip.
    assert apply_modifier(2800.0, "/1400") == 2.0
    assert apply_modifier(100.0, "*1.05") == 105.0
    assert apply_modifier(50.0, None) == 50.0
    assert apply_modifier(50.0, "garbage") == 50.0


def test_compute_hsp_categories_and_op():
    comps = [
        PricedComponent("bahan", "semen", koefisien=2.0, harga=1000.0),  # 2000
        PricedComponent("upah", "tukang", koefisien=0.5, harga=100000.0),  # 50000
        PricedComponent("alat", "molen", koefisien=0.1, harga=50000.0),  # 5000
    ]
    res = compute_hsp(comps, op_rate=0.10)
    assert res.bahan == 2000.0
    assert res.upah == 50000.0
    assert res.alat == 5000.0
    assert res.subtotal == 57000.0
    assert res.op_value == 5700.0
    assert res.hsp == 62700.0


def test_tkdn_weighted():
    comps = [
        PricedComponent("bahan", "lokal", koefisien=1.0, harga=100.0, tkdn_factor=1.0),
        PricedComponent("bahan", "impor", koefisien=1.0, harga=100.0, tkdn_factor=0.0),
    ]
    res = compute_hsp(comps)
    # 100 lokal dari 200 total -> 0.5
    assert res.tkdn_factor == 0.5


def test_modifier_in_subtotal():
    comp = PricedComponent("bahan", "x", koefisien=1.0, harga=2800.0, formula_modifier="/1400")
    assert comp.subtotal == 2.0
