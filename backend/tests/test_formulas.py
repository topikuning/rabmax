"""Unit tests formula helpers (Known Issue #2 anti double-count)."""

from app.services.builder.formulas import (
    cell_ref,
    mul,
    quote_sheet,
    sum_of_rows,
    sum_range,
    weighted_rekap,
)


def test_quote_sheet():
    assert quote_sheet("RAB") == "RAB"
    assert quote_sheet("Resume Analisa") == "'Resume Analisa'"
    assert quote_sheet("Sub Resume EE") == "'Sub Resume EE'"


def test_cell_ref():
    assert cell_ref("Resume Analisa", "D5") == "'Resume Analisa'!D5"
    assert cell_ref("RAB", "J14") == "RAB!J14"


def test_mul():
    assert mul("G14", "E14") == "=G14*E14"


def test_sum_of_rows_no_double_count():
    # Grand = sum baris subtotal saja, BUKAN range item+subtotal.
    assert sum_of_rows("H", [41, 49, 67, 82]) == "=H41+H49+H67+H82"
    assert sum_of_rows("H", []) == "=0"


def test_sum_range():
    assert sum_range("J", 14, 1656) == "=SUM(J14:J1656)"


def test_weighted_rekap():
    assert weighted_rekap("G14", "G$38", "H14") == "=(G14/G$38)*H14"
