"""Seed AHSP dari file JSON / JSONL / .gz (hasil ekstraksi AI).

Format file: lihat docs/SEED_FORMAT.md / docs/PROMPT_EKSTRAK_AHSP.md.
- JSON  : {"meta": {...}, "ahsp": [ {item}, ... ]}
- JSONL : satu baris = satu item AHSP (baris meta/checkpoint/_part_end di-skip).
- .gz   : versi gzip dari salah satu di atas (mis. seed bawaan di seed_data/).

Idempotent: upsert by (kode, source); komponen lama diganti; kode kembar dalam satu
file otomatis di-suffix '#n' agar item beda tak saling timpa.

Inti `apply_ahsp(db, ...)` dipakai bersama oleh CLI ini dan endpoint admin API.

Jalankan (CLI):
    cd backend
    python -m scripts.seed_ahsp /path/ahsp.jsonl [source_override]
"""

from __future__ import annotations

import asyncio
import gzip
import json
import sys
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

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


def _clip(v: object, n: int) -> str:
    """Potong string ke panjang maks kolom (cegah StringDataRightTruncation)."""
    return str(v or "").strip()[:n]


def _norm_kategori(v: str) -> str:
    s = (v or "").strip().lower()
    if s in _VALID_KATEGORI:
        return s
    if "tenaga" in s or s in {"oh", "tk"}:
        return "upah"
    if "alat" in s or "peralatan" in s:
        return "alat"
    return "bahan"


def _read_text(path: str | Path) -> str:
    p = Path(path)
    if p.suffix.lower() == ".gz":
        return gzip.decompress(p.read_bytes()).decode("utf-8")
    return p.read_text(encoding="utf-8")


def parse_content(text: str) -> tuple[dict, list[dict]]:
    """Parse isi file (JSON atau JSONL) → (meta, list_item_ahsp)."""
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
        if "meta" in obj and "kode" not in obj:
            meta = obj["meta"]
            continue
        if any(k in obj for k in ("checkpoint", "_part_end", "_continue")) and "kode" not in obj:
            continue
        if "ahsp" in obj:
            items.extend(obj["ahsp"])
            continue
        if "kode" in obj:
            items.append(obj)
    return meta, items


def _load(path: str) -> tuple[dict, list[dict]]:
    return parse_content(_read_text(path))


async def apply_ahsp(
    db: AsyncSession,
    entries: list[dict],
    source: str,
    version: str | None = None,
) -> dict:
    """Upsert daftar item AHSP ke DB (dipakai CLI & API). Return ringkasan."""
    if source not in _VALID_SOURCE:
        source = "custom"
    created = updated = comp_total = renamed = 0
    warnings: list[str] = []
    seen_kode: dict[str, int] = {}

    for entry in entries:
        kode = str(entry.get("kode", "")).strip()
        if not kode:
            warnings.append("AHSP tanpa kode dilewati")
            continue
        seen_kode[kode] = seen_kode.get(kode, 0) + 1
        if seen_kode[kode] > 1:
            kode = f"{kode}#{seen_kode[kode]}"
            renamed += 1
        kode = _clip(kode, 50)  # kolom ahsp_codes.kode = String(50)

        existing = (
            await db.execute(
                select(AHSPCode).where(AHSPCode.kode == kode, AHSPCode.source == source)
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

        ahsp.uraian = str(entry.get("uraian", "")).strip()  # Text — tak dibatasi
        ahsp.satuan = _clip(entry.get("satuan", ""), 20)  # String(20)
        ahsp.version = _clip(entry.get("version") or version, 30) or None  # String(30)
        ahsp.work_group = _clip(entry.get("work_group"), 50) or None  # String(50)
        tier = str(entry.get("confidence_tier", "single_source"))
        ahsp.confidence_tier = tier if tier in _VALID_TIER else "single_source"
        extra = [f"{k}: {entry[k]}" for k in ("bidang", "divisi") if entry.get(k)]
        note = entry.get("notes")
        ahsp.notes = " | ".join([*extra, note]) if note else (" | ".join(extra) or None)
        await db.flush()

        for i, c in enumerate(entry.get("components", [])):
            koef = c.get("koefisien")
            if koef is None:
                koef = 0.0
            nama = str(c.get("nama_material", "")).strip()
            if len(nama) > 300:
                warnings.append(f"{kode}: nama_material {len(nama)} char (data janggal) → dipotong 300")
            db.add(
                AHSPComponent(
                    ahsp_id=ahsp.id,
                    kategori=_norm_kategori(c.get("kategori", "bahan")),
                    nama_material=nama[:300],  # String(300)
                    koefisien=float(koef),
                    satuan=_clip(c.get("satuan", ""), 20),  # String(20)
                    formula_modifier=_clip(c.get("formula_modifier"), 50) or None,  # String(50)
                    urutan=int(c.get("urutan", i)),
                )
            )
            comp_total += 1

    return {
        "source": source,
        "created": created,
        "updated": updated,
        "renamed_dupes": renamed,
        "components": comp_total,
        "warnings": warnings,
    }


async def count_ahsp(db: AsyncSession) -> int:
    return int((await db.execute(select(func.count(AHSPCode.id)))).scalar_one())


async def seed(path: str, source_override: str | None = None) -> dict:
    meta, entries = _load(path)
    source = source_override or str(meta.get("source", "custom"))
    async with AsyncSessionLocal() as db:
        summary = await apply_ahsp(db, entries, source, meta.get("version"))
        await db.commit()
    print(
        f"✓ AHSP seeded dari {path}\n"
        f"  source={summary['source']}  baru={summary['created']}  "
        f"diperbarui={summary['updated']}  komponen={summary['components']}  "
        f"kode_kembar_di-suffix={summary['renamed_dupes']}"
    )
    return summary


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.seed_ahsp <file.json|jsonl|gz> [source]")
        raise SystemExit(2)
    asyncio.run(seed(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))


if __name__ == "__main__":
    main()
