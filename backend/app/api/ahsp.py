"""AHSP catalogue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AHSPResponse
from app.db.models import AHSPCode
from app.db.session import get_db
from app.services.builder.hsp_calculator import compute_hsp
from app.services.builder.source import source_ahsp_components

router = APIRouter()


@router.get("", response_model=list[AHSPResponse])
async def list_ahsp(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None, description="Search by kode or uraian"),
    work_group: str | None = None,
    source: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AHSPCode]:
    """List/search AHSP codes."""
    stmt = select(AHSPCode)
    if q:
        like = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                AHSPCode.kode.ilike(like),
                AHSPCode.uraian.ilike(like),
            )
        )
    if work_group:
        stmt = stmt.where(AHSPCode.work_group == work_group)
    if source:
        stmt = stmt.where(AHSPCode.source == source)
    stmt = stmt.order_by(AHSPCode.kode).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{ahsp_id}", response_model=AHSPResponse)
async def get_ahsp(ahsp_id: int, db: AsyncSession = Depends(get_db)) -> AHSPCode:
    a = await db.get(AHSPCode, ahsp_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AHSP not found")
    return a


@router.get("/{ahsp_id}/detail")
async def get_ahsp_detail(
    ahsp_id: int,
    op_rate: float = 0.10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Rincian AHSP: komponen (bahan/upah/alat) + harga dari DB + perhitungan HSP.

    Harga diambil dari master Bahan & Upah (tanpa LLM). Komponen tanpa harga →
    harga 0 dan ditandai (perlu seed Bahan & Upah).
    """
    a = await db.get(AHSPCode, ahsp_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AHSP not found")

    return await _build_detail(a, db, op_rate, use_llm=False)


@router.post("/{ahsp_id}/source-prices")
async def source_ahsp_prices(
    ahsp_id: int,
    op_rate: float = 0.10,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Estimasi harga via AI untuk komponen yang belum ada harga (disimpan ke
    master Bahan & Upah dengan flag ai_generated=True), lalu kembalikan detail.
    Butuh API key AI ter-set di server."""
    a = await db.get(AHSPCode, ahsp_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AHSP not found")
    # use_llm=True → cari & cache harga material yang belum ada.
    await source_ahsp_components(a, db, use_llm=True)
    return await _build_detail(a, db, op_rate, use_llm=False)


async def _build_detail(
    a: AHSPCode, db: AsyncSession, op_rate: float, use_llm: bool
) -> dict:
    priced = await source_ahsp_components(a, db, use_llm=use_llm)
    result = compute_hsp(priced, op_rate=op_rate)

    components = [
        {
            "kategori": c.kategori,
            "nama_material": c.nama,
            "koefisien": round(c.koefisien, 6),
            "satuan": c.satuan,
            "harga": round(c.harga, 2),
            "subtotal": round(c.subtotal, 2),
            "tkdn_factor": c.tkdn_factor,
            "harga_tersedia": c.harga > 0,
        }
        for c in priced
    ]
    missing = sum(1 for c in priced if c.harga <= 0)

    return {
        "id": a.id,
        "kode": a.kode,
        "uraian": a.uraian,
        "satuan": a.satuan,
        "source": str(a.source),
        "work_group": a.work_group,
        "confidence_tier": str(a.confidence_tier),
        "notes": a.notes,
        "components": components,
        "components_total": len(priced),
        "components_missing_price": missing,
        "hsp": result.as_breakdown(),
    }
