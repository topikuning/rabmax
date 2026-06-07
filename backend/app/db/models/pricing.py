"""Pricing Intelligence models (RABMAXPROMPT.md) — geografi, taxonomy, vendor
registry self-learning, price snapshots/consensus, transport, UMK, discovery audit.

Lihat docs/PRICING_SYSTEM.md untuk arsitektur. Semua harga WAJIB traceable
(source_url + page_quote) — anti-halusinasi.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ===================== Geografi =====================
class Provinsi(Base):
    __tablename__ = "provinsi"

    id: Mapped[int] = mapped_column(primary_key=True)
    kode: Mapped[str] = mapped_column(String(5), unique=True, index=True)  # BPS '52'
    nama: Mapped[str] = mapped_column(String(100))
    nama_singkat: Mapped[str | None] = mapped_column(String(20))
    ibukota: Mapped[str | None] = mapped_column(String(100))
    pulau: Mapped[str | None] = mapped_column(String(50))
    region: Mapped[str | None] = mapped_column(String(50))  # 'Indonesia Timur'
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))

    kota_list: Mapped[list[KotaKabupaten]] = relationship(back_populates="provinsi")


class KotaKabupaten(Base):
    __tablename__ = "kota_kabupaten"
    __table_args__ = (Index("idx_kotkab_provinsi", "provinsi_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provinsi_id: Mapped[int] = mapped_column(ForeignKey("provinsi.id", ondelete="CASCADE"))
    kode: Mapped[str] = mapped_column(String(10), unique=True, index=True)  # BPS '5271'
    nama: Mapped[str] = mapped_column(String(100))
    tipe: Mapped[str] = mapped_column(String(15))  # 'kota' | 'kabupaten'
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))

    provinsi: Mapped[Provinsi] = relationship(back_populates="kota_list")


class ProvinsiAdjacency(Base):
    """Mapping provinsi tetangga (fallback harga), user-editable."""

    __tablename__ = "provinsi_adjacency"
    __table_args__ = (UniqueConstraint("provinsi_id", "neighbor_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    provinsi_id: Mapped[int] = mapped_column(ForeignKey("provinsi.id", ondelete="CASCADE"))
    neighbor_id: Mapped[int] = mapped_column(ForeignKey("provinsi.id", ondelete="CASCADE"))
    travel_mode: Mapped[str] = mapped_column(String(15))  # land|ferry|sea|air
    priority: Mapped[int] = mapped_column(Integer, default=1)
    notes: Mapped[str | None] = mapped_column(Text)


# ===================== UMK =====================
class UMK(Base):
    __tablename__ = "umk"
    __table_args__ = (UniqueConstraint("kota_kabupaten_id", "tahun"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    kota_kabupaten_id: Mapped[int] = mapped_column(ForeignKey("kota_kabupaten.id", ondelete="CASCADE"))
    provinsi_id: Mapped[int] = mapped_column(ForeignKey("provinsi.id", ondelete="CASCADE"))
    tahun: Mapped[int] = mapped_column(Integer, index=True)

    umk: Mapped[float] = mapped_column(Numeric(18, 2))
    sk_nomor: Mapped[str | None] = mapped_column(String(100))
    sk_tanggal: Mapped[date | None] = mapped_column(Date)
    sumber_url: Mapped[str | None] = mapped_column(String(500))
    sumber_label: Mapped[str | None] = mapped_column(String(300))

    upah_pekerja_harian: Mapped[float | None] = mapped_column(Numeric(18, 2))
    upah_tukang_harian: Mapped[float | None] = mapped_column(Numeric(18, 2))
    upah_kepala_tukang_harian: Mapped[float | None] = mapped_column(Numeric(18, 2))
    upah_mandor_harian: Mapped[float | None] = mapped_column(Numeric(18, 2))

    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ===================== Taxonomy & Classification =====================
class ItemCategory(Base):
    __tablename__ = "item_categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("item_categories.id", ondelete="SET NULL"))
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)  # 'beton.semen.portland'
    name: Mapped[str] = mapped_column(String(200))
    level: Mapped[int] = mapped_column(Integer, default=0)
    standard_unit: Mapped[str | None] = mapped_column(String(20))
    typical_brands: Mapped[list | None] = mapped_column(JSON)
    typical_specs: Mapped[dict | None] = mapped_column(JSON)
    search_keywords: Mapped[list | None] = mapped_column(JSON)


class ItemClassification(Base):
    __tablename__ = "item_classifications"
    __table_args__ = (UniqueConstraint("norm_item_name", "satuan"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    norm_item_name: Mapped[str] = mapped_column(String(300), index=True)
    satuan: Mapped[str] = mapped_column(String(20))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("item_categories.id", ondelete="SET NULL"))
    detected_brand: Mapped[str | None] = mapped_column(String(100))
    detected_specs: Mapped[dict | None] = mapped_column(JSON)
    classified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    classifier_llm: Mapped[str | None] = mapped_column(String(50))
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.0)


# ===================== Vendor Registry =====================
class Vendor(Base):
    __tablename__ = "vendors"
    __table_args__ = (UniqueConstraint("domain"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    domain: Mapped[str] = mapped_column(String(200), index=True)
    canonical_url: Mapped[str | None] = mapped_column(String(500))
    source_type: Mapped[str] = mapped_column(String(40), default="unknown")

    reliability_score: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)
    domain_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    total_snapshots: Mapped[int] = mapped_column(Integer, default=0)
    successful_scrapes: Mapped[int] = mapped_column(Integer, default=0)
    failed_scrapes: Mapped[int] = mapped_column(Integer, default=0)
    last_validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    scraper_recipe: Mapped[dict | None] = mapped_column(JSON)
    recipe_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recipe_last_tested: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recipe_works: Mapped[bool] = mapped_column(Boolean, default=True)

    rate_limit_per_min: Mapped[int] = mapped_column(Integer, default=20)
    requires_javascript: Mapped[bool] = mapped_column(Boolean, default=False)
    robots_txt_allowed: Mapped[bool | None] = mapped_column(Boolean)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class VendorSpecialty(Base):
    __tablename__ = "vendor_specialties"
    __table_args__ = (UniqueConstraint("vendor_id", "category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"))
    category_id: Mapped[int] = mapped_column(ForeignKey("item_categories.id", ondelete="CASCADE"))
    items_priced: Mapped[int] = mapped_column(Integer, default=0)
    avg_confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.0)
    last_item_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class VendorServiceArea(Base):
    __tablename__ = "vendor_service_areas"
    __table_args__ = (
        Index("idx_vsa_vendor", "vendor_id"),
        Index("idx_vsa_kota", "kota_kabupaten_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"))
    scope: Mapped[str] = mapped_column(String(20))  # nasional|provinsi|kota|radius_km
    provinsi_id: Mapped[int | None] = mapped_column(ForeignKey("provinsi.id", ondelete="SET NULL"))
    kota_kabupaten_id: Mapped[int | None] = mapped_column(ForeignKey("kota_kabupaten.id", ondelete="SET NULL"))
    center_lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    center_lon: Mapped[float | None] = mapped_column(Numeric(9, 6))
    radius_km: Mapped[int | None] = mapped_column(Integer)
    delivery_free_threshold: Mapped[float | None] = mapped_column(Numeric(18, 2))
    delivery_base_cost: Mapped[float | None] = mapped_column(Numeric(18, 2))
    delivery_per_km_cost: Mapped[float | None] = mapped_column(Numeric(18, 2))
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.5)


# ===================== Price Snapshots & Consensus =====================
class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (
        Index("idx_snap_lookup", "norm_nama", "satuan", "tahun", "expires_at"),
        Index("idx_snap_vendor_cat", "vendor_id", "category_id"),
        Index("idx_snap_location", "vendor_kota_id", "vendor_provinsi_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendors.id", ondelete="CASCADE"))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("item_categories.id", ondelete="SET NULL"))
    classification_id: Mapped[int | None] = mapped_column(ForeignKey("item_classifications.id", ondelete="SET NULL"))

    nama_material: Mapped[str] = mapped_column(String(300))
    norm_nama: Mapped[str] = mapped_column(String(300), index=True)
    satuan: Mapped[str] = mapped_column(String(20))
    spesifikasi: Mapped[str | None] = mapped_column(Text)
    merek: Mapped[str | None] = mapped_column(String(100))

    harga: Mapped[float] = mapped_column(Numeric(18, 2))
    satuan_jual: Mapped[str | None] = mapped_column(String(50))
    konversi_factor: Mapped[float | None] = mapped_column(Numeric(8, 4))
    harga_standar: Mapped[float] = mapped_column(Numeric(18, 2))

    # Provenance — WAJIB
    source_url: Mapped[str] = mapped_column(String(1000))
    page_quote: Mapped[str] = mapped_column(Text)
    discovered_via: Mapped[str] = mapped_column(String(20))  # recipe_scrape|ai_discovery|lkpp_api|manual

    vendor_provinsi_id: Mapped[int | None] = mapped_column(ForeignKey("provinsi.id", ondelete="SET NULL"))
    vendor_kota_id: Mapped[int | None] = mapped_column(ForeignKey("kota_kabupaten.id", ondelete="SET NULL"))
    delivery_scope: Mapped[str | None] = mapped_column(String(100))

    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tahun: Mapped[int] = mapped_column(Integer, index=True)

    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.0)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False)
    variance_from_median: Mapped[float | None] = mapped_column(Numeric(8, 4))

    llm_provider: Mapped[str | None] = mapped_column(String(50))
    llm_model: Mapped[str | None] = mapped_column(String(100))
    llm_reasoning: Mapped[str | None] = mapped_column(Text)
    raw_response: Mapped[dict | None] = mapped_column(JSON)


class PriceConsensus(Base):
    __tablename__ = "price_consensus"
    __table_args__ = (
        UniqueConstraint("norm_nama", "satuan", "provinsi_id", "kota_kabupaten_id", "tahun"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    norm_nama: Mapped[str] = mapped_column(String(300), index=True)
    satuan: Mapped[str] = mapped_column(String(20))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("item_categories.id", ondelete="SET NULL"))
    provinsi_id: Mapped[int | None] = mapped_column(ForeignKey("provinsi.id", ondelete="SET NULL"))
    kota_kabupaten_id: Mapped[int | None] = mapped_column(ForeignKey("kota_kabupaten.id", ondelete="SET NULL"))
    tahun: Mapped[int] = mapped_column(Integer)

    n_sources: Mapped[int] = mapped_column(Integer, default=0)
    median_price: Mapped[float] = mapped_column(Numeric(18, 2))
    mean_price: Mapped[float | None] = mapped_column(Numeric(18, 2))
    min_price: Mapped[float | None] = mapped_column(Numeric(18, 2))
    max_price: Mapped[float | None] = mapped_column(Numeric(18, 2))
    std_deviation: Mapped[float | None] = mapped_column(Numeric(18, 2))
    variance_pct: Mapped[float | None] = mapped_column(Numeric(6, 2))

    confidence: Mapped[float] = mapped_column(Numeric(4, 3), default=0.0)
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False)
    contributing_snapshot_ids: Mapped[list | None] = mapped_column(JSON)
    last_computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ===================== Transport =====================
class TransportRate(Base):
    __tablename__ = "transport_rates"
    __table_args__ = (
        UniqueConstraint("origin_provinsi_id", "dest_provinsi_id", "transport_mode", "source_provider"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    origin_provinsi_id: Mapped[int] = mapped_column(ForeignKey("provinsi.id", ondelete="CASCADE"))
    origin_kota_id: Mapped[int | None] = mapped_column(ForeignKey("kota_kabupaten.id", ondelete="SET NULL"))
    dest_provinsi_id: Mapped[int] = mapped_column(ForeignKey("provinsi.id", ondelete="CASCADE"))
    dest_kota_id: Mapped[int | None] = mapped_column(ForeignKey("kota_kabupaten.id", ondelete="SET NULL"))

    transport_mode: Mapped[str] = mapped_column(String(30))
    rate_per_kg: Mapped[float | None] = mapped_column(Numeric(18, 4))
    rate_per_m3: Mapped[float | None] = mapped_column(Numeric(18, 2))
    rate_per_ton: Mapped[float | None] = mapped_column(Numeric(18, 2))
    rate_flat_per_truk: Mapped[float | None] = mapped_column(Numeric(18, 2))
    min_charge: Mapped[float | None] = mapped_column(Numeric(18, 2))
    transit_time_days: Mapped[int | None] = mapped_column(Integer)

    source_provider: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(String(500))
    last_scraped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class MaterialLogistics(Base):
    __tablename__ = "material_logistics"
    __table_args__ = (UniqueConstraint("category_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("item_categories.id", ondelete="CASCADE"))
    berat_jenis_kg_per_m3: Mapped[float | None] = mapped_column(Numeric(18, 2))
    is_fragile: Mapped[bool] = mapped_column(Boolean, default=False)
    requires_special_handling: Mapped[bool] = mapped_column(Boolean, default=False)
    is_oversized: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hazardous: Mapped[bool] = mapped_column(Boolean, default=False)
    preferred_mode: Mapped[str | None] = mapped_column(String(30))
    handling_surcharge_pct: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text)


# ===================== Discovery Audit & Manual Fallback =====================
class DiscoveryJob(Base):
    __tablename__ = "discovery_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    triggered_by: Mapped[str] = mapped_column(String(30))
    triggered_by_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))

    query_item: Mapped[str] = mapped_column(String(300))
    query_satuan: Mapped[str | None] = mapped_column(String(20))
    query_provinsi_id: Mapped[int | None] = mapped_column(ForeignKey("provinsi.id", ondelete="SET NULL"))
    query_kota_id: Mapped[int | None] = mapped_column(ForeignKey("kota_kabupaten.id", ondelete="SET NULL"))

    status: Mapped[str] = mapped_column(String(20), default="queued")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    llm_provider: Mapped[str | None] = mapped_column(String(50))
    llm_model: Mapped[str | None] = mapped_column(String(100))
    web_search_queries: Mapped[list | None] = mapped_column(JSON)
    total_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost_usd: Mapped[float] = mapped_column(Numeric(10, 4), default=0)

    vendors_discovered: Mapped[list | None] = mapped_column(JSON)
    snapshots_created: Mapped[list | None] = mapped_column(JSON)
    final_consensus_id: Mapped[int | None] = mapped_column(ForeignKey("price_consensus.id", ondelete="SET NULL"))
    error_log: Mapped[str | None] = mapped_column(Text)


class ManualPriceOverride(Base):
    """LAST RESORT — kalau AI discovery gagal total."""

    __tablename__ = "manual_price_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id", ondelete="SET NULL"))
    kota_kabupaten_id: Mapped[int | None] = mapped_column(ForeignKey("kota_kabupaten.id", ondelete="SET NULL"))

    nama_material: Mapped[str] = mapped_column(String(300))
    norm_nama: Mapped[str] = mapped_column(String(300), index=True)
    satuan: Mapped[str] = mapped_column(String(20))
    harga: Mapped[float] = mapped_column(Numeric(18, 2))

    source_label: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str | None] = mapped_column(String(500))
    bukti_dukung_file: Mapped[str | None] = mapped_column(String(500))

    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class PriceTier(str, Enum):
    KOTA_LOKAL = "kota_lokal"
    PROVINSI_LOKAL = "provinsi_lokal"
    PROVINSI_TETANGGA = "provinsi_tetangga"
    NASIONAL_MARKUP = "nasional_markup"
    DISCOVERY = "discovery"
    MANUAL = "manual"
    UNRESOLVED = "unresolved"
