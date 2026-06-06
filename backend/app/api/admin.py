"""Admin endpoints (superuser) — seeding data master tanpa console.

- Stats jumlah AHSP / Bahan & Upah.
- Seed AHSP dari data bawaan (bundled di image) — sekali klik.
- Seed AHSP / Bahan & Upah dari file upload (JSON/JSONL/.gz).
"""

from __future__ import annotations

import gzip

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_superuser
from app.config import settings
from app.db.session import get_db
from scripts.seed_ahsp import apply_ahsp, count_ahsp
from scripts.seed_ahsp import parse_content as parse_ahsp
from scripts.seed_bahan_upah import (
    apply_bahan_upah,
    count_bahan_upah,
)
from scripts.seed_bahan_upah import (
    parse_content as parse_bu,
)

router = APIRouter(dependencies=[Depends(get_current_superuser)])

BUNDLED_AHSP = "ahsp_se_djbk_47_2026.jsonl.gz"


def _decode_upload(raw: bytes, filename: str) -> str:
    if filename.endswith(".gz"):
        return gzip.decompress(raw).decode("utf-8")
    return raw.decode("utf-8")


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)) -> dict:
    return {
        "ahsp_count": await count_ahsp(db),
        "bahan_upah_count": await count_bahan_upah(db),
        "bundled_ahsp_available": (settings.seed_data_path / BUNDLED_AHSP).exists(),
    }


@router.post("/seed/ahsp/bundled", status_code=status.HTTP_200_OK)
async def seed_ahsp_bundled(db: AsyncSession = Depends(get_db)) -> dict:
    """Seed AHSP dari data bawaan repo (SE DJBK 47/2026)."""
    path = settings.seed_data_path / BUNDLED_AHSP
    if not path.exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Data bawaan tidak ditemukan.")
    text = gzip.decompress(path.read_bytes()).decode("utf-8")
    meta, items = parse_ahsp(text)
    summary = await apply_ahsp(db, items, meta.get("source", "se_djbk_47_2026"), meta.get("version"))
    return {"items_in_file": len(items), **summary, "warnings": len(summary["warnings"])}


@router.post("/seed/ahsp", status_code=status.HTTP_200_OK)
async def seed_ahsp_upload(
    file: UploadFile = File(...),
    source: str = "custom",
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Seed AHSP dari file upload (JSON/JSONL/.gz)."""
    try:
        text = _decode_upload(await file.read(), file.filename or "")
        meta, items = parse_ahsp(text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Gagal baca file: {e}") from e
    summary = await apply_ahsp(db, items, meta.get("source", source), meta.get("version"))
    return {"items_in_file": len(items), **summary, "warnings": len(summary["warnings"])}


@router.post("/seed/bahan-upah", status_code=status.HTTP_200_OK)
async def seed_bahan_upah_upload(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Seed harga Bahan & Upah dari file upload (JSON/JSONL/.gz)."""
    try:
        text = _decode_upload(await file.read(), file.filename or "")
        meta, items = parse_bu(text)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"Gagal baca file: {e}") from e
    summary = await apply_bahan_upah(db, items, meta)
    return {"items_in_file": len(items), **summary}
