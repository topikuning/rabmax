"""Project CRUD + pricing endpoints."""

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_owned_project
from app.api.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.db.models import Project, User
from app.db.session import get_db
from app.services.orchestrator import generate_boq
from app.services.pricing import price_and_calibrate_project
from app.services.validator import check_records, check_workbook_double_count

router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0,
) -> list[Project]:
    """List project milik user yang login."""
    result = await db.execute(
        select(Project)
        .where(Project.owner_id == user.id)
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    project = Project(**payload.model_dump(), owner_id=user.id)
    # Derive provinsi dari kota (location-aware pricing).
    if project.kota_kabupaten_id:
        from app.db.models import KotaKabupaten

        kota = await db.get(KotaKabupaten, project.kota_kabupaten_id)
        if kota:
            project.provinsi_id = kota.provinsi_id
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project: Project = Depends(get_owned_project),
) -> Project:
    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> Project:
    updates = payload.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(project, k, v)
    await db.flush()
    await db.refresh(project)
    return project


@router.post("/{project_id}/price", status_code=status.HTTP_200_OK)
async def price_project(
    use_llm: bool = True,
    discover: bool = False,
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stage 3+5 — source harga per item lalu kalibrasi total ke target.

    Harga komponen di-resolve lokasi-aware (Tier 1-6) bila project punya kota/provinsi.
    `discover=true` mengizinkan AI web-search discovery (Tier 5) saat snapshot lokal
    belum cukup. Set final_hsp + calibration_multiplier di tiap ItemMatch. Jalankan
    setelah matcher (`POST /api/matches/{id}/run`).
    """
    try:
        summary = await price_and_calibrate_project(
            project.id, db, use_llm=use_llm, discover=discover
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Pricing failed: {e}"
        ) from e
    return asdict(summary)


@router.post("/{project_id}/generate", status_code=status.HTTP_200_OK)
async def generate_project_boq(
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Stage 4 — tulis workbook BOQ ke storage/outputs + validasi.

    Jalankan setelah matcher (`/matches/{id}/run`) + pricing (`/projects/{id}/price`).
    File hasil bisa diunduh via `/files/{output_file_path}`.
    """
    try:
        result = await generate_boq(project.id, db)
    except ValueError as e:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e

    # Validasi cepat (deterministik) di records yang baru dibangun.
    from app.services.orchestrator import _build_records

    report = check_records(await _build_records(project.id, db))
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
    project: Project = Depends(get_owned_project),
    db: AsyncSession = Depends(get_db),
) -> None:
    await db.delete(project)
