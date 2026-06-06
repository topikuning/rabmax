"""Seed harga Bahan & Upah dari file JSON/JSONL/.gz (SSH provinsi / distributor).

Format: lihat docs/SEED_FORMAT.md. Idempotent: upsert by (nama, provinsi, tahun).
Inti `apply_bahan_upah(db, ...)` dipakai bersama CLI & endpoint admin API.

Jalankan (CLI):
    cd backend
    python -m scripts.seed_bahan_upah /path/harga.jsonl
"""

from __future__ import annotations

import asyncio
import json
import sys

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BahanUpahCategory, BahanUpahItem, SourceTier
from app.db.session import AsyncSessionLocal
from scripts.seed_ahsp import _read_text

_VALID_CAT = {e.value for e in BahanUpahCategory}
_VALID_TIER = {e.value for e in SourceTier}


def parse_content(text: str) -> tuple[dict, list[dict]]:
    """Parse JSON {"meta","items"} atau JSONL (baris meta + item) → (meta, items)."""
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "items" in data:
            return data.get("meta", {}), list(data["items"])
        if isinstance(data, list):
            return {}, data
    except json.JSONDecodeError:
        pass
    meta: dict = {}
    items: list[dict] = []
    for raw in text.splitlines():
        raw = raw.strip().rstrip(",")
        if not raw or raw in "[]":
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if "meta" in obj and "nama" not in obj:
            meta = obj["meta"]
            continue
        if "nama" in obj:
            items.append(obj)
    return meta, items


async def apply_bahan_upah(db: AsyncSession, items: list[dict], meta: dict) -> dict:
    provinsi = meta.get("provinsi")
    kota = meta.get("kota")
    tahun = int(meta.get("tahun", 2025))
    source_label = meta.get("source_label", "seed")

    created = updated = 0
    for it in items:
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

    return {"created": created, "updated": updated}


async def count_bahan_upah(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(BahanUpahItem.id)))).scalar_one())


async def seed(path: str) -> dict:
    meta, items = parse_content(_read_text(path))
    async with AsyncSessionLocal() as db:
        summary = await apply_bahan_upah(db, items, meta)
        await db.commit()
    print(f"✓ Bahan & Upah seeded dari {path}: baru={summary['created']} diperbarui={summary['updated']}")
    return summary


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.seed_bahan_upah <file.json|jsonl|gz>")
        raise SystemExit(2)
    asyncio.run(seed(sys.argv[1]))


if __name__ == "__main__":
    main()
