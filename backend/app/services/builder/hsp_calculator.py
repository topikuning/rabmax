"""Hitung HSP (Harga Satuan Pekerjaan) dari komponen AHSP.

HSP = Σ(koefisien × harga × modifier) per kategori (bahan/upah/alat), lalu
ditambah Overhead & Profit (O&P). TKDN dihitung sebagai nilai tertimbang.

Pure python — decoupled dari ORM supaya unit-testable. Lihat Known Issue #1:
formula_modifier (mis. '/1400') JANGAN di-strip — ikut dihitung di sini.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# O&P default 10% (lazim untuk lelang pemerintah; bisa di-override).
DEFAULT_OP_RATE = 0.10

_MODIFIER_RE = re.compile(r"^\s*([*/])\s*([\d.]+)\s*$")


def apply_modifier(value: float, modifier: str | None) -> float:
    """Terapkan modifier formula seperti '/1400' atau '*1.05' ke value."""
    if not modifier:
        return value
    m = _MODIFIER_RE.match(modifier)
    if not m:
        return value
    op, num = m.group(1), float(m.group(2))
    if num == 0:
        return value
    return value / num if op == "/" else value * num


@dataclass
class PricedComponent:
    """Komponen AHSP yang sudah punya harga (hasil sourcing)."""

    kategori: str  # "bahan" | "upah" | "alat"
    nama: str
    koefisien: float
    harga: float
    satuan: str = ""
    formula_modifier: str | None = None
    tkdn_factor: float = 1.0

    @property
    def subtotal(self) -> float:
        return apply_modifier(self.koefisien * self.harga, self.formula_modifier)


@dataclass
class HSPResult:
    bahan: float = 0.0
    upah: float = 0.0
    alat: float = 0.0
    op_rate: float = DEFAULT_OP_RATE
    components: list[PricedComponent] = field(default_factory=list)

    @property
    def subtotal(self) -> float:
        """Jumlah sebelum O&P."""
        return self.bahan + self.upah + self.alat

    @property
    def op_value(self) -> float:
        return self.subtotal * self.op_rate

    @property
    def hsp(self) -> float:
        """HSP final termasuk O&P."""
        return self.subtotal + self.op_value

    @property
    def tkdn_factor(self) -> float:
        """TKDN tertimbang 0-1 berdasarkan nilai komponen."""
        total = sum(c.subtotal for c in self.components)
        if total <= 0:
            return 0.0
        local = sum(c.subtotal * c.tkdn_factor for c in self.components)
        return round(local / total, 4)

    def as_breakdown(self) -> dict:
        return {
            "bahan": round(self.bahan, 2),
            "upah": round(self.upah, 2),
            "alat": round(self.alat, 2),
            "subtotal": round(self.subtotal, 2),
            "op": round(self.op_value, 2),
            "hsp": round(self.hsp, 2),
            "tkdn_factor": self.tkdn_factor,
        }


def compute_hsp(
    components: list[PricedComponent],
    op_rate: float = DEFAULT_OP_RATE,
) -> HSPResult:
    """Hitung HSP dari daftar komponen ber-harga."""
    result = HSPResult(op_rate=op_rate, components=list(components))
    for c in components:
        sub = c.subtotal
        if c.kategori == "bahan":
            result.bahan += sub
        elif c.kategori == "upah":
            result.upah += sub
        elif c.kategori == "alat":
            result.alat += sub
        else:
            # kategori tak dikenal -> masuk bahan (konservatif)
            result.bahan += sub
    return result
