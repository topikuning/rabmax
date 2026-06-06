"""Helper pembuat formula Excel — pure string functions, unit-testable.

Dipisah supaya logika formula (yang rawan bug, lihat Known Issue #2/#6/#8) bisa
ditest tanpa openpyxl/DB.
"""

from __future__ import annotations

import re

_SAFE_SHEET = re.compile(r"^[A-Za-z0-9_]+$")


def quote_sheet(name: str) -> str:
    """Quote nama sheet bila mengandung spasi/karakter khusus (gaya Excel)."""
    if _SAFE_SHEET.match(name):
        return name
    # Excel: escape single quote jadi double single-quote, bungkus dengan '...'.
    return "'" + name.replace("'", "''") + "'"


def cell_ref(sheet: str, cell: str) -> str:
    """Referensi sel lintas-sheet, mis. 'Resume Analisa'!D5."""
    return f"{quote_sheet(sheet)}!{cell}"


def eq(expr: str) -> str:
    """Bungkus expr jadi formula Excel ('=...')."""
    return expr if expr.startswith("=") else f"={expr}"


def mul(cell_a: str, cell_b: str) -> str:
    """Formula perkalian dua sel, mis. =G14*E14."""
    return eq(f"{cell_a}*{cell_b}")


def sum_of_rows(col: str, rows: list[int]) -> str:
    """Jumlah sel SPESIFIK (bukan range) — fix double-count (Known Issue #2).

    Grand JUMLAH HALAMAN = sum baris subtotal saja, mis. =H41+H49+H67+H82.
    """
    if not rows:
        return "=0"
    return eq("+".join(f"{col}{r}" for r in rows))


def sum_range(col: str, start: int, end: int) -> str:
    """SUM range — pakai HANYA untuk daftar item flat tanpa subtotal di tengah."""
    return eq(f"SUM({col}{start}:{col}{end})")


def weighted_rekap(g_cell: str, g_total_cell: str, h_cell: str) -> str:
    """REKAP col I = (G/G$total)*H — bobot (Known Issue #8)."""
    return eq(f"({g_cell}/{g_total_cell})*{h_cell}")


def ppn(base_cell: str, rate: float = 0.11) -> str:
    """Formula PPN dari sel base."""
    return eq(f"{base_cell}*{rate}")
