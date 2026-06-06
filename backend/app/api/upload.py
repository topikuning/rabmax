"""File upload + parser trigger endpoint."""

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_owned_project
from app.api.schemas import ParseSummary
from app.config import settings
from app.db.models import (
    ItemMatch,
    MatchMethod,
    MatchType,
    PaketItem,
    Project,
    ProjectStatus,
)
from app.db.session import get_db
from app.services.parser import parse_filled_rab, parse_workbook

router = APIRouter()

ALLOWED_EXTENSIONS = {".xlsx", ".xlsm"}


def _validate_upload(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Filename required")
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Only {ALLOWED_EXTENSIONS} files allowed",
        )


@router.post("/{project_id}", response_model=ParseSummary)
async def upload_and_parse(
    file: UploadFile = File(...),
    mode: str = Form("generate"),
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> ParseSummary:
    """Upload Excel file + immediately parse + populate paket_items.

    mode: 'generate' (RAB kosong → BOQ) or 'profit_analysis' (RAB terisi → profit).
    """
    project_id = project.id
    _validate_upload(file)

    # Persist file
    ext = Path(file.filename).suffix.lower()
    save_name = f"{project_id}_{uuid4().hex[:8]}{ext}"
    save_path = settings.upload_path / save_name

    project.status = ProjectStatus.PARSING
    await db.flush()

    with save_path.open("wb") as dst:
        shutil.copyfileobj(file.file, dst)
    logger.info(f"Uploaded to {save_path}, size={save_path.stat().st_size}")

    project.input_file_path = str(save_path.relative_to(settings.storage_path))

    # Parse
    try:
        if mode == "profit_analysis":
            result = parse_filled_rab(save_path)
        else:
            result = parse_workbook(save_path)
    except Exception as e:
        logger.exception("Parse failed")
        project.status = ProjectStatus.FAILED
        await db.flush()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Parse failed: {e}"
        ) from e

    # Clear existing items (re-upload scenario)
    from sqlalchemy import delete

    await db.execute(delete(PaketItem).where(PaketItem.project_id == project_id))

    # Insert parsed items
    for item in result.items:
        paket_item = PaketItem(
            project_id=project_id,
            sheet_name=item.sheet_name,
            excel_row=item.excel_row,
            no_label=item.no_label,
            uraian=item.uraian,
            satuan=item.satuan,
            volume=item.volume,
            parent_uraian=item.parent_uraian,
            norm_uraian=item.norm_uraian,
            norm_satuan=item.norm_satuan,
        )
        db.add(paket_item)
        # Placeholder match (UNRESOLVED) — Stage 2 matcher akan isi
        match = ItemMatch(
            project_id=project_id,
            paket_item=paket_item,
            match_type=MatchType.UNRESOLVED,
            method=MatchMethod.RULE_TOKEN,
            confidence=0.0,
        )
        db.add(match)

    project.status = ProjectStatus.READY_FOR_REVIEW
    await db.flush()

    # Count unique items (uraian + satuan)
    unique_keys = {(it.norm_uraian, it.norm_satuan) for it in result.items}

    return ParseSummary(
        project_id=project_id,
        paket_sheets=len(result.paket_sheets),
        aggregator_sheets=len(result.aggregator_sheets),
        items_total=len(result.items),
        items_unique=len(unique_keys),
        needs_ai_assist=result.needs_ai_assist,
        warnings=result.warnings,
    )
