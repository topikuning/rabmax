"""AHSP catalogue endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import AHSPResponse
from app.db.models import AHSPCode
from app.db.session import get_db

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
