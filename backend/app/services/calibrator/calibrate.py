"""Stage 5 — Calibrator: sesuaikan total ke target nilai penawaran.

Strategi (Known Issue #11): uniform multiplier sebagai last resort, dengan audit
trail wajib `[×X.XXX target-calibrated]`. Band check 80-120% HPS (LKPP).

Pure python — input ringkas, testable tanpa DB.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# LKPP: penawaran valid dalam band 80-120% HPS.
BAND_LOW = 0.80
BAND_HIGH = 1.20
# Guard rail: multiplier ekstrem menandakan data salah, bukan sekadar kalibrasi.
MULTIPLIER_MIN = 0.5
MULTIPLIER_MAX = 2.0


@dataclass
class CalibrationItem:
    item_id: int
    volume: float
    base_hsp: float

    @property
    def base_total(self) -> float:
        return self.volume * self.base_hsp


@dataclass
class CalibratedItem:
    item_id: int
    volume: float
    base_hsp: float
    calibrated_hsp: float
    multiplier: float

    @property
    def calibrated_total(self) -> float:
        return self.volume * self.calibrated_hsp

    @property
    def audit_label(self) -> str:
        if abs(self.multiplier - 1.0) < 1e-9:
            return ""
        return f"[×{self.multiplier:.3f} target-calibrated]"


@dataclass
class CalibrationResult:
    base_total: float
    target_value: float
    multiplier: float
    calibrated_total: float
    items: list[CalibratedItem] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    clamped: bool = False

    @property
    def band_ratio_vs_target(self) -> float:
        if self.target_value <= 0:
            return 0.0
        return self.calibrated_total / self.target_value


def calibrate(
    items: list[CalibrationItem],
    target_value: float,
    hps_total: float | None = None,
) -> CalibrationResult:
    """Hitung uniform multiplier agar total mendekati target_value.

    `hps_total` (opsional): bila diberikan, cek band 80-120% HPS untuk target.
    """
    base_total = sum(it.base_total for it in items)
    result = CalibrationResult(
        base_total=base_total,
        target_value=target_value,
        multiplier=1.0,
        calibrated_total=base_total,
    )

    if base_total <= 0:
        result.warnings.append("Base total = 0; tidak bisa kalibrasi (cek harga/HSP).")
        return result
    if target_value <= 0:
        result.warnings.append("Target value tidak diset; lewati kalibrasi.")
        result.items = [
            CalibratedItem(it.item_id, it.volume, it.base_hsp, it.base_hsp, 1.0)
            for it in items
        ]
        return result

    multiplier = target_value / base_total

    if multiplier < MULTIPLIER_MIN or multiplier > MULTIPLIER_MAX:
        clamped_mult = max(MULTIPLIER_MIN, min(MULTIPLIER_MAX, multiplier))
        result.warnings.append(
            f"Multiplier {multiplier:.3f} di luar guard rail "
            f"[{MULTIPLIER_MIN}, {MULTIPLIER_MAX}]; di-clamp ke {clamped_mult:.3f}. "
            "Periksa harga / target — kemungkinan ada data anomali."
        )
        multiplier = clamped_mult
        result.clamped = True

    # Band check vs HPS (jika ada).
    if hps_total and hps_total > 0:
        ratio = target_value / hps_total
        if ratio < BAND_LOW or ratio > BAND_HIGH:
            result.warnings.append(
                f"Target {ratio*100:.1f}% HPS di luar band LKPP "
                f"{BAND_LOW*100:.0f}-{BAND_HIGH*100:.0f}%."
            )

    result.multiplier = round(multiplier, 6)
    result.items = [
        CalibratedItem(
            item_id=it.item_id,
            volume=it.volume,
            base_hsp=it.base_hsp,
            calibrated_hsp=round(it.base_hsp * multiplier, 2),
            multiplier=result.multiplier,
        )
        for it in items
    ]
    result.calibrated_total = sum(ci.calibrated_total for ci in result.items)
    return result
