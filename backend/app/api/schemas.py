"""Pydantic schemas untuk API I/O."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import ProjectMode, ProjectStatus


# === Projects ===


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    lokasi: str | None = None
    tahun_anggaran: int | None = Field(None, ge=2000, le=2100)
    target_value: float | None = Field(None, ge=0)
    mode: ProjectMode = ProjectMode.GENERATE
    notes: str | None = None


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
