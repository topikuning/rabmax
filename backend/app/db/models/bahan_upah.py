"""Bahan & Upah master data — SSH (provinsi/kota) + distributor publish prices."""

from datetime import datetime
from enum import Enum

from sqlalchemy import (
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class BahanUpahCategory(str, Enum):
    BAHAN = "bahan"
    UPAH = "upah"
    ALAT = "alat"


class SourceTier(str, Enum):
    A = "A"  # SSH resmi (SK Gubernur / Buku SH Kota/Kabupaten)
    B = "B"  # Distributor resmi (brand whitelist: Toto, Onda, Schneider, etc)
    C = "C"  # Marketplace/publikasi generic
    D = "D"  # Tanpa keterangan — perlu verifikasi


class BahanUpahItem(Base):
    """Master harga material/upah/alat."""

    __tablename__ = "bahan_upah_items"
    __table_args__ = (
        Index("idx_bu_nama", "nama"),
        Index("idx_bu_provinsi_tahun", "provinsi", "tahun"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    nama: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    satuan: Mapped[str] = mapped_column(String(20), nullable=False)
    harga: Mapped[float] = mapped_column(Numeric(precision=18, scale=2), nullable=False)

    category: Mapped[BahanUpahCategory] = mapped_column(String(20), nullable=False)
    tier: Mapped[SourceTier] = mapped_column(String(5), nullable=False)

    # TKDN factor 0-1
    tkdn_factor: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=4),
        default=1.0,
        comment="TKDN component 0-1 (1.0 = 100% lokal)",
    )

    # Sumber metadata
    source_label: Mapped[str] = mapped_column(
        String(300),
        comment="Citation jelas, e.g. 'SHS Kota Mataram 2025' atau 'Distributor: Toto Closet CW421J 2025'",
    )
    provinsi: Mapped[str | None] = mapped_column(String(50), index=True)
    kota: Mapped[str | None] = mapped_column(String(100), index=True)
    tahun: Mapped[int] = mapped_column(default=2025, index=True)

    # Aliasing — beberapa nama lain yang sama harga
    aliases: Mapped[str | None] = mapped_column(
        Text, comment="JSON array of alternative names"
    )

    notes: Mapped[str | None] = mapped_column(Text)

    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Reverse rel
    used_in_components: Mapped[list["AHSPComponent"]] = relationship(  # noqa: F821
        back_populates="bahan_upah"
    )
