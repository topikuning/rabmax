"""Item match endpoints — list per project, run matcher, manual override."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import (
    ItemMatchResponse,
    ManualMatchUpdate,
    PaketItemResponse,
)
from app.db.models import (
    AHSPCode,
    ItemMatch,
    MatchMethod,
    MatchType,
    PaketItem,
    Project,
)
from app.db.session import get_db
from app.services.matcher import run_matching

router = APIRouter()


@router.post("/{project_id}/run", status_code=status.HTTP_200_OK)
async def run_matcher(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stage 2 — jalankan rule + LLM matcher untuk semua item project."""
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    try:
        summary = await run_matching(project_id, db)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Matching failed: {e}"
        ) from e
    return asdict(summary)


@router.get("/{project_id}/items", response_model=list[PaketItemResponse])
async def list_items(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[PaketItem]:
    """All paket items for a project."""
    result = await db.execute(
        select(PaketItem)
        .where(PaketItem.project_id == project_id)
        .order_by(PaketItem.sheet_name, PaketItem.excel_row)
    )
    return list(result.scalars().all())


@router.get("/{project_id}", response_model=list[ItemMatchResponse])
async def list_matches(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    only_unreviewed: bool = False,
) -> list[ItemMatch]:
    """All matches for a project. Optionally filter to unreviewed."""
    stmt = select(ItemMatch).where(ItemMatch.project_id == project_id)
    if only_unreviewed:
        stmt = stmt.where(ItemMatch.reviewed_by_user.is_(False))
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch("/{match_id}", response_model=ItemMatchResponse)
async def update_match(
    match_id: int,
    payload: ManualMatchUpdate,
    db: AsyncSession = Depends(get_db),
) -> ItemMatch:
    """User override of a match. Marks as reviewed."""
    match = await db.get(ItemMatch, match_id)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Match not found")

    # Validate match type
    try:
        match_type_enum = MatchType(payload.match_type)
    except ValueError as e:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Invalid match_type: {payload.match_type}"
        ) from e

    # If AHSP, verify AHSP exists
    if match_type_enum == MatchType.AHSP:
        if not payload.ahsp_id:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "ahsp_id required for AHSP match"
            )
        ahsp = await db.get(AHSPCode, payload.ahsp_id)
        if not ahsp:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "AHSP not found")
        match.ahsp_id = payload.ahsp_id
        match.lumpsum_price = None
        match.lumpsum_source = None
    elif match_type_enum == MatchType.LUMPSUM:
        if payload.lumpsum_price is None:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "lumpsum_price required for LUMPSUM match"
            )
        match.lumpsum_price = payload.lumpsum_price
        match.lumpsum_source = payload.lumpsum_source
        match.ahsp_id = None

    match.match_type = match_type_enum
    match.method = MatchMethod.MANUAL
    if payload.tkdn_factor is not None:
        match.tkdn_factor = payload.tkdn_factor
    if payload.user_notes is not None:
        match.user_notes = payload.user_notes
    match.reviewed_by_user = True
    match.confidence = 1.0  # Manual = full confidence

    await db.flush()
    await db.refresh(match)
    return match
