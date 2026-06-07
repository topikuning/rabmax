"""Pricing endpoints — resolve harga (resolver Tier 1-6) + manual override (Tier 6)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import current_year
from app.db.models import ManualPriceOverride, Project, User
from app.db.session import get_db
from app.services.parser import normalize_text
from app.services.pricing.resolver import resolve_price

router = APIRouter()


class ResolveRequest(BaseModel):
    nama_material: str
    satuan: str
    project_id: int | None = None
    kota_kabupaten_id: int | None = None
    provinsi_id: int | None = None
    tahun: int = Field(default_factory=current_year)
    discover: bool = False  # True → boleh trigger AI discovery (Tier 5)


async def _discovery_hook(db: AsyncSession, **kw) -> int:
    from app.services.pricing.discovery import discover_prices

    return await discover_prices(
        db, nama_material=kw["nama_material"], satuan=kw["satuan"],
        kota_id=kw.get("kota_id"), provinsi_id=kw.get("provinsi_id"), tahun=kw.get("tahun"),
    )


@router.post("/resolve")
async def resolve(
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    kota_id, prov_id, tahun = body.kota_kabupaten_id, body.provinsi_id, body.tahun
    if body.project_id:
        p = await db.get(Project, body.project_id)
        if p and (p.owner_id is None or p.owner_id == user.id):
            kota_id = kota_id or p.kota_kabupaten_id
            prov_id = prov_id or p.provinsi_id
            tahun = p.tahun_pricing or tahun
    result = await resolve_price(
        db, body.nama_material, body.satuan, kota_id, prov_id, tahun,
        user_id=user.id, discovery=_discovery_hook if body.discover else None,
    )
    return asdict(result)


class ManualCreate(BaseModel):
    nama_material: str = Field(..., max_length=300)
    satuan: str = Field(..., max_length=20)
    harga: float = Field(..., ge=0)
    source_label: str = Field(..., max_length=300)
    reason: str
    kota_kabupaten_id: int | None = None
    project_id: int | None = None
    source_url: str | None = None


class ManualResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nama_material: str
    satuan: str
    harga: float
    source_label: str
    reason: str
    kota_kabupaten_id: int | None


@router.get("/manual", response_model=list[ManualResponse])
async def list_manual(
    db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ManualPriceOverride]:
    rows = await db.execute(
        select(ManualPriceOverride).where(ManualPriceOverride.user_id == user.id)
        .order_by(ManualPriceOverride.created_at.desc())
    )
    return list(rows.scalars().all())


@router.post("/manual", response_model=ManualResponse, status_code=status.HTTP_201_CREATED)
async def create_manual(
    body: ManualCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ManualPriceOverride:
    row = ManualPriceOverride(
        user_id=user.id,
        nama_material=body.nama_material,
        norm_nama=normalize_text(body.nama_material),
        satuan=body.satuan,
        harga=body.harga,
        source_label=body.source_label,
        source_url=body.source_url,
        reason=body.reason,
        kota_kabupaten_id=body.kota_kabupaten_id,
        project_id=body.project_id,
    )
    db.add(row)
    await db.flush()
    await db.refresh(row)
    return row


@router.delete("/manual/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_manual(
    override_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    row = await db.get(ManualPriceOverride, override_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not found")
    await db.delete(row)
