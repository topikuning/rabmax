"""Faktor kehilangan/waste material (SE DJBK 47/2026 Tabel A.3, sebagian)."""

FAKTOR_KEHILANGAN_JALAN_ASPAL = {
    "curah_lt_100m3": (1.053, 1.080), "curah_ge_100m3": (1.032, 1.068),
    "kemasan_lt_100m3": (1.022, 1.040), "kemasan_ge_100m3": (1.009, 1.033),
}
FAKTOR_KEHILANGAN_BETON_SEMEN = {
    "semen": (1.010, 1.020), "pasir_agregat_halus": (1.050, 1.100),
    "agregat_kasar": (1.050, 1.100), "superplasticizer": (1.010, 1.020),
}


def faktor_kehilangan_mid(tabel: dict, key: str) -> float:
    lo, hi = tabel.get(key, (1.0, 1.0))
    return round((lo + hi) / 2, 4)
