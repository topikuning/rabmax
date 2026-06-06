"""Bahan & Upah catalogue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import BahanUpahResponse
from app.db.models import BahanUpahItem
from app.db.session import get_db

router = APIRouter()


@router.get("", response_model=list[BahanUpahResponse])
async def list_bahan_upah(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(None, description="Search nama"),
    category: str | None = None,
    tier: str | None = None,
    provinsi: str | None = None,
    tahun: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[BahanUpahItem]:
    stmt = select(BahanUpahItem)
    if q:
        stmt = stmt.where(BahanUpahItem.nama.ilike(f"%{q.lower()}%"))
    if category:
        stmt = stmt.where(BahanUpahItem.category == category)
    if tier:
        stmt = stmt.where(BahanUpahItem.tier == tier)
    if provinsi:
        stmt = stmt.where(BahanUpahItem.provinsi == provinsi)
    if tahun:
        stmt = stmt.where(BahanUpahItem.tahun == tahun)
    stmt = stmt.order_by(BahanUpahItem.nama).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{item_id}", response_model=BahanUpahResponse)
async def get_bahan_upah(
    item_id: int, db: AsyncSession = Depends(get_db)
) -> BahanUpahItem:
    item = await db.get(BahanUpahItem, item_id)
    if not item:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item
