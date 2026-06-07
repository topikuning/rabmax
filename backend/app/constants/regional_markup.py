"""Default regional markup (fallback bila tak ada TransportRate). Benchmark dari
Jakarta; sistem kalibrasi ulang via scrape ekspedisi aktual."""

DEFAULT_REGIONAL_MARKUP = {
    "jabodetabek": 0.00, "jawa_barat_non_jabodetabek": 0.03, "jawa_tengah": 0.05,
    "jawa_timur": 0.07, "banten": 0.02, "di_yogyakarta": 0.06, "bali": 0.12,
    "ntb": 0.18, "ntt": 0.25, "sumatra_utara": 0.10, "sumatra_selatan": 0.12,
    "sumatra_barat": 0.13, "aceh": 0.18, "riau": 0.10, "jambi": 0.13,
    "bengkulu": 0.16, "lampung": 0.08, "kep_riau": 0.20, "kep_babel": 0.20,
    "kalimantan_barat": 0.18, "kalimantan_tengah": 0.20, "kalimantan_timur": 0.15,
    "kalimantan_selatan": 0.15, "kalimantan_utara": 0.25, "sulawesi_selatan": 0.15,
    "sulawesi_utara": 0.20, "sulawesi_tengah": 0.22, "sulawesi_tenggara": 0.22,
    "sulawesi_barat": 0.22, "gorontalo": 0.22, "maluku": 0.30, "maluku_utara": 0.32,
    "papua_barat": 0.40, "papua": 0.45, "papua_tengah": 0.45, "papua_pegunungan": 0.50,
    "papua_selatan": 0.42, "papua_barat_daya": 0.42,
}

# Markup per provinsi BPS kode → key DEFAULT_REGIONAL_MARKUP
PROVINSI_KODE_TO_MARKUP_KEY = {
    "11": "aceh", "12": "sumatra_utara", "13": "sumatra_barat", "14": "riau",
    "15": "jambi", "16": "sumatra_selatan", "17": "bengkulu", "18": "lampung",
    "19": "kep_babel", "21": "kep_riau", "31": "jabodetabek", "32": "jawa_barat_non_jabodetabek",
    "33": "jawa_tengah", "34": "di_yogyakarta", "35": "jawa_timur", "36": "banten",
    "51": "bali", "52": "ntb", "53": "ntt", "61": "kalimantan_barat",
    "62": "kalimantan_tengah", "63": "kalimantan_selatan", "64": "kalimantan_timur",
    "65": "kalimantan_utara", "71": "sulawesi_utara", "72": "sulawesi_tengah",
    "73": "sulawesi_selatan", "74": "sulawesi_tenggara", "75": "gorontalo",
    "76": "sulawesi_barat", "81": "maluku", "82": "maluku_utara", "91": "papua_barat",
    "92": "papua", "93": "papua_selatan", "94": "papua_tengah", "95": "papua_pegunungan",
    "96": "papua_barat_daya",
}

MATERIAL_MARKUP_MULTIPLIER = {
    "beton.semen": 1.2, "baja.tulangan": 1.5, "kayu.balok": 1.3, "pipa.pvc": 1.1,
    "keramik": 1.25, "cat": 1.0, "alat_listrik.kabel": 1.05, "sanitary": 1.2,
}


def get_default_regional_markup(provinsi_kode: str, material_category: str | None = None) -> float:
    key = PROVINSI_KODE_TO_MARKUP_KEY.get(provinsi_kode, "")
    base = DEFAULT_REGIONAL_MARKUP.get(key, 0.20)
    mult = 1.1
    if material_category:
        for cat_prefix, m in MATERIAL_MARKUP_MULTIPLIER.items():
            if material_category.startswith(cat_prefix):
                mult = m
                break
    return round(base * mult, 4)
