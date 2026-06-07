"""Pydantic schemas untuk API I/O."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ProjectMode, ProjectStatus

# === Auth / Users ===


class UserCreate(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=200)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None
    is_active: bool
    is_superuser: bool
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# === Projects ===


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    lokasi: str | None = None
    tahun_anggaran: int | None = Field(None, ge=2000, le=2100)
    target_value: float | None = Field(None, ge=0)
    mode: ProjectMode = ProjectMode.GENERATE
    notes: str | None = None
    # Lokasi pricing (location-aware). kota_kabupaten_id sangat dianjurkan.
    kota_kabupaten_id: int | None = None
    tahun_pricing: int | None = Field(None, ge=2000, le=2100)


class ProjectUpdate(BaseModel):
    name: str | None = None
    lokasi: str | None = None
    tahun_anggaran: int | None = None
    target_value: float | None = None
    status: ProjectStatus | None = None
    notes: str | None = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    lokasi: str | None
    tahun_anggaran: int | None
    target_value: float | None
    mode: ProjectMode
    status: ProjectStatus
    input_file_path: str | None
    output_file_path: str | None
    notes: str | None
    kota_kabupaten_id: int | None = None
    provinsi_id: int | None = None
    tahun_pricing: int | None = None
    created_at: datetime
    updated_at: datetime


# === Parser ===


class ParseSummary(BaseModel):
    project_id: int
    paket_sheets: int
    aggregator_sheets: int
    items_total: int
    items_unique: int
    needs_ai_assist: list[str]
    warnings: list[str]


# === Items ===


class PaketItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sheet_name: str
    excel_row: int
    no_label: str | None
    uraian: str
    satuan: str
    volume: float
    parent_uraian: str | None


class ItemMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    paket_item_id: int
    match_type: str
    method: str
    ahsp_id: int | None
    lumpsum_price: float | None
    lumpsum_source: str | None
    final_hsp: float | None
    tkdn_factor: float | None
    confidence: float
    reviewed_by_user: bool


class ManualMatchUpdate(BaseModel):
    """User override match."""

    match_type: str
    ahsp_id: int | None = None
    lumpsum_price: float | None = None
    lumpsum_source: str | None = None
    tkdn_factor: float | None = None
    user_notes: str | None = None


# === AHSP ===


class AHSPResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kode: str
    uraian: str
    satuan: str
    source: str
    confidence_tier: str
    work_group: str | None


# === BahanUpah ===


class BahanUpahResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nama: str
    satuan: str
    harga: float
    category: str
    tier: str
    tkdn_factor: float
    source_label: str
    provinsi: str | None
    kota: str | None
    tahun: int
    ai_generated: bool


class BahanUpahCreate(BaseModel):
    nama: str = Field(..., min_length=1, max_length=300)
    satuan: str = Field(..., max_length=20)
    harga: float = Field(..., ge=0)
    category: str = "bahan"
    tier: str = "D"
    tkdn_factor: float = Field(1.0, ge=0, le=1)
    source_label: str = "manual"
    provinsi: str | None = None
    kota: str | None = None
    tahun: int = 2025


class BahanUpahUpdate(BaseModel):
    nama: str | None = None
    satuan: str | None = None
    harga: float | None = Field(None, ge=0)
    category: str | None = None
    tier: str | None = None
    tkdn_factor: float | None = Field(None, ge=0, le=1)
    source_label: str | None = None
    provinsi: str | None = None
    kota: str | None = None
    tahun: int | None = None


# === Profit Analysis ===


class ProfitAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    hps_total: float
    hps_total_incl_ppn: float
    estimated_cost_total: float
    estimated_cost_breakdown: dict
    gross_profit: float
    gross_profit_margin_pct: float
    risk_items: list
    per_paket_breakdown: list
    assumptions: dict
    confidence: float
    items_resolved: int
    items_total: int
    ai_summary: str | None
    created_at: datetime
