"""Bahan & Upah catalogue endpoints — list, create, edit (manual)."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import BahanUpahCreate, BahanUpahResponse, BahanUpahUpdate
from app.db.models import BahanUpahItem
from app.db.session import get_db

router = APIRouter()


def _filtered(stmt, q, category, tier, provinsi, kota, source, tahun):
    if q:
        stmt = stmt.where(BahanUpahItem.nama.ilike(f"%{q.lower()}%"))
    if category:
        stmt = stmt.where(BahanUpahItem.category == category)
    if tier:
        stmt = stmt.where(BahanUpahItem.tier == tier)
    if provinsi:
        stmt = stmt.where(BahanUpahItem.provinsi == provinsi)
    if kota:
        stmt = stmt.where(BahanUpahItem.kota.ilike(f"%{kota.lower()}%"))
    if source:
        stmt = stmt.where(BahanUpahItem.source_label.ilike(f"%{source.lower()}%"))
    if tahun:
        stmt = stmt.where(BahanUpahItem.tahun == tahun)
    return stmt


@router.get("", response_model=list[BahanUpahResponse])
async def list_bahan_upah(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None, description="Search nama"),
    category: str | None = None,
    tier: str | None = None,
    provinsi: str | None = None,
    kota: str | None = None,
    source: str | None = None,
    tahun: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[BahanUpahItem]:
    stmt = _filtered(select(BahanUpahItem), q, category, tier, provinsi, kota, source, tahun)
    stmt = stmt.order_by(BahanUpahItem.nama).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/count")
async def count_bahan_upah(
    db: AsyncSession = Depends(get_db),
    q: str | None = None,
    category: str | None = None,
    tier: str | None = None,
    provinsi: str | None = None,
    kota: str | None = None,
    source: str | None = None,
    tahun: int | None = None,
) -> dict:
    """Total baris yang cocok filter (untuk paginasi server-side grid besar)."""
    stmt = _filtered(
        select(func.count(BahanUpahItem.id)), q, category, tier, provinsi, kota, source, tahun
    )
    return {"count": int((await db.execute(stmt)).scalar_one())}


@router.post("", response_model=BahanUpahResponse, status_code=status.HTTP_201_CREATED)
async def create_bahan_upah(
    payload: BahanUpahCreate,
    db: AsyncSession = Depends(get_db),
) -> BahanUpahItem:
    item = BahanUpahItem(**payload.model_dump(), ai_generated=False)
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


@router.patch("/{item_id}", response_model=BahanUpahResponse)
async def update_bahan_upah(
    item_id: int,
    payload: BahanUpahUpdate,
    db: AsyncSession = Depends(get_db),
) -> BahanUpahItem:
    item = await db.get(BahanUpahItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    # Diedit manusia → bukan murni AI lagi.
    item.ai_generated = False
    await db.flush()
    await db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bahan_upah(item_id: int, db: AsyncSession = Depends(get_db)) -> None:
    item = await db.get(BahanUpahItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    await db.delete(item)


@router.get("/{item_id}", response_model=BahanUpahResponse)
async def get_bahan_upah(
    item_id: int, db: AsyncSession = Depends(get_db)
) -> BahanUpahItem:
    item = await db.get(BahanUpahItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item
