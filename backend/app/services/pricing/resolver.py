"""Stage 7 — Location-aware layered resolver (RABMAXPROMPT 4.2, Strategi B).

Tier 1 kota → 2 provinsi(+transport) → 3 tetangga(+transport) → 4 nasional(+markup)
→ 5 discovery → 6 manual → unresolved. Discovery di-inject (default: no-op) sampai
agent siap (butuh jaringan, final-verify di deploy).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    KotaKabupaten,
    ManualPriceOverride,
    PriceSnapshot,
    Provinsi,
    ProvinsiAdjacency,
    Vendor,
)
from app.services.parser import normalize_text
from app.services.pricing.consensus import SnapshotInput, compute_consensus
from app.services.pricing.transport import default_markup

CONF_KOTA = 0.7
CONF_PROVINSI = 0.7
CONF_TETANGGA = 0.6
MIN_SOURCES = 3

# Discovery hook: async (db, nama, satuan, kota, provinsi, tahun) -> jumlah snapshot baru.
DiscoveryFn = Callable[..., Awaitable[int]]


@dataclass
class PriceResolveResult:
    harga_final: float | None = None
    harga_base: float | None = None
    markup_transport: float = 0.0
    tier_used: str = "unresolved"
    confidence: float = 0.0
    n_sources: int = 0
    sources: list[str] = field(default_factory=list)
    warning_messages: list[str] = field(default_factory=list)
    audit: dict = field(default_factory=dict)


async def _consensus_for(
    db: AsyncSession, norm: str, satuan: str, tahun: int, *,
    kota_id: int | None = None, provinsi_id: int | None = None, nasional: bool = False,
):
    now = datetime.now(timezone.utc)
    stmt = (
        select(PriceSnapshot, Vendor.reliability_score, Vendor.source_type, Vendor.domain)
        .join(Vendor, Vendor.id == PriceSnapshot.vendor_id)
        .where(
            PriceSnapshot.norm_nama == norm,
            PriceSnapshot.satuan == satuan,
            PriceSnapshot.tahun == tahun,
            PriceSnapshot.is_outlier.is_(False),
            or_(PriceSnapshot.expires_at.is_(None), PriceSnapshot.expires_at >= now),
        )
    )
    if kota_id is not None:
        stmt = stmt.where(PriceSnapshot.vendor_kota_id == kota_id)
    elif provinsi_id is not None:
        stmt = stmt.where(PriceSnapshot.vendor_provinsi_id == provinsi_id)
    elif nasional:
        stmt = stmt.where(PriceSnapshot.delivery_scope == "nasional")

    rows = (await db.execute(stmt)).all()
    snaps = [SnapshotInput(float(s.harga_standar), float(rel or 0.5), st or "unknown") for s, rel, st, _ in rows]
    sources = [d for *_, d in rows]
    return compute_consensus(snaps), sources


async def resolve_price(
    db: AsyncSession,
    nama_material: str,
    satuan: str,
    project_kota_id: int | None,
    project_provinsi_id: int | None,
    tahun: int,
    user_id: int | None = None,
    discovery: DiscoveryFn | None = None,
    _recursed: bool = False,
) -> PriceResolveResult:
    norm = normalize_text(nama_material)

    # provinsi kode (untuk markup)
    prov_kode = None
    if project_provinsi_id:
        prov = await db.get(Provinsi, project_provinsi_id)
        prov_kode = prov.kode if prov else None

    # TIER 1 — kota
    if project_kota_id:
        c, src = await _consensus_for(db, norm, satuan, tahun, kota_id=project_kota_id)
        if c.n_sources >= MIN_SOURCES and c.confidence >= CONF_KOTA:
            return PriceResolveResult(
                harga_final=c.median_price, harga_base=c.median_price, tier_used="kota_lokal",
                confidence=c.confidence, n_sources=c.n_sources, sources=src,
                audit={"consensus": c.__dict__},
            )

    # TIER 2 — provinsi + transport
    if project_provinsi_id:
        c, src = await _consensus_for(db, norm, satuan, tahun, provinsi_id=project_provinsi_id)
        if c.n_sources >= MIN_SOURCES and c.confidence >= CONF_PROVINSI:
            mk = default_markup(c.median_price, prov_kode or "", None) if prov_kode else None
            cost = mk.cost_per_unit if mk else 0.0
            return PriceResolveResult(
                harga_final=round(c.median_price + cost, 2), harga_base=c.median_price,
                markup_transport=cost, tier_used="provinsi_lokal", confidence=c.confidence,
                n_sources=c.n_sources, sources=src,
                warning_messages=([mk.note] if mk else []), audit={"consensus": c.__dict__},
            )

    # TIER 3 — provinsi tetangga (priority) + transport
    if project_provinsi_id:
        neighbors = (await db.execute(
            select(ProvinsiAdjacency).where(ProvinsiAdjacency.provinsi_id == project_provinsi_id)
            .order_by(ProvinsiAdjacency.priority)
        )).scalars().all()
        for nb in neighbors:
            c, src = await _consensus_for(db, norm, satuan, tahun, provinsi_id=nb.neighbor_id)
            if c.n_sources >= MIN_SOURCES and c.confidence >= CONF_TETANGGA:
                nbp = await db.get(Provinsi, nb.neighbor_id)
                mk = default_markup(c.median_price, prov_kode or "", None) if prov_kode else None
                cost = mk.cost_per_unit if mk else 0.0
                return PriceResolveResult(
                    harga_final=round(c.median_price + cost, 2), harga_base=c.median_price,
                    markup_transport=cost, tier_used="provinsi_tetangga", confidence=c.confidence,
                    n_sources=c.n_sources, sources=src,
                    warning_messages=[f"Harga dari {nbp.nama_singkat if nbp else nb.neighbor_id} + transport"],
                    audit={"consensus": c.__dict__},
                )

    # TIER 4 — nasional + default regional markup
    c, src = await _consensus_for(db, norm, satuan, tahun, nasional=True)
    if c.n_sources >= MIN_SOURCES:
        mk = default_markup(c.median_price, prov_kode or "", None) if prov_kode else None
        cost = mk.cost_per_unit if mk else 0.0
        return PriceResolveResult(
            harga_final=round(c.median_price + cost, 2), harga_base=c.median_price,
            markup_transport=cost, tier_used="nasional_markup", confidence=c.confidence,
            n_sources=c.n_sources, sources=src,
            warning_messages=([mk.note] if mk else []), audit={"consensus": c.__dict__},
        )

    # TIER 5 — discovery (lokasi-biased), lalu recurse sekali
    if discovery and not _recursed:
        created = await discovery(
            db, nama_material=nama_material, satuan=satuan,
            kota_id=project_kota_id, provinsi_id=project_provinsi_id, tahun=tahun,
        )
        if created:
            return await resolve_price(
                db, nama_material, satuan, project_kota_id, project_provinsi_id,
                tahun, user_id, discovery, _recursed=True,
            )

    # TIER 6 — manual override
    if user_id:
        stmt = select(ManualPriceOverride).where(
            ManualPriceOverride.norm_nama == norm,
            ManualPriceOverride.satuan == satuan,
        )
        if project_kota_id:
            stmt = stmt.where(
                or_(ManualPriceOverride.kota_kabupaten_id == project_kota_id,
                    ManualPriceOverride.kota_kabupaten_id.is_(None))
            )
        m = (await db.execute(stmt.order_by(ManualPriceOverride.created_at.desc()))).scalars().first()
        if m:
            return PriceResolveResult(
                harga_final=float(m.harga), harga_base=float(m.harga), tier_used="manual",
                confidence=1.0, n_sources=1, sources=[m.source_label],
            )

    return PriceResolveResult(
        tier_used="unresolved",
        warning_messages=["Tidak ada harga dari semua tier. Discovery/manual diperlukan."],
    )
