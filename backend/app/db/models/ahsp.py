"""AHSP (Analisa Harga Satuan Pekerjaan) models — Permen PUPR catalogue."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
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


class AHSPSource(str, Enum):
    PERMEN_PUPR_28_2016 = "permen_pupr_28_2016"
    PERMEN_PUPR_8_2023 = "permen_pupr_8_2023"
    SE_DJBK_47_2026 = "se_djbk_47_2026"
    CUSTOM = "custom"


class AHSPConfidenceTier(str, Enum):
    CONSISTENT = "consistent"  # ada di 3+ source resmi
    SINGLE_SOURCE = "single_source"
    INCONSISTENT = "inconsistent"
    CUSTOM = "custom"


class ComponentCategory(str, Enum):
    UPAH = "upah"
    BAHAN = "bahan"
    ALAT = "alat"


class AHSPCode(Base):
    """Master AHSP catalogue."""

    __tablename__ = "ahsp_codes"
    __table_args__ = (
        Index("idx_ahsp_kode", "kode"),
        Index("idx_ahsp_work_group", "work_group"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    kode: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    uraian: Mapped[str] = mapped_column(Text, nullable=False)
    satuan: Mapped[str] = mapped_column(String(20), nullable=False)

    source: Mapped[AHSPSource] = mapped_column(String(50), nullable=False)
    version: Mapped[str | None] = mapped_column(String(30))
    confidence_tier: Mapped[AHSPConfidenceTier] = mapped_column(
        String(30), default=AHSPConfidenceTier.SINGLE_SOURCE
    )

    work_group: Mapped[str | None] = mapped_column(
        String(50),
        index=True,
        comment="Kategorisasi: galian, beton, pembesian, plesteran, etc.",
    )

    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    components: Mapped[list["AHSPComponent"]] = relationship(
        back_populates="ahsp", cascade="all, delete-orphan"
    )


class AHSPComponent(Base):
    """Komponen per AHSP: bahan/upah/alat dengan koefisien."""

    __tablename__ = "ahsp_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    ahsp_id: Mapped[int] = mapped_column(
        ForeignKey("ahsp_codes.id", ondelete="CASCADE"), nullable=False
    )
    kategori: Mapped[ComponentCategory] = mapped_column(String(20), nullable=False)
    nama_material: Mapped[str] = mapped_column(String(300), nullable=False)
    koefisien: Mapped[float] = mapped_column(Numeric(precision=18, scale=6), nullable=False)
    satuan: Mapped[str] = mapped_column(String(20), nullable=False)
    # Harga satuan nasional resmi (dari AHSP CK 2026) — baseline bila tak ada
    # override lokasi. None bila sumber tak menyertakan harga.
    harga_satuan: Mapped[float | None] = mapped_column(
        Numeric(precision=18, scale=2), nullable=True
    )
    formula_modifier: Mapped[str | None] = mapped_column(
        String(50),
        comment="Modifier seperti '/1400' untuk unit conversion. Stored as Excel formula suffix.",
    )

    # FK ke bahan_upah_items — optional, untuk autolinking
    bahan_upah_id: Mapped[int | None] = mapped_column(
        ForeignKey("bahan_upah_items.id", ondelete="SET NULL")
    )

    urutan: Mapped[int] = mapped_column(Integer, default=0)

    ahsp: Mapped["AHSPCode"] = relationship(back_populates="components")
    bahan_upah: Mapped["BahanUpahItem | None"] = relationship(  # noqa: F821
        back_populates="used_in_components"
    )
