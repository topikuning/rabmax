"""Stage 6 — Transport markup (RABMAXPROMPT 4.8).

Pure helper (default regional markup) + dataclass hasil. Versi DB-aware (pakai
TransportRate aktual) menyusul setelah scraper transport jalan; sekarang fallback
ke default regional markup.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.constants.regional_markup import get_default_regional_markup


@dataclass
class TransportMarkupResult:
    cost_per_unit: float
    markup_pct: float
    method: str  # 'default_regional' | 'transport_rate'
    note: str = ""


def default_markup(
    harga_base: float,
    dest_provinsi_kode: str,
    material_category: str | None = None,
) -> TransportMarkupResult:
    """Markup berbasis default regional (fallback). harga_base dalam Rupiah."""
    pct = get_default_regional_markup(dest_provinsi_kode, material_category)
    cost = round(harga_base * pct, 2)
    return TransportMarkupResult(
        cost_per_unit=cost,
        markup_pct=round(pct * 100, 2),
        method="default_regional",
        note=f"Markup default {pct*100:.1f}% (prov {dest_provinsi_kode})",
    )


def from_transport_rate(
    rate_per_ton: float | None,
    rate_per_m3: float | None,
    berat_jenis_kg_per_m3: float | None,
    handling_surcharge_pct: float = 0.0,
    min_charge: float | None = None,
    volume_unit: float = 1.0,
) -> float:
    """Cost transport per satuan dari tarif aktual (RABMAXPROMPT 4.8 langkah 5).

    Material berat (≥500 kg/m3) → per ton; ringan → per m3. + handling. + min charge.
    """
    cost = 0.0
    bj = berat_jenis_kg_per_m3 or 0.0
    if bj >= 500 and rate_per_ton:
        ton = (bj / 1000.0) * volume_unit
        cost = rate_per_ton * ton
    elif rate_per_m3:
        cost = rate_per_m3 * volume_unit
    elif rate_per_ton and bj:
        cost = rate_per_ton * (bj / 1000.0) * volume_unit
    cost *= 1 + (handling_surcharge_pct or 0) / 100.0
    if min_charge:
        cost = max(cost, min_charge)
    return round(cost, 2)
