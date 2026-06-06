"""Matcher rules — work-group classification, stopwords, weak overrides, kabel remap.

Di-port & dikembangkan dari skrip matcher sebelumnya. Lihat build.md "Known Issues":
- #4 WEAK matches: work group filter dulu, baru token.
- #5 Kabel NYY: per ukuran ke AHSP berbeda, JANGAN mass-map ke 1 kode.

Semua konstanta di sini bersifat data-driven supaya gampang di-extend saat
seeding AHSP (Session 4) tanpa ubah algoritma di `rule_matcher.py`.
"""

from __future__ import annotations

import re

# --- Stopwords Indonesia untuk tokenisasi uraian pekerjaan ---
# Kata yang tidak membedakan jenis pekerjaan (dibuang sebelum scoring).
STOPWORDS: frozenset[str] = frozenset(
    {
        "dan", "untuk", "dengan", "yang", "pada", "di", "ke", "dari", "atau",
        "per", "tiap", "setiap", "secara", "serta", "buah", "unit", "titik",
        "pekerjaan", "pek", "pemasangan", "pasang", "pemb", "pembuatan",
        "membuat", "pengadaan", "termasuk", "meliputi", "ukuran", "uk",
        "tebal", "tbl", "tb", "diameter", "dia", "tinggi", "lebar", "panjang",
        "jenis", "tipe", "type", "merk", "merek", "setara", "ex", "eks",
        "standar", "standard", "sni", "kualitas", "mutu", "warna", "finish",
        "lengkap", "beserta", "berikut", "accessories", "asesoris", "fitting",
    }
)

# Tokens dimensi/satuan yang DIPERTAHANKAN walau pendek (signifikan untuk match).
KEEP_SHORT_TOKENS: frozenset[str] = frozenset(
    {"k", "fc", "fy", "nyy", "nym", "nya", "pvc", "ppr", "gip", "bj", "wf"}
)

_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[./][a-z0-9]+)*")


def tokenize(norm_uraian: str) -> list[str]:
    """Tokenize teks ter-normalisasi menjadi token signifikan.

    Pertahankan token dimensi (angka, k-225, 3/4, m2) dan keyword teknis.
    Buang stopwords & token 1-huruf non-teknis.
    """
    raw = _TOKEN_RE.findall(norm_uraian.lower())
    out: list[str] = []
    for t in raw:
        if t in STOPWORDS:
            continue
        if len(t) == 1 and t not in KEEP_SHORT_TOKENS and not t.isdigit():
            continue
        out.append(t)
    return out


# --- Work group classification ---
# Urutan penting: pengecekan dari spesifik ke umum. Keyword pertama yang match
# menentukan work group. Ini filter utama anti "weak match" (Known Issue #4).
WORK_GROUP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "persiapan": (
        "bouwplank", "bowplank", "direksi keet", "direkskeet", "papan nama",
        "pengukuran", "mobilisasi", "demobilisasi", "pembersihan lapangan",
        "papan proyek", "k3", "sewa", "los kerja",
    ),
    "bongkaran": ("bongkar", "pembongkaran", "pembersihan existing"),
    "tanah": (
        "galian", "urugan", "urug", "timbunan", "pemadatan", "stripping",
        "buangan tanah", "pasir urug",
    ),
    "pondasi": (
        "pondasi", "batu kali", "aanstamping", "anstamping", "sumuran",
        "strauss", "bore pile", "borepile", "tiang pancang", "pancang",
        "footplat", "foot plat",
    ),
    "pembesian": (
        "pembesian", "besi beton", "tulangan", "baja tulangan", "wiremesh",
        "wire mesh", "besi polos", "besi ulir",
    ),
    "bekisting": ("bekisting", "begisting", "begesting", "formwork", "cetakan beton"),
    "beton": (
        "beton", "cor", "sloof", "kolom", "balok", "plat lantai", "ring balk",
        "ringbalk", "rabat", "lantai kerja", "k-", "k 225", "k225", "fc", "readymix",
        "ready mix", "beton bertulang", "kanstin beton", "leveling",
    ),
    "dinding": (
        "pasang bata", "batu bata", "bata merah", "batako", "bata ringan",
        "hebel", "dinding", "roster", "pasangan dinding",
    ),
    "plesteran": ("plester", "plesteran", "acian", "benangan", "sponengan", "kamprot"),
    "lantai": (
        "keramik", "granit", "homogeneous", "homogenous", "lantai", "ubin",
        "tegel", "screed", "plint", "tile", "marmer", "vinyl",
    ),
    "atap": (
        "atap", "genteng", "kuda-kuda", "kuda kuda", "gording", "reng", "usuk",
        "kasau", "baja ringan", "nok", "listplank", "lisplank", "talang jurai",
        "spandek", "spandeck", "zincalume", "alumunium foil", "aluminium foil",
    ),
    "plafon": (
        "plafon", "plafond", "langit-langit", "langit langit", "gypsum",
        "grc", "hollow", "rangka plafon",
    ),
    "kusen": (
        "kusen", "pintu", "jendela", "daun pintu", "daun jendela", "kaca",
        "engsel", "kunci", "grendel", "handle", "railing tangga", "boven",
    ),
    "sanitasi": (
        "closet", "kloset", "wastafel", "kran", "floor drain", "septictank",
        "septic tank", "bak kontrol", "bak mandi", "urinoir", "urinal",
        "sanitair", "jet washer", "shower", "wudhu",
    ),
    "plumbing": (
        "pipa", "pvc", "instalasi air", "talang", "ppr", "pipa gip", "valve",
        "stop kran", "pipa pralon", "air kotor", "air bersih", "drainase pipa",
    ),
    "listrik": (
        "kabel", "instalasi listrik", "lampu", "saklar", "sakelar",
        "stop kontak", "stopkontak", "mcb", "panel listrik", "grounding",
        "nyy", "nym", "nya", "armatur", "downlight", "fitting lampu",
    ),
    "drainase": (
        "saluran", "gorong-gorong", "gorong gorong", "drainase", "kanstin",
        "kansteen", "kanstein", "u-ditch", "uditch", "buis beton", "got",
    ),
    "halaman": (
        "paving", "paving block", "grass block", "pagar", "kanopi", "carport",
        "taman", "rumput",
    ),
    "pengecatan": (
        "cat", "pengecatan", "plamir", "plamur", "meni", "menie", "waterproofing",
        "waterproof", "coating", "politur", "duco",
    ),
    "baja": (
        "konstruksi baja", "rangka baja", "wf", "kanal", "cnp", "unp", "siku",
        "plat baja", "baut", "angkur",
    ),
}


