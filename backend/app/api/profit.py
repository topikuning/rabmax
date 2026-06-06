"""Profit analysis endpoints (Mode B)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ProfitAnalysisResponse
from app.db.models import ProfitAnalysis
from app.db.session import get_db

router = APIRouter()


@router.get("/{project_id}", response_model=list[ProfitAnalysisResponse])
async def list_analyses(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[ProfitAnalysis]:
    """List all profit analyses for a project (history)."""
    result = await db.execute(
        select(ProfitAnalysis)
        .where(ProfitAnalysis.project_id == project_id)
        .order_by(ProfitAnalysis.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/detail/{analysis_id}", response_model=ProfitAnalysisResponse)
async def get_analysis(
    analysis_id: int, db: AsyncSession = Depends(get_db)
) -> ProfitAnalysis:
    a = await db.get(ProfitAnalysis, analysis_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return a


@router.post("/{project_id}/run", status_code=status.HTTP_202_ACCEPTED)
async def run_analysis(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger profit analysis for project (Mode B).

    Pipeline (TODO Session 2):
    1. Parse RAB terisi → extract HPS per item
    2. For each item: lookup harga distributor real (DB + AI for missing)
    3. Compute cost real vs HPS → profit per item
    4. Aggregate per paket
    5. AI narrative summary (top risks, recommendations)
    6. Persist ProfitAnalysis row
    """
    # Placeholder — full implementation in Session 2
    raise HTTPException(
        status.HTTP_501_NOT_IMPLEMENTED,
        "Profit analyzer pipeline pending — Session 2 deliverable",
    )
