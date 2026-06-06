"""Project model."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    PARSING = "parsing"
    MATCHING = "matching"
    BUILDING = "building"
    READY_FOR_REVIEW = "ready_for_review"
    FINALIZED = "finalized"
    FAILED = "failed"


class ProjectMode(str, Enum):
    GENERATE = "generate"  # Mode A: RAB kosong → output BOQ
    PROFIT_ANALYSIS = "profit_analysis"  # Mode B: RAB terisi → profit analysis


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Pemilik project (multi-user). Nullable utk kompatibilitas data lama.
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    lokasi: Mapped[str | None] = mapped_column(String(300))
    tahun_anggaran: Mapped[int | None]
    target_value: Mapped[float | None] = mapped_column(
        Numeric(precision=18, scale=2),
        comment="Target nilai penawaran lelang (incl PPN)",
    )
    mode: Mapped[ProjectMode] = mapped_column(
        String(30), default=ProjectMode.GENERATE, nullable=False
    )
    status: Mapped[ProjectStatus] = mapped_column(
        String(30), default=ProjectStatus.DRAFT, nullable=False
    )

    # File paths (relative to STORAGE_PATH)
    input_file_path: Mapped[str | None] = mapped_column(String(500))
    output_file_path: Mapped[str | None] = mapped_column(String(500))

    notes: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User | None"] = relationship(  # noqa: F821
        back_populates="projects"
    )
    paket_items: Mapped[list["PaketItem"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    item_matches: Mapped[list["ItemMatch"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
    profit_analyses: Mapped[list["ProfitAnalysis"]] = relationship(  # noqa: F821
        back_populates="project", cascade="all, delete-orphan"
    )
