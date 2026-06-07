"""Stage 3 — UMK → upah konstruksi (RABMAXPROMPT 4.9).

UMK = LANTAI upah. Upah harian = UMK/26 × multiplier posisi. Pure → testable.
"""

from __future__ import annotations

from app.constants.upah_multiplier import UPAH_KONSTRUKSI_MULTIPLIER

_HARI_KERJA = 26


def derive_upah_konstruksi(umk: float) -> dict[str, float]:
    """Hitung upah harian per posisi dari UMK bulanan."""
    daily = umk / _HARI_KERJA
    return {
        "pekerja": round(daily * UPAH_KONSTRUKSI_MULTIPLIER["pekerja"], 2),
        "tukang": round(daily * UPAH_KONSTRUKSI_MULTIPLIER["tukang_batu"], 2),
        "kepala_tukang": round(daily * UPAH_KONSTRUKSI_MULTIPLIER["kepala_tukang"], 2),
        "mandor": round(daily * UPAH_KONSTRUKSI_MULTIPLIER["mandor"], 2),
    }


def reconcile_upah(umk_derived: float, market_discovery: float | None) -> tuple[float, str]:
    """UMK = lantai. Pasar boleh lebih tinggi, tidak boleh lebih rendah.

    Return (upah_final, catatan).
    """
    if market_discovery is None:
        return umk_derived, "umk_floor"
    if market_discovery >= umk_derived:
        note = "market"
        if umk_derived > 0 and (market_discovery - umk_derived) / umk_derived > 0.30:
            note = "market_review (>30% di atas UMK)"
        return market_discovery, note
    return umk_derived, "umk_floor (pasar < UMK)"
