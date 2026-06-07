"""Test seed geografi (38 provinsi + 514 kota/kab) + adjacency."""

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401 — register semua model
from app.db.models import KotaKabupaten, Provinsi, ProvinsiAdjacency
from app.db.session import Base
from scripts.seed_geografi import apply_geografi


@pytest_asyncio.fixture
async def db():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    Sm = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with Sm() as s:
        yield s
    await eng.dispose()


@pytest.mark.asyncio
async def test_seed_counts(db):
    s = await apply_geografi(db)
    await db.commit()
    assert s["provinsi"]["created"] == 38
    assert s["kota_kabupaten"]["created"] == 514
    assert s["adjacency_created"] > 0
    assert (await db.execute(select(func.count(Provinsi.id)))).scalar_one() == 38
    assert (await db.execute(select(func.count(KotaKabupaten.id)))).scalar_one() == 514


@pytest.mark.asyncio
async def test_ntb_mataram(db):
    await apply_geografi(db)
    await db.commit()
    ntb = (await db.execute(select(Provinsi).where(Provinsi.kode == "52"))).scalar_one()
    assert ntb.nama_singkat == "NTB" and ntb.pulau == "Bali-Nusra"
    mtr = (await db.execute(select(KotaKabupaten).where(KotaKabupaten.kode == "5271"))).scalar_one()
    assert mtr.provinsi_id == ntb.id and mtr.tipe == "kota"


@pytest.mark.asyncio
async def test_idempotent(db):
    await apply_geografi(db)
    await db.commit()
    s2 = await apply_geografi(db)
    await db.commit()
    # Tidak menggandakan & adjacency tak dibuat ulang.
    assert (await db.execute(select(func.count(Provinsi.id)))).scalar_one() == 38
    assert s2["adjacency_created"] == 0
    assert (await db.execute(select(func.count(ProvinsiAdjacency.id)))).scalar_one() == 104