def classify_work_group(norm_uraian: str) -> str | None:
    """Tentukan work group dari uraian ter-normalisasi.

    Return key work group, atau None jika tidak terklasifikasi.
    Strategi: hitung match keyword per group, pilih yang paling banyak/awal.
    """
    text = norm_uraian.lower()
    best_group: str | None = None
    best_score = 0
    for group, keywords in WORK_GROUP_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            best_group = group
    return best_group


# --- Weak override blocklist (Known Issue #4) ---
# Jika uraian item mengandung token kiri, kandidat AHSP yang mengandung token
# kanan DI-PENALTI berat (hampir dipastikan salah meski ada overlap token).
WEAK_OVERRIDES: tuple[tuple[str, str], ...] = (
    # "Beton mutu rendah" jangan ke "Pembesian Besi Beton"
    ("beton", "pembesian"),
    ("beton", "tulangan"),
    ("cor", "pembesian"),
    # Plesteran jangan ke pasangan bata, dan sebaliknya
    ("acian", "pasang bata"),
    ("plester", "pondasi"),
    # Cat jangan ke material yang dicat
    ("cat", "kusen"),
    ("cat", "plafon gypsum"),
    # Galian jangan ke urugan
    ("galian tanah", "urugan pasir"),
)

WEAK_OVERRIDE_PENALTY = 0.6


# --- Kabel NYY remap (Known Issue #5) ---
# Per ukuran kabel ke kode AHSP berbeda. JANGAN mass-map ke 1 kode.
# Kode mengikuti katalog Permen PUPR (5.1.1.1.x). Resolusi kode->ahsp_id
# dilakukan orchestrator dari kandidat DB. Lengkapi saat seeding (Session 4).
KABEL_NYY_REMAP: dict[str, str] = {
    "2x2.5": "5.1.1.1.18",
    "3x2.5": "5.1.1.1.20",
    "4x2.5": "5.1.1.1.22",
    "2x4": "5.1.1.1.24",
    "3x4": "5.1.1.1.26",
    "4x4": "5.1.1.1.28",
    "4x6": "5.1.1.1.30",
    "4x10": "5.1.1.1.32",
    "4x16": "5.1.1.1.34",
    "4x25": "5.1.1.1.36",
}

_KABEL_SIZE_RE = re.compile(r"(\d+)\s*x\s*([\d.,]+)")


def detect_kabel_nyy(norm_uraian: str) -> str | None:
    """Jika uraian adalah kabel NYY berukuran, return kode AHSP target.

    Return kode (str) atau None.
    """
    text = norm_uraian.lower()
    if "nyy" not in text and "kabel" not in text:
        return None
    if "nyy" not in text:
        return None
    m = _KABEL_SIZE_RE.search(text)
    if not m:
        return None
    size = f"{m.group(1)}x{m.group(2).replace(',', '.')}"
    return KABEL_NYY_REMAP.get(size)


def weak_override_penalty(item_uraian: str, cand_uraian: str) -> float:
    """Return faktor penalti (0-1, 1=no penalty) untuk pasangan weak override."""
    factor = 1.0
    for left, right in WEAK_OVERRIDES:
        # Item bertema `left`, tapi kandidat bertema `right` (mis. item "beton" vs
        # kandidat "pembesian besi beton") -> hampir pasti salah, kena penalti.
        if left in item_uraian and right in cand_uraian:
            factor *= 1.0 - WEAK_OVERRIDE_PENALTY
    return factor
