"""Pricing orchestrator — Stage 3 (source) + Stage 5 (calibrate) di level project.

Menghasilkan HSP final per item (sudah ter-kalibrasi ke target) dan menyimpannya
di ItemMatch.final_hsp + calibration_multiplier. Ini fondasi sebelum Stage 4
(Excel builder) yang akan menulis angka-angka ini ke workbook.
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ItemMatch,
    MatchType,
    PaketItem,
    Project,
    ProjectStatus,
)
from app.services.builder.source import price_match
from app.services.calibrator.calibrate import CalibrationItem, calibrate


@dataclass
class PricingSummary:
    project_id: int
    items_priced: int
    items_zero_price: int
    base_total: float
    calibrated_total: float
    multiplier: float
    target_value: float | None
    warnings: list[str]


async def price_and_calibrate_project(
    project_id: int,
    db: AsyncSession,
    use_llm: bool = True,
    op_rate: float = 0.10,
) -> PricingSummary:
    """Hitung HSP per item (source) lalu kalibrasi total ke target."""
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} tidak ditemukan")

    project.status = ProjectStatus.BUILDING
    await db.flush()

    # Pair (paket_item, match) untuk project.
    rows = list(
        (
            await db.execute(
                select(PaketItem, ItemMatch)
                .join(ItemMatch, ItemMatch.paket_item_id == PaketItem.id)
                .where(PaketItem.project_id == project_id)
            )
        ).all()
    )

    provinsi = None  # bisa diturunkan dari project.lokasi nanti
    tahun = project.tahun_anggaran

    # Cache HSP per (match_type, ahsp_id/lumpsum) supaya tak source ulang item identik.
    base_hsp_cache: dict[tuple, float] = {}
    items_priced = 0
    items_zero = 0
    calib_items: list[CalibrationItem] = []

    for paket_item, match in rows:
        cache_key = (
            str(match.match_type),
            match.ahsp_id,
            float(match.lumpsum_price) if match.lumpsum_price is not None else None,
        )
        if cache_key in base_hsp_cache:
            base = base_hsp_cache[cache_key]
            # Tetap set field di match (final_hsp/tkdn) dari cache base.
            match.final_hsp = base
        else:
            await price_match(match, db, provinsi, tahun, op_rate, use_llm)
            base = float(match.final_hsp or 0.0)
            base_hsp_cache[cache_key] = base

        if match.match_type in (MatchType.AHSP, MatchType.LUMPSUM) and base > 0:
            items_priced += 1
        else:
            items_zero += 1

        calib_items.append(
            CalibrationItem(
                item_id=match.id,
                volume=float(paket_item.volume),
                base_hsp=base,
            )
        )

    target = float(project.target_value) if project.target_value else 0.0
    calib = calibrate(calib_items, target_value=target)

    # Terapkan hasil kalibrasi ke match.
    calib_by_id = {ci.item_id: ci for ci in calib.items}
    for _paket_item, match in rows:
        ci = calib_by_id.get(match.id)
        if ci is None:
            continue
        match.final_hsp = ci.calibrated_hsp
        match.calibration_multiplier = ci.multiplier if calib.multiplier != 1.0 else None

    project.status = ProjectStatus.READY_FOR_REVIEW
    await db.flush()

    logger.info(
        f"Pricing project {project_id}: priced={items_priced} zero={items_zero} "
        f"base_total={calib.base_total:.0f} -> calibrated={calib.calibrated_total:.0f} "
        f"(×{calib.multiplier})"
    )

    return PricingSummary(
        project_id=project_id,
        items_priced=items_priced,
        items_zero_price=items_zero,
        base_total=round(calib.base_total, 2),
        calibrated_total=round(calib.calibrated_total, 2),
        multiplier=calib.multiplier,
        target_value=target or None,
        warnings=calib.warnings,
    )
