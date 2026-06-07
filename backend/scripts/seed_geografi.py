"""Seed geografi Indonesia (38 provinsi + 514 kota/kabupaten) + adjacency.

Sumber: backend/seed_data/geografi_id.json (ekstrak cahyadsn/wilayah, Kepmendagri 2022).
Idempotent: upsert by kode. Inti `apply_geografi(db)` dipakai CLI & auto-seed.

Jalankan:
    cd backend
    python -m scripts.seed_geografi
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import KotaKabupaten, Provinsi, ProvinsiAdjacency
from app.db.session import AsyncSessionLocal

# --- Pulau & region by province BPS kode ---
SINGKAT = {
    "11": "Aceh", "12": "Sumut", "13": "Sumbar", "14": "Riau", "15": "Jambi",
    "16": "Sumsel", "17": "Bengkulu", "18": "Lampung", "19": "Babel", "21": "Kepri",
    "31": "DKI", "32": "Jabar", "33": "Jateng", "34": "DIY", "35": "Jatim", "36": "Banten",
    "51": "Bali", "52": "NTB", "53": "NTT",
    "61": "Kalbar", "62": "Kalteng", "63": "Kalsel", "64": "Kaltim", "65": "Kaltara",
    "71": "Sulut", "72": "Sulteng", "73": "Sulsel", "74": "Sultra", "75": "Gorontalo", "76": "Sulbar",
    "81": "Maluku", "82": "Malut",
    "91": "Pabar", "92": "Papua", "93": "Papsel", "94": "Papteng", "95": "Papgung", "96": "PBD",
}


def pulau_of(kode: str) -> str:
    p = int(kode)
    if 11 <= p <= 21:
        return "Sumatra"
    if 31 <= p <= 36:
        return "Jawa"
    if 51 <= p <= 53:
        return "Bali-Nusra"
    if 61 <= p <= 65:
        return "Kalimantan"
    if 71 <= p <= 76:
        return "Sulawesi"
    if 81 <= p <= 82:
        return "Maluku"
    return "Papua"


def region_of(pulau: str) -> str:
    return {
        "Sumatra": "Indonesia Barat", "Jawa": "Indonesia Barat",
        "Bali-Nusra": "Indonesia Tengah", "Kalimantan": "Indonesia Tengah", "Sulawesi": "Indonesia Tengah",
        "Maluku": "Indonesia Timur", "Papua": "Indonesia Timur",
    }.get(pulau, "Indonesia Tengah")


# --- Default adjacency (kode → [(neighbor_kode, mode, priority)]). Admin-editable. ---
DEFAULT_ADJACENCY: dict[str, list[tuple[str, str, int]]] = {
    # Sumatra chain (land)
    "11": [("12", "land", 1)],
    "12": [("11", "land", 1), ("13", "land", 2), ("14", "land", 2), ("21", "sea", 3)],
    "13": [("12", "land", 1), ("14", "land", 2), ("15", "land", 2), ("17", "land", 3)],
    "14": [("12", "land", 1), ("13", "land", 2), ("15", "land", 2), ("21", "sea", 3)],
    "15": [("13", "land", 1), ("14", "land", 2), ("16", "land", 2), ("17", "land", 3)],
    "16": [("15", "land", 1), ("17", "land", 2), ("18", "land", 2), ("19", "sea", 3)],
    "17": [("13", "land", 1), ("15", "land", 2), ("16", "land", 2), ("18", "land", 3)],
    "18": [("16", "land", 1), ("17", "land", 2), ("36", "ferry", 3)],
    "19": [("16", "sea", 1), ("21", "sea", 2)],
    "21": [("14", "sea", 1), ("12", "sea", 2), ("19", "sea", 3)],
    # Jawa chain
    "31": [("32", "land", 1), ("36", "land", 1)],
    "32": [("31", "land", 1), ("36", "land", 1), ("33", "land", 2)],
    "33": [("32", "land", 1), ("34", "land", 1), ("35", "land", 2)],
    "34": [("33", "land", 1), ("35", "land", 2)],
    "35": [("33", "land", 1), ("34", "land", 2), ("51", "ferry", 3)],
    "36": [("31", "land", 1), ("32", "land", 1), ("18", "ferry", 3)],
    # Bali-Nusra
    "51": [("35", "ferry", 1), ("52", "sea", 2)],
    "52": [("51", "sea", 1), ("53", "sea", 2), ("35", "sea", 3), ("73", "sea", 4)],
    "53": [("52", "sea", 1), ("51", "sea", 2)],
    # Kalimantan
    "61": [("62", "land", 1), ("63", "land", 2)],
    "62": [("61", "land", 1), ("63", "land", 2), ("64", "land", 3)],
    "63": [("62", "land", 1), ("64", "land", 2), ("61", "land", 3)],
    "64": [("65", "land", 1), ("62", "land", 2), ("63", "land", 2)],
    "65": [("64", "land", 1)],
    # Sulawesi
    "71": [("75", "land", 1), ("72", "land", 2)],
    "72": [("75", "land", 1), ("73", "land", 2), ("74", "land", 2), ("76", "land", 2)],
    "73": [("76", "land", 1), ("74", "land", 2), ("72", "land", 2), ("52", "sea", 3)],
    "74": [("73", "land", 1), ("72", "land", 2)],
    "75": [("71", "land", 1), ("72", "land", 2)],
    "76": [("73", "land", 1), ("72", "land", 2)],
    # Maluku
    "81": [("82", "sea", 1), ("74", "sea", 2)],
    "82": [("81", "sea", 1), ("71", "sea", 2)],
    # Papua
    "91": [("96", "land", 1), ("94", "land", 2), ("82", "sea", 3)],
    "92": [("94", "land", 1), ("95", "land", 2), ("93", "land", 3)],
    "93": [("92", "land", 1), ("95", "land", 2)],
    "94": [("92", "land", 1), ("91", "land", 2), ("95", "land", 2)],
    "95": [("92", "land", 1), ("94", "land", 2), ("93", "land", 2)],
    "96": [("91", "land", 1)],
}


async def apply_geografi(db: AsyncSession) -> dict:
    data = json.loads((settings.seed_data_path / "geografi_id.json").read_text(encoding="utf-8"))

    prov_by_kode: dict[str, Provinsi] = {}
    prov_created = prov_updated = 0
    for p in data["provinsi"]:
        kode = p["kode"]
        existing = (await db.execute(select(Provinsi).where(Provinsi.kode == kode))).scalar_one_or_none()
        row = existing or Provinsi(kode=kode)
        row.nama = p["nama"]
        row.nama_singkat = SINGKAT.get(kode)
        row.ibukota = p.get("ibukota")
        row.pulau = pulau_of(kode)
        row.region = region_of(row.pulau)
        row.latitude = p.get("lat")
        row.longitude = p.get("lng")
        if existing:
            prov_updated += 1
        else:
            db.add(row)
            prov_created += 1
        await db.flush()
        prov_by_kode[kode] = row

    kota_created = kota_updated = 0
    for k in data["kota_kabupaten"]:
        prov = prov_by_kode.get(k["provinsi_kode"])
        if prov is None:
            continue
        existing = (await db.execute(select(KotaKabupaten).where(KotaKabupaten.kode == k["kode"]))).scalar_one_or_none()
        row = existing or KotaKabupaten(kode=k["kode"])
        row.provinsi_id = prov.id
        row.nama = k["nama"]
        row.tipe = k["tipe"]
        row.latitude = k.get("lat")
        row.longitude = k.get("lng")
        if existing:
            kota_updated += 1
        else:
            db.add(row)
            kota_created += 1

    # Adjacency (hanya bila tabel kosong — admin-editable setelahnya)
    adj_created = 0
    has_adj = (await db.execute(select(func.count(ProvinsiAdjacency.id)))).scalar_one()
    if not has_adj:
        for kode, neighbors in DEFAULT_ADJACENCY.items():
            src = prov_by_kode.get(kode)
            if not src:
                continue
            for nb_kode, mode, prio in neighbors:
                nb = prov_by_kode.get(nb_kode)
                if not nb:
                    continue
                db.add(ProvinsiAdjacency(provinsi_id=src.id, neighbor_id=nb.id, travel_mode=mode, priority=prio))
                adj_created += 1

    await db.flush()
    return {
        "provinsi": {"created": prov_created, "updated": prov_updated},
        "kota_kabupaten": {"created": kota_created, "updated": kota_updated},
        "adjacency_created": adj_created,
    }


async def seed() -> dict:
    async with AsyncSessionLocal() as db:
        summary = await apply_geografi(db)
        await db.commit()
    print(f"✓ Geografi seeded: {summary}")
    return summary


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
