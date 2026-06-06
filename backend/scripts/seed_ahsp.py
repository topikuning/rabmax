"""Seed AHSP dari file JSON atau JSONL hasil ekstraksi AI.

Format file: lihat docs/SEED_FORMAT.md / docs/PROMPT_EKSTRAK_AHSP.md.
- JSON  : {"meta": {...}, "ahsp": [ {item}, ... ]}
- JSONL : satu baris = satu item AHSP (lebih tahan utk dokumen besar/ber-batch).
          Baris {"meta": {...}} atau {"checkpoint": {...}} otomatis di-skip sbg item.

Idempotent: upsert by (kode, source); komponen lama diganti.

Jalankan:
    cd backend
    python -m scripts.seed_ahsp /path/ahsp.jsonl [source_override]
    # contoh: python -m scripts.seed_ahsp ../se_djbk_47_cipta_karya.jsonl se_djbk_47_2026
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


def _load(path: str) -> tuple[dict, list[dict]]:
    """Baca file JSON atau JSONL → (meta, list_item_ahsp)."""
    text = Path(path).read_text(encoding="utf-8")
    # Coba sebagai satu dokumen JSON dulu.
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "ahsp" in data:
            return data.get("meta", {}), list(data["ahsp"])
        if isinstance(data, list):
            return {}, data
        if isinstance(data, dict) and "kode" in data:
            return {}, [data]
    except json.JSONDecodeError:
        pass
    # JSONL: satu objek per baris.
    meta: dict = {}
    items: list[dict] = []
    for ln, raw in enumerate(text.splitlines(), 1):
        raw = raw.strip().rstrip(",")
        if not raw or raw in "[]":
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            print(f"  ! baris {ln} bukan JSON valid, dilewati")
            continue
        if not isinstance(obj, dict):
            continue
        if "checkpoint" in obj or obj.get("type") == "checkpoint":
            continue
        if "meta" in obj and "kode" not in obj:
            meta = obj["meta"]
            continue
        if "ahsp" in obj:  # sebagian AI bungkus array dalam 1 baris
            items.extend(obj["ahsp"])
            continue
        if "kode" in obj:
            items.append(obj)
    return meta, items


async def seed(path: str, source_override: str | None = None) -> None:
    meta, entries = _load(path)
    source = source_override or str(meta.get("source", "custom"))
    if source not in _VALID_SOURCE:
        print(f"  ! source '{source}' tak dikenal → pakai 'custom'")
        source = "custom"
    version = meta.get("version")

    created = updated = comp_total = 0
    warnings: list[str] = []
    seen_kode: dict[str, int] = {}

    async with AsyncSessionLocal() as db:
        for entry in entries:
            kode = str(entry.get("kode", "")).strip()
            if not kode:
                warnings.append("AHSP tanpa kode dilewati")
                continue

            # Disambiguasi kode kembar dalam satu file (item beda berbagi kode) agar
            # tidak saling timpa saat upsert by (kode, source).
            seen_kode[kode] = seen_kode.get(kode, 0) + 1
            if seen_kode[kode] > 1:
                new_kode = f"{kode}#{seen_kode[kode]}"
                warnings.append(f"kode kembar '{kode}' → '{new_kode}' (item beda dipertahankan)")
                kode = new_kode

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
            ahsp.version = entry.get("version") or version
            ahsp.work_group = entry.get("work_group") or None
            tier = str(entry.get("confidence_tier", "single_source"))
            ahsp.confidence_tier = tier if tier in _VALID_TIER else "single_source"
            # Simpan bidang/divisi (jika ada) ke notes agar tak hilang.
            extra = [
                f"{k}: {entry[k]}"
                for k in ("bidang", "divisi")
                if entry.get(k)
            ]
            note = entry.get("notes")
            ahsp.notes = " | ".join([*extra, note]) if note else (" | ".join(extra) or None)
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
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.seed_ahsp <file.json|file.jsonl> [source]")
        raise SystemExit(2)
    src = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(seed(sys.argv[1], src))


if __name__ == "__main__":
    main()

