"""Profit analysis endpoints (Mode B)."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_owned_project
from app.api.schemas import ProfitAnalysisResponse
from app.db.models import ProfitAnalysis, Project, User
from app.db.session import get_db
from app.services.profit_analyzer import run_profit_analysis

router = APIRouter()


@router.get("/{project_id}", response_model=list[ProfitAnalysisResponse])
async def list_analyses(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> list[ProfitAnalysis]:
    """List all profit analyses for a project (history)."""
    result = await db.execute(
        select(ProfitAnalysis)
        .where(ProfitAnalysis.project_id == project.id)
        .order_by(ProfitAnalysis.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/detail/{analysis_id}", response_model=ProfitAnalysisResponse)
async def get_analysis(
    analysis_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ProfitAnalysis:
    a = await db.get(ProfitAnalysis, analysis_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    project = await db.get(Project, a.project_id)
    if project is None or (project.owner_id is not None and project.owner_id != user.id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    return a


@router.post("/{project_id}/run", status_code=status.HTTP_200_OK)
async def run_analysis(
    use_llm: bool = True,
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Trigger profit analysis for project (Mode B).

    Pipeline:
    1. Parse RAB terisi → extract HPS per item.
    2. Estimasi biaya real (match HSP / LLM / fallback rasio).
    3. Profit per item & agregasi per paket.
    4. Identifikasi item berisiko + narasi AI.
    5. Persist ProfitAnalysis.
    """
    try:
        result = await run_profit_analysis(project.id, db, use_llm=use_llm)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    return asdict(result)
