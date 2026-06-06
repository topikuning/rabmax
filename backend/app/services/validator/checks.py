"""Stage 6 — Validator: sanity check hasil generate.

Bagian `check_records` murni (testable). `check_workbook_formulas` membaca file
hasil untuk memastikan formula G/H/I benar-benar ter-inject.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from app.services.builder.excel_writer import PricedItemRecord
from app.services.parser.excel_parser import (
    ColumnMap,
    SheetLayout,
    analyze_sheet_layout,
    detect_header_row,
)

# Range SUM dalam formula, mis. =SUM(H13:H82) → tangkap baris awal/akhir.
_SUM_RANGE_RE = re.compile(r"SUM\(\s*[A-Z]+\$?(\d+)\s*:\s*[A-Z]+\$?(\d+)\s*\)", re.IGNORECASE)

# TKDN minimum lelang (build.md: 40-70% tergantung jenis proyek).
DEFAULT_TKDN_MIN = 0.40


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors


def check_records(
    records: list[PricedItemRecord],
    tkdn_min: float = DEFAULT_TKDN_MIN,
) -> ValidationReport:
    """Cek konsistensi data harga & TKDN sebelum/ sesudah build."""
    rep = ValidationReport()
    if not records:
        rep.errors.append("Tidak ada item untuk divalidasi.")
        return rep

    unpriced = [r for r in records if r.harga <= 0]
    if unpriced:
        rep.warnings.append(
            f"{len(unpriced)} item belum ber-harga (HSP=0). "
            "Seed AHSP/bahan_upah atau set lumpsum manual."
        )

    bad_tkdn = [r for r in records if not (0.0 <= r.tkdn <= 1.0)]
    if bad_tkdn:
        rep.errors.append(
            f"{len(bad_tkdn)} item punya TKDN di luar rentang 0-1 "
            "(Resume Analisa col E HARUS faktor 0-1, bukan tipe). "
            "Contoh: " + ", ".join(r.uraian[:30] for r in bad_tkdn[:3])
        )

    total = sum(r.harga * r.volume for r in records)
    priced = [r for r in records if r.harga > 0]
    weighted_tkdn = (
        sum(r.tkdn * r.harga * r.volume for r in priced) / total if total > 0 else 0.0
    )
    if priced and weighted_tkdn < tkdn_min:
        rep.warnings.append(
            f"TKDN proyek tertimbang {weighted_tkdn*100:.1f}% < minimum "
            f"{tkdn_min*100:.0f}%."
        )

    rep.stats = {
        "items_total": len(records),
        "items_priced": len(priced),
        "items_unpriced": len(unpriced),
        "grand_total": round(total, 2),
        "weighted_tkdn": round(weighted_tkdn, 4),
    }
    return rep


def check_workbook_formulas(
    output_path: Path | str,
    records: list[PricedItemRecord],
    col_map: ColumnMap | None = None,
) -> ValidationReport:
    """Pastikan tiap item punya formula G/H/I (Known Issue #9: no missing row)."""
    from openpyxl import load_workbook

    cm = col_map or ColumnMap()
    rep = ValidationReport()
    wb = load_workbook(Path(output_path))  # formula string, bukan data_only

    missing = 0
    for r in records:
        if r.sheet_name not in wb.sheetnames:
            rep.errors.append(f"Sheet hilang di output: {r.sheet_name}")
            continue
        ws = wb[r.sheet_name]
        h = ws[f"{cm.jumlah}{r.excel_row}"].value
        if not (isinstance(h, str) and h.startswith("=")):
            missing += 1
    if missing:
        rep.errors.append(f"{missing} item tanpa formula JUMLAH (col H).")

    rep.stats["formula_checked"] = len(records)
    rep.stats["formula_missing"] = missing
    return rep


def _rows_in_formula(formula: str, candidate_rows: set[int]) -> list[int]:
    """Baris dari `candidate_rows` yang tercakup dalam range SUM(...) di formula."""
    hit: list[int] = []
    for m in _SUM_RANGE_RE.finditer(formula):
        lo, hi = sorted((int(m.group(1)), int(m.group(2))))
        hit.extend(r for r in candidate_rows if lo <= r <= hi)
    return sorted(set(hit))


def check_double_count(ws, layout: SheetLayout, col_map: ColumnMap | None = None) -> ValidationReport:
    """Deteksi double-count dinamis (Known Issue #2) untuk SATU paket sheet.

    Bila formula di baris subtotal/total menjumlahkan range yang ikut mencakup
    baris subtotal lain → potensi double-count. Sepenuhnya berbasis struktur
    yang terdeteksi (RAB dinamis, tanpa nomor baris hardcode).
    """
    cm = col_map or ColumnMap()
    rep = ValidationReport()
    agg_rows = set(layout.subtotal_rows)
    if layout.total_row:
        agg_rows.add(layout.total_row)

    jumlah_col = ord(cm.jumlah) - 64
    for r in sorted(agg_rows):
        val = ws.cell(row=r, column=jumlah_col).value
        if not (isinstance(val, str) and val.startswith("=")):
            continue
        swallowed = _rows_in_formula(val, agg_rows - {r})
        if swallowed:
            rep.warnings.append(
                f"{ws.title}!baris {r}: SUM mencakup baris subtotal {swallowed} "
                "→ potensi double-count (Known Issue #2). "
                "Pakai penjumlahan baris subtotal saja (=H{a}+H{b}+...)."
            )
    rep.stats["agg_rows"] = sorted(agg_rows)
    return rep


def check_workbook_double_count(
    output_path: Path | str,
    aggregator_sheet_names: set[str] | None = None,
) -> ValidationReport:
    """Scan semua paket sheet di workbook hasil untuk potensi double-count."""
    from openpyxl import load_workbook

    skip = aggregator_sheet_names or {
        "REKAP", "RAB", "Sub Resume EE", "Bahan & Upah", "ANALISA", "Resume Analisa",
    }
    rep = ValidationReport()
    wb = load_workbook(Path(output_path))
    for sn in wb.sheetnames:
        if sn in skip:
            continue
        ws = wb[sn]
        hr = detect_header_row(ws)
        if hr is None:
            continue
        layout = analyze_sheet_layout(ws, hr)
        sub = check_double_count(ws, layout)
        rep.warnings.extend(sub.warnings)
    rep.stats["sheets_scanned"] = len(wb.sheetnames)
    return rep
