"""Pricing endpoints — resolve harga (resolver Tier 1-6) + manual override (Tier 6)."""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import current_year
from app.db.models import (
    BahanUpahItem,
    ManualPriceOverride,
    PriceConsensus,
    PriceSnapshot,
    Project,
    User,
    Vendor,
)
from app.db.session import get_db
from app.services.parser import normalize_text
from app.services.pricing.resolver import resolve_price

router = APIRouter()


@router.get("/vendors")
async def list_vendors(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    q: str | None = None,
    active: bool | None = None,
    limit: int = 200,
    offset: int = 0,
) -> list[dict]:
    """Vendor hasil discovery (untuk audit reliabilitas sumber)."""
    stmt = select(Vendor)
    if q:
        stmt = stmt.where(Vendor.name.ilike(f"%{q.lower()}%") | Vendor.domain.ilike(f"%{q.lower()}%"))
    if active is not None:
        stmt = stmt.where(Vendor.is_active.is_(active))
    stmt = stmt.order_by(Vendor.reliability_score.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [{
        "id": v.id, "name": v.name, "domain": v.domain, "source_type": v.source_type,
        "reliability_score": float(v.reliability_score), "total_snapshots": v.total_snapshots,
        "successful_scrapes": v.successful_scrapes, "failed_scrapes": v.failed_scrapes,
        "is_active": v.is_active, "domain_verified": v.domain_verified,
    } for v in rows]


@router.get("/snapshots")
async def list_snapshots(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    q: str | None = None,
    kota_id: int | None = None,
    outlier: bool | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """PriceSnapshot hasil discovery — WAJIB ada source_url + page_quote (audit anti-halusinasi)."""
    stmt = select(PriceSnapshot, Vendor.name, Vendor.domain).join(
        Vendor, Vendor.id == PriceSnapshot.vendor_id
    )
    if q:
        stmt = stmt.where(PriceSnapshot.norm_nama.ilike(f"%{normalize_text(q)}%"))
    if kota_id:
        stmt = stmt.where(PriceSnapshot.vendor_kota_id == kota_id)
    if outlier is not None:
        stmt = stmt.where(PriceSnapshot.is_outlier.is_(outlier))
    stmt = stmt.order_by(PriceSnapshot.scraped_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).all()
    return [{
        "id": s.id, "nama_material": s.nama_material, "satuan": s.satuan, "merek": s.merek,
        "harga": float(s.harga), "harga_standar": float(s.harga_standar) if s.harga_standar else None,
        "vendor": vname, "vendor_domain": vdom, "source_url": s.source_url,
        "page_quote": s.page_quote, "discovered_via": s.discovered_via,
        "is_outlier": s.is_outlier, "confidence": float(s.confidence) if s.confidence else None,
        "tahun": s.tahun, "llm_provider": s.llm_provider,
    } for s, vname, vdom in rows]


@router.get("/consensus")
async def list_consensus(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
    q: str | None = None,
    kota_id: int | None = None,
    provinsi_id: int | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """PriceConsensus terhitung (median + sebaran per lokasi)."""
    stmt = select(PriceConsensus)
    if q:
        stmt = stmt.where(PriceConsensus.norm_nama.ilike(f"%{normalize_text(q)}%"))
    if kota_id:
        stmt = stmt.where(PriceConsensus.kota_kabupaten_id == kota_id)
    if provinsi_id:
        stmt = stmt.where(PriceConsensus.provinsi_id == provinsi_id)
    stmt = stmt.order_by(PriceConsensus.last_computed_at.desc()).limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return [{
        "id": c.id, "norm_nama": c.norm_nama, "satuan": c.satuan, "n_sources": c.n_sources,
        "median_price": float(c.median_price), "min_price": float(c.min_price) if c.min_price else None,
        "max_price": float(c.max_price) if c.max_price else None,
        "variance_pct": float(c.variance_pct) if c.variance_pct else None,
        "confidence": float(c.confidence) if c.confidence else None,
        "needs_review": c.needs_review, "tahun": c.tahun,
    } for c in rows]


@router.get("/data-stats")
async def data_stats(
    db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)
) -> dict:
    """Ringkasan jumlah data pricing-intelligence (untuk panel admin)."""
    async def _n(model) -> int:
        return int((await db.execute(select(func.count(model.id)))).scalar_one())

    # bahan_upah per kategori sumber (SSH per-kota vs nasional vs lain).
    ssh = int((await db.execute(select(func.count(BahanUpahItem.id)).where(
        BahanUpahItem.source_label.like("SSH %")))).scalar_one())
    nasional = int((await db.execute(select(func.count(BahanUpahItem.id)).where(
        BahanUpahItem.source_label.like("AHSP CK 2026%")))).scalar_one())
    n_kota = int((await db.execute(
        select(func.count(func.distinct(BahanUpahItem.kota_kabupaten_id))).where(
            BahanUpahItem.kota_kabupaten_id.is_not(None)))).scalar_one())
    return {
        "vendors": await _n(Vendor), "snapshots": await _n(PriceSnapshot),
        "consensus": await _n(PriceConsensus), "manual": await _n(ManualPriceOverride),
        "bahan_upah_total": await _n(BahanUpahItem),
        "bahan_upah_ssh": ssh, "bahan_upah_nasional": nasional, "kota_terisi": n_kota,
    }


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
