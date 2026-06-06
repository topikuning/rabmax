"""Profit analysis (Mode B): RAB terisi → cost real → profit margin."""

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ProfitAnalysis(Base):
    """Hasil analisa profit untuk Mode B."""

    __tablename__ = "profit_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )

    # Input nilai dari file RAB terisi (HPS)
    hps_total: Mapped[float] = mapped_column(Numeric(precision=18, scale=2))
    hps_total_incl_ppn: Mapped[float] = mapped_column(Numeric(precision=18, scale=2))

    # Hasil komputasi cost real
    estimated_cost_total: Mapped[float] = mapped_column(Numeric(precision=18, scale=2))
    estimated_cost_breakdown: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="Per kategori: {'bahan': X, 'upah': Y, 'alat': Z, 'overhead': W}",
    )

    # Profit
    gross_profit: Mapped[float] = mapped_column(Numeric(precision=18, scale=2))
    gross_profit_margin_pct: Mapped[float] = mapped_column(
        Numeric(precision=5, scale=2), comment="Profit / HPS × 100"
    )

    # Risk / safety net analysis
    risk_items: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="List items dengan margin tipis atau cost > HPS",
    )

    # Per paket breakdown
    per_paket_breakdown: Mapped[list] = mapped_column(
        JSON,
        default=list,
        comment="List dict per paket: {nama, hps, cost, profit, margin_pct}",
    )

    # Asumsi yang dipakai
    assumptions: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        comment="O&P rate, waste factor, overhead rate, tahun harga, dll",
    )

    notes: Mapped[str | None] = mapped_column(Text)
    ai_summary: Mapped[str | None] = mapped_column(
        Text, comment="AI-generated narrative summary"
    )

    confidence: Mapped[float] = mapped_column(
        Numeric(precision=4, scale=3),
        default=0.0,
        comment="0-1, % items dengan harga real ditemukan",
    )
    items_resolved: Mapped[int] = mapped_column(Integer, default=0)
    items_total: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship(  # noqa: F821
        back_populates="profit_analyses"
    )
