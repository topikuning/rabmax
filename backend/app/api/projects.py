"""Project CRUD + pricing endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.db.models import Project
from app.db.session import get_db
from app.services.orchestrator import generate_boq
from app.services.pricing import price_and_calibrate_project
from app.services.validator import check_records, check_workbook_double_count

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
) -> list[Project]:
    """List all projects (single user mode)."""
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    project = Project(**payload.model_dump())
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(project, k, v)
    await db.flush()
    await db.refresh(project)
    return project


@router.post("/{project_id}/price", status_code=status.HTTP_200_OK)
async def price_project(
    project_id: int,
    use_llm: bool = True,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stage 3+5 — source harga per item lalu kalibrasi total ke target.

    Set final_hsp + calibration_multiplier di tiap ItemMatch. Jalankan setelah
    matcher (`POST /api/matches/{id}/run`). Stage 4 (tulis Excel) menyusul.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    try:
        summary = await price_and_calibrate_project(project_id, db, use_llm=use_llm)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Pricing failed: {e}"
        ) from e
    return asdict(summary)


@router.post("/{project_id}/generate", status_code=status.HTTP_200_OK)
async def generate_project_boq(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stage 4 — tulis workbook BOQ ke storage/outputs + validasi.

    Jalankan setelah matcher (`/matches/{id}/run`) + pricing (`/projects/{id}/price`).
    File hasil bisa diunduh via `/files/{output_file_path}`.
    """
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    try:
        result = await generate_boq(project_id, db)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e

    # Validasi cepat (deterministik) di records yang baru dibangun.
    from app.services.orchestrator import _build_records

    report = check_records(await _build_records(project_id, db))
    # Scan double-count dinamis di workbook hasil (struktur dideteksi per-file).
    from app.config import settings

    dc = check_workbook_double_count(settings.storage_path / result.output_file_path)
    warnings = report.warnings + dc.warnings
    return {
        **asdict(result),
        "download_url": f"/files/{result.output_file_path}",
        "validation": {
            "ok": report.ok,
            "errors": report.errors,
            "warnings": warnings,
            "stats": report.stats,
        },
    }


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    await db.delete(project)
