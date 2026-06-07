"""Turunkan master Bahan & Upah dari komponen AHSP (harga dikosongkan = 0).

Idemu: AHSP punya ribuan komponen (nama bahan/upah/alat). Buat item Bahan & Upah
untuk tiap material UNIK dengan harga 0 → katalog langsung berisi daftar yang
perlu diberi harga (lewat edit manual / AI / discovery).

Idempotent: skip material yang sudah ada (by nama). harga<=0 = "belum ada harga".
"""

from __future__ import annotations

import asyncio

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import current_year
from app.db.models import AHSPComponent, BahanUpahItem
from app.db.session import AsyncSessionLocal
from app.services.parser import normalize_text

_VALID_CAT = {"bahan", "upah", "alat"}


async def derive_from_ahsp(db: AsyncSession) -> dict:
    """Buat BahanUpahItem (harga 0) untuk tiap material unik di ahsp_components."""
    # Nama material yang sudah ada di master (normalized) → jangan duplikat.
    existing = {
        normalize_text(n)
        for (n,) in (await db.execute(select(BahanUpahItem.nama))).all()
    }

    # Material unik dari komponen AHSP: (norm) -> (nama, kategori, satuan)
    rows = (
        await db.execute(
            select(
                AHSPComponent.nama_material,
                AHSPComponent.kategori,
                AHSPComponent.satuan,
            )
        )
    ).all()

    seen: dict[str, tuple[str, str, str]] = {}
    for nama, kategori, satuan in rows:
        nama = (nama or "").strip()
        if not nama:
            continue
        norm = normalize_text(nama)
        if norm in existing or norm in seen:
            continue
        kat = kategori if kategori in _VALID_CAT else "bahan"
        seen[norm] = (nama[:300], kat, (satuan or "")[:20])

    created = 0
    yr = current_year()
    for nama, kat, satuan in seen.values():
        db.add(
            BahanUpahItem(
                nama=nama, satuan=satuan, harga=0, category=kat, tier="D",
                tkdn_factor=1.0, source_label="dari AHSP (belum ada harga)",
                tahun=yr, ai_generated=False,
            )
        )
        created += 1
    await db.flush()

    total = (await db.execute(select(func.count(BahanUpahItem.id)))).scalar_one()
    return {"created": created, "skipped_existing": len(rows) - created, "total_bahan_upah": total}


async def seed() -> dict:
    async with AsyncSessionLocal() as db:
        s = await derive_from_ahsp(db)
        await db.commit()
    print(f"✓ Bahan & Upah diturunkan dari AHSP: {s}")
    return s


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
