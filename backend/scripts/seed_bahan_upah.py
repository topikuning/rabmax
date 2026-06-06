"""Seed harga Bahan & Upah dari file JSON (SSH provinsi / distributor).

Format: lihat docs/SEED_FORMAT.md. Idempotent: upsert by (nama, provinsi, tahun).

Jalankan:
    cd backend
    python -m scripts.seed_bahan_upah /path/ssh_mataram_2025.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select

from app.db.models import BahanUpahCategory, BahanUpahItem, SourceTier
from app.db.session import AsyncSessionLocal

_VALID_CAT = {e.value for e in BahanUpahCategory}
_VALID_TIER = {e.value for e in SourceTier}


async def seed(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    provinsi = meta.get("provinsi")
    kota = meta.get("kota")
    tahun = int(meta.get("tahun", 2025))
    source_label = meta.get("source_label", "seed")

    created = updated = 0
    async with AsyncSessionLocal() as db:
        for it in data.get("items", []):
            nama = str(it.get("nama", "")).strip()
            if not nama or it.get("harga") is None:
                continue
            i_prov = it.get("provinsi", provinsi)
            i_tahun = int(it.get("tahun", tahun))

            existing = (
                await db.execute(
                    select(BahanUpahItem).where(
                        BahanUpahItem.nama == nama,
                        BahanUpahItem.provinsi == i_prov,
                        BahanUpahItem.tahun == i_tahun,
                    )
                )
            ).scalar_one_or_none()

            cat = str(it.get("category", "bahan"))
            tier = str(it.get("tier", "D")).upper()
            row = existing or BahanUpahItem(nama=nama)
            row.satuan = str(it.get("satuan", "")).strip()
            row.harga = float(it["harga"])
            row.category = cat if cat in _VALID_CAT else "bahan"
            row.tier = tier if tier in _VALID_TIER else "D"
            row.tkdn_factor = float(it.get("tkdn_factor", 1.0))
            row.source_label = it.get("source_label", source_label)
            row.provinsi = i_prov
            row.kota = it.get("kota", kota)
            row.tahun = i_tahun
            aliases = it.get("aliases")
            row.aliases = json.dumps(aliases, ensure_ascii=False) if aliases else None
            row.notes = it.get("notes")
            if existing:
                updated += 1
            else:
                db.add(row)
                created += 1

        await db.commit()

    print(f"✓ Bahan & Upah seeded dari {path}: baru={created} diperbarui={updated}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.seed_bahan_upah <file.json>")
        raise SystemExit(2)
    asyncio.run(seed(sys.argv[1]))


if __name__ == "__main__":
    main()
