"""Berat isi/jenis bahan T/m3 (SE DJBK 47/2026 Tabel A.2, sebagian)."""

BERAT_ISI_BAHAN = {
    "pvc_polyvinyl_chloride": (0.500, 1.200), "hdpe": (0.500, 1.000),
    "gip": (7.550, 8.450), "dcip": (7.500, 8.650), "kayu": (0.650, 0.950),
    "baja_tulangan": 7.856, "asphaltic_plug": (1.400, 1.600),
    "beton": 2.400, "pasir": 1.400, "semen": 1.250, "batu_pecah": 1.350,
}


def berat_jenis_mid(key: str) -> float | None:
    v = BERAT_ISI_BAHAN.get(key)
    if v is None:
        return None
    return round((v[0] + v[1]) / 2, 3) if isinstance(v, tuple) else v
