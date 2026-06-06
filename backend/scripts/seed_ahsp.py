"""Seed AHSP dari file JSON hasil ekstraksi AI.

Format file: lihat docs/SEED_FORMAT.md / docs/PROMPT_EKSTRAK_AHSP.md.
Idempotent: upsert by (kode, source); komponen lama diganti.

Jalankan:
    cd backend
    python -m scripts.seed_ahsp /path/ahsp_pupr_8_2023.json
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import delete, select

from app.db.models import (
    AHSPCode,
    AHSPComponent,
    AHSPConfidenceTier,
    AHSPSource,
    ComponentCategory,
)
from app.db.session import AsyncSessionLocal

_VALID_SOURCE = {e.value for e in AHSPSource}
_VALID_TIER = {e.value for e in AHSPConfidenceTier}
_VALID_KATEGORI = {e.value for e in ComponentCategory}


def _norm_kategori(v: str) -> str:
    s = (v or "").strip().lower()
    if s in _VALID_KATEGORI:
        return s
    if "tenaga" in s or s in {"oh", "tk"}:
        return "upah"
    if "alat" in s or "peralatan" in s:
        return "alat"
    return "bahan"


async def seed(path: str) -> None:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    meta = data.get("meta", {})
    source = str(meta.get("source", "custom"))
    if source not in _VALID_SOURCE:
        print(f"  ! source '{source}' tak dikenal → pakai 'custom'")
        source = "custom"
    version = meta.get("version")

    entries = data.get("ahsp", [])
    created = updated = comp_total = 0
    warnings: list[str] = []

    async with AsyncSessionLocal() as db:
        for entry in entries:
            kode = str(entry.get("kode", "")).strip()
            if not kode:
                warnings.append("AHSP tanpa kode dilewati")
                continue

            existing = (
                await db.execute(
                    select(AHSPCode).where(
                        AHSPCode.kode == kode, AHSPCode.source == source
                    )
                )
            ).scalar_one_or_none()

            if existing:
                ahsp = existing
                await db.execute(
                    delete(AHSPComponent).where(AHSPComponent.ahsp_id == ahsp.id)
                )
                updated += 1
            else:
                ahsp = AHSPCode(kode=kode, source=source)
                db.add(ahsp)
                created += 1

            ahsp.uraian = str(entry.get("uraian", "")).strip()
            ahsp.satuan = str(entry.get("satuan", "")).strip()
            ahsp.version = version
            ahsp.work_group = entry.get("work_group") or None
            tier = str(entry.get("confidence_tier", "single_source"))
            ahsp.confidence_tier = tier if tier in _VALID_TIER else "single_source"
            ahsp.notes = entry.get("notes")
            await db.flush()

            for i, c in enumerate(entry.get("components", [])):
                koef = c.get("koefisien")
                if koef is None:
                    warnings.append(f"{kode}: koefisien null pada '{c.get('nama_material')}' → 0")
                    koef = 0.0
                db.add(
                    AHSPComponent(
                        ahsp_id=ahsp.id,
                        kategori=_norm_kategori(c.get("kategori", "bahan")),
                        nama_material=str(c.get("nama_material", "")).strip(),
                        koefisien=float(koef),
                        satuan=str(c.get("satuan", "")).strip(),
                        formula_modifier=c.get("formula_modifier") or None,
                        urutan=int(c.get("urutan", i)),
                    )
                )
                comp_total += 1

        await db.commit()

    print(f"✓ AHSP seeded dari {path}")
    print(f"  source={source}  baru={created}  diperbarui={updated}  komponen={comp_total}")
    if warnings:
        print(f"  ⚠ {len(warnings)} peringatan:")
        for w in warnings[:20]:
            print(f"    - {w}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.seed_ahsp <file.json>")
        raise SystemExit(2)
    asyncio.run(seed(sys.argv[1]))


if __name__ == "__main__":
    main()
