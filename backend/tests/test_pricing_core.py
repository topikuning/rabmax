"""Tests Pricing core (consensus, transport, umk) — pure, tanpa DB/network."""

from app.constants.regional_markup import get_default_regional_markup
from app.services.pricing.consensus import SnapshotInput, compute_consensus
from app.services.pricing.transport import default_markup, from_transport_rate
from app.services.pricing.umk import derive_upah_konstruksi, reconcile_upah


def _snaps(prices, rel=0.5, st="unknown"):
    return [SnapshotInput(p, rel, st) for p in prices]


def test_consensus_filters_outliers():
    # 4 harga rapat + 1 outlier ekstrem
    r = compute_consensus(_snaps([100, 102, 98, 101, 500]))
    assert len(r.outlier_indices) == 1
    assert 95 <= r.median_price <= 105


def test_consensus_needs_review_high_variance():
    r = compute_consensus(_snaps([100, 300]))
    assert r.needs_review  # n<2 setelah filter atau variance tinggi


def test_consensus_confidence_boost():
    r = compute_consensus(_snaps([100, 101, 99], rel=0.8, st="official_distributor"))
    assert r.n_sources == 3
    assert r.confidence >= 0.7  # +0.2(n>=3) +0.2(var<15) +0.2(rel) +0.1(official)


def test_transport_default_markup_papua_extreme():
    # Papua (92) base 0.45 × mult 1.1 default ≈ 0.495 → ~50%
    r = default_markup(1000000, "92")
    assert 0.45 <= r.markup_pct / 100 <= 0.55
    assert r.cost_per_unit > 400000


def test_transport_material_specific_multiplier():
    # baja.tulangan multiplier 1.5 > default 1.1
    baja = get_default_regional_markup("52", "baja.tulangan.ulir")
    generic = get_default_regional_markup("52", None)
    assert baja > generic


def test_transport_from_rate_heavy_material():
    # baja 7856 kg/m3 → pakai rate_per_ton
    cost = from_transport_rate(rate_per_ton=200000, rate_per_m3=None,
                               berat_jenis_kg_per_m3=7856, volume_unit=1.0)
    assert cost > 0  # 200000 * 7.856 ton


def test_umk_derive():
    u = derive_upah_konstruksi(2600000)  # /26 = 100000/hari pekerja
    assert u["pekerja"] == 100000
    assert u["mandor"] == 200000  # mult 2.0
    assert u["tukang"] > u["pekerja"]


def test_umk_floor_compliance():
    # pasar < UMK → pakai UMK (lantai)
    final, note = reconcile_upah(120000, 100000)
    assert final == 120000 and "umk_floor" in note
    # pasar > UMK → pakai pasar
    final2, _ = reconcile_upah(100000, 130000)
    assert final2 == 130000
