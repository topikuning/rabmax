"""Admin endpoints (superuser) — seeding data master tanpa console.

- Stats jumlah AHSP / Bahan & Upah.
- Seed AHSP dari data bawaan (bundled di image) — sekali klik.
- Seed AHSP / Bahan & Upah dari file upload (JSON/JSONL/.gz).
"""

from __future__ import annotations

import gzip

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
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


# ===================== AI / Integrasi — tes & status =====================
@router.get("/ai/status")
async def ai_status() -> dict:
    """Status tiap AI provider (key ada? library terpasang? siap?)."""
    from app.ai.client import provider_status

    s = provider_status()
    return {"providers": list(s.values()), "any_configured": any(p["configured"] for p in s.values())}


class AITestRequest(BaseModel):
    provider: str = "claude"
    prompt: str = "Balas satu kata: OK"


@router.post("/ai/test")
async def ai_test(body: AITestRequest) -> dict:
    """Kirim prompt uji ke SATU provider (tanpa fallback). Return hasil/error+latency."""
    import time

    from app.ai.client import AIMessage, ai_client, provider_status

    st = provider_status().get(body.provider)
    if not st:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Provider tak dikenal: {body.provider}")
    if not st["configured"]:
        return {"ok": False, "provider": body.provider, "error": st["reason"], "latency_ms": 0}

    t0 = time.perf_counter()
    try:
        resp = await ai_client.complete(
            [AIMessage(role="user", content=body.prompt)],
            provider=body.provider, fallback=False, max_tokens=64,
        )
        return {
            "ok": True, "provider": resp.provider, "model": resp.model,
            "text": resp.text[:500],
            "input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens,
            "latency_ms": round((time.perf_counter() - t0) * 1000),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False, "provider": body.provider, "error": str(e)[:400],
            "latency_ms": round((time.perf_counter() - t0) * 1000),
        }


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)) -> dict:
    return {
        "ahsp_count": await count_ahsp(db),
        "bahan_upah_count": await count_bahan_upah(db),
        "bundled_ahsp_available": (settings.seed_data_path / BUNDLED_AHSP).exists(),
    }


@router.post("/derive-bahan-upah")
async def derive_bahan_upah(db: AsyncSession = Depends(get_db)) -> dict:
    """Turunkan master Bahan & Upah dari komponen AHSP (harga 0). Idempotent."""
    from scripts.seed_bahan_upah_from_ahsp import derive_from_ahsp

    return await derive_from_ahsp(db)


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
