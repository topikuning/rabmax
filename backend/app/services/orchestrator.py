"""End-to-end orchestrator — generate_boq: chain parse→match→price→build Excel.

Mengasumsikan upload/parse sudah jalan (paket_items terisi). Bila match/harga
belum ada, generate tetap menghasilkan workbook yang valid secara struktur
(harga 0 untuk item belum ter-source) — supaya tak gagal total tanpa seed data.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import (
    AHSPCode,
    ItemMatch,
    MatchType,
    PaketItem,
    Project,
    ProjectStatus,
)
from app.services.builder.excel_writer import PricedItemRecord, generate_workbook


@dataclass
class GenerateResult:
    project_id: int
    output_file_path: str
    resume_rows: int
    items_written: int
    items_total: int
    items_unpriced: int


def _sumber_label(match: ItemMatch, ahsp: AHSPCode | None) -> str:
    parts: list[str] = []
    if match.match_type == MatchType.AHSP and ahsp is not None:
        parts.append(str(ahsp.source))
    elif match.match_type == MatchType.LUMPSUM:
        parts.append(match.lumpsum_source or "lumpsum")
    if match.calibration_multiplier:
        parts.append(f"[×{float(match.calibration_multiplier):.3f} target-calibrated]")
    return " ".join(parts) or "-"


async def _build_records(project_id: int, db: AsyncSession) -> list[PricedItemRecord]:
    rows = list(
        (
            await db.execute(
                select(PaketItem, ItemMatch)
                .join(ItemMatch, ItemMatch.paket_item_id == PaketItem.id)
                .where(PaketItem.project_id == project_id)
            )
        ).all()
    )
    # Cache AHSP lookups.
    ahsp_cache: dict[int, AHSPCode | None] = {}
    records: list[PricedItemRecord] = []
    for pi, match in rows:
        ahsp = None
        if match.ahsp_id:
            if match.ahsp_id not in ahsp_cache:
                ahsp_cache[match.ahsp_id] = await db.get(AHSPCode, match.ahsp_id)
            ahsp = ahsp_cache[match.ahsp_id]
        kode = ahsp.kode if ahsp else ("LUMPSUM" if match.match_type == MatchType.LUMPSUM else "-")
        tier = str(ahsp.confidence_tier) if ahsp else "-"
        records.append(
            PricedItemRecord(
                sheet_name=pi.sheet_name,
                excel_row=pi.excel_row,
                norm_uraian=pi.norm_uraian,
                norm_satuan=pi.norm_satuan,
                uraian=pi.uraian,
                satuan=pi.satuan,
                volume=float(pi.volume),
                harga=float(match.final_hsp) if match.final_hsp is not None else 0.0,
                tkdn=float(match.tkdn_factor) if match.tkdn_factor is not None else 0.0,
                tipe=str(match.match_type),
                kode=kode,
                sumber=_sumber_label(match, ahsp),
                tier=tier,
            )
        )
    return records


async def generate_boq(project_id: int, db: AsyncSession) -> GenerateResult:
    """Tulis workbook BOQ ke storage/outputs dan set output_file_path."""
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} tidak ditemukan")
    if not project.input_file_path:
        raise ValueError("Project belum punya file input. Upload dulu.")

    input_path = settings.storage_path / project.input_file_path
    if not Path(input_path).exists():
        raise ValueError(f"File input tidak ditemukan: {input_path}")

    project.status = ProjectStatus.BUILDING
    await db.flush()

    records = await _build_records(project_id, db)
    if not records:
        project.status = ProjectStatus.FAILED
        await db.flush()
        raise ValueError("Tidak ada item/match. Jalankan parse + match dulu.")

    out_name = f"BOQ_{project_id}_{Path(project.input_file_path).stem}.xlsx"
    out_path = settings.output_path / out_name

    summary = generate_workbook(input_path, out_path, records)

    rel = str(out_path.relative_to(settings.storage_path))
    project.output_file_path = rel
    project.status = ProjectStatus.FINALIZED
    await db.flush()

    unpriced = sum(1 for r in records if r.harga <= 0)
    logger.info(
        f"generate_boq project {project_id} -> {rel} "
        f"(written={summary['items_written']}/{len(records)}, unpriced={unpriced})"
    )
    return GenerateResult(
        project_id=project_id,
        output_file_path=rel,
        resume_rows=summary["resume_rows"],
        items_written=summary["items_written"],
        items_total=len(records),
        items_unpriced=unpriced,
    )
