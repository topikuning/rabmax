"""Geografi endpoints — provinsi + kota/kabupaten (untuk dropdown lokasi proyek)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import KotaKabupaten, Provinsi
from app.db.session import get_db

router = APIRouter()


class ProvinsiResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kode: str
    nama: str
    nama_singkat: str | None
    pulau: str | None


class KotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    provinsi_id: int
    kode: str
    nama: str
    tipe: str


@router.get("/provinsi", response_model=list[ProvinsiResponse])
async def list_provinsi(db: AsyncSession = Depends(get_db)) -> list[Provinsi]:
    rows = await db.execute(select(Provinsi).order_by(Provinsi.nama))
    return list(rows.scalars().all())


@router.get("/kota", response_model=list[KotaResponse])
async def list_kota(
    provinsi_id: int, db: AsyncSession = Depends(get_db)
) -> list[KotaKabupaten]:
    rows = await db.execute(
        select(KotaKabupaten)
        .where(KotaKabupaten.provinsi_id == provinsi_id)
        .order_by(KotaKabupaten.nama)
    )
    return list(rows.scalars().all())
