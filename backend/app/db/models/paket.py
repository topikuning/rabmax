"""Per-project models: parsed items + their matches."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class MatchType(str, Enum):
    AHSP = "ahsp"
    LUMPSUM = "lumpsum"
    SECTION = "section"
    UNRESOLVED = "unresolved"


class MatchMethod(str, Enum):
    RULE_EXACT = "rule_exact"
    RULE_TOKEN = "rule_token"
    RULE_LOOKBACK = "rule_lookback"
    LLM_VERIFIED = "llm_verified"
    LLM_SUGGESTED = "llm_suggested"
    MANUAL = "manual"


class PaketItem(Base):
    """Setiap item dari file lelang kosong yang di-upload user.
    Item, satuan, volume adalah PAKEM — non-negotiable."""

    __tablename__ = "paket_items"
    __table_args__ = (
        Index("idx_paket_project_sheet", "project_id", "sheet_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    sheet_name: Mapped[str] = mapped_column(String(100), nullable=False)
    excel_row: Mapped[int] = mapped_column(Integer, nullable=False)
    no_label: Mapped[str | None] = mapped_column(String(30))  # col A: 1, 2, a, b, etc

    uraian: Mapped[str] = mapped_column(Text, nullable=False)
    satuan: Mapped[str] = mapped_column(String(30), nullable=False)
    volume: Mapped[float] = mapped_column(Numeric(precision=18, scale=4), nullable=False)

    # Untuk multi-row parent/sub pattern
    parent_uraian: Mapped[str | None] = mapped_column(
        Text,
        comment="Jika sub-row hanya nama lokasi, parent uraian adalah pekerjaan utamanya",
    )

    # Normalized untuk matching
    norm_uraian: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    norm_satuan: Mapped[str] = mapped_column(String(30), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="paket_items")  # noqa: F821
    match: Mapped["ItemMatch | None"] = relationship(
        back_populates="paket_item", uselist=False, cascade="all, delete-orphan"
    )


class ItemMatch(Base):
    """Hasil matching item → AHSP atau LUMPSUM. User bisa override manual."""

    __tablename__ = "item_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    paket_item_id: Mapped[int] = mapped_column(
        ForeignKey("paket_items.id", ondelete="CASCADE"), nullable=False, unique=True
    )

    match_type: Mapped[MatchType] = mapped_column(String(30), nullable=False)
    method: Mapped[MatchMethod] = mapped_column(String(30), nullable=False)

    # AHSP match
    ahsp_id: Mapped[int | None] = mapped_column(
        ForeignKey("ahsp_codes.id", ondelete="SET NULL")
    )

    # LUMPSUM match
    lumpsum_price: Mapped[float | None] = mapped_column(Numeric(precision=18, scale=2))
    lumpsum_source: Mapped[str | None] = mapped_column(String(300))

    # Common
    final_hsp: Mapped[float | None] = mapped_column(
        Numeric(precision=18, scale=2),
        comment="Final HSP terhitung (mungkin di-calibrate)",
    )
    tkdn_factor: Mapped[float | None] = mapped_column(
        Numeric(precision=5, scale=4)
    )

    # Ringkasan sumber harga (audit): mis. "SSH resmi kota ×5 · Baseline nasional ×8".
    price_source: Mapped[str | None] = mapped_column(
        String(300), comment="Ringkasan tier sumber harga komponen (untuk audit/Excel)"
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(precision=4, scale=3),
        default=0.0,
        comment="0-1, LLM confidence atau rule score",
    )

    reviewed_by_user: Mapped[bool] = mapped_column(Boolean, default=False)
    user_notes: Mapped[str | None] = mapped_column(Text)

    # Calibration metadata
    calibration_multiplier: Mapped[float | None] = mapped_column(
        Numeric(precision=8, scale=6),
        comment="Multiplier applied untuk hit target",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="item_matches")  # noqa: F821
    paket_item: Mapped["PaketItem"] = relationship(back_populates="match")
