"""Wiring test — source_ahsp_components pakai resolver lokasi-aware.

Memastikan harga komponen AHSP berbeda antar kota (mis. Malang vs Surabaya)
saat kota_id diberikan, dan jatuh ke 0 (tanpa LLM) saat tak ada snapshot.
"""

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401
from app.db.models import (
    AHSPCode,
    AHSPComponent,
    KotaKabupaten,
    PriceSnapshot,
    Provinsi,
    Vendor,
)
from app.db.session import Base
from app.services.builder.source import source_ahsp_components
from app.services.parser import normalize_text

NAMA, SAT, TAHUN = "Semen Portland", "kg", 2026
NORM = normalize_text(NAMA)


@pytest_asyncio.fixture
async def ctx():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with sm() as db:
        jatim = Provinsi(kode="35", nama="Jawa Timur", nama_singkat="Jatim")
        db.add(jatim)
        await db.flush()
        malang = KotaKabupaten(provinsi_id=jatim.id, kode="3573", nama="Kota Malang", tipe="kota")
        surabaya = KotaKabupaten(provinsi_id=jatim.id, kode="3578", nama="Kota Surabaya", tipe="kota")
        v = Vendor(name="TokoX", domain="tokox.id", reliability_score=0.8,
                   source_type="official_distributor")
        db.add_all([malang, surabaya, v])
        await db.flush()

        ahsp = AHSPCode(kode="A.1.1", uraian="Pekerjaan beton", satuan="m3", source="test")
        db.add(ahsp)
        await db.flush()
        db.add(AHSPComponent(ahsp_id=ahsp.id, kategori="bahan", nama_material=NAMA,
                             koefisien=2.0, satuan=SAT))
        await db.flush()
        yield db, ahsp, malang, surabaya, v
    await eng.dispose()


def _snap(v, harga, kota_id):
    return PriceSnapshot(
        vendor_id=v.id, nama_material=NAMA, norm_nama=NORM, satuan=SAT,
        harga=harga, harga_standar=harga, source_url="https://tokox.id/p",
        page_quote="Rp " + str(harga), discovered_via="ai_discovery", tahun=TAHUN,
        vendor_kota_id=kota_id,
    )


@pytest.mark.asyncio
async def test_harga_beda_antar_kota(ctx):
    db, ahsp, malang, surabaya, v = ctx
    for h in (1450, 1460, 1440):  # Malang ~1450
        db.add(_snap(v, h, malang.id))
    for h in (1600, 1610, 1590):  # Surabaya ~1600
        db.add(_snap(v, h, surabaya.id))
    await db.flush()

    pm = await source_ahsp_components(
        ahsp, db, tahun=TAHUN, use_llm=False, kota_id=malang.id, provinsi_id=malang.provinsi_id
    )
    ps = await source_ahsp_components(
        ahsp, db, tahun=TAHUN, use_llm=False, kota_id=surabaya.id, provinsi_id=surabaya.provinsi_id
    )
    assert 1440 <= pm[0].harga <= 1460
    assert 1590 <= ps[0].harga <= 1610
    assert ps[0].harga > pm[0].harga  # Surabaya > Malang → lokasi-aware terbukti


@pytest.mark.asyncio
async def test_tanpa_snapshot_pakai_harga_satuan_nasional(ctx):
    """Tanpa snapshot lokasi & tanpa LLM → pakai harga_satuan nasional (baseline CK)."""
    db, ahsp, malang, surabaya, v = ctx
    # Set harga_satuan resmi pada komponen.
    comp = (await db.execute(select(AHSPComponent).where(AHSPComponent.ahsp_id == ahsp.id))).scalar_one()
    comp.harga_satuan = 1450
    await db.flush()
    priced = await source_ahsp_components(
        ahsp, db, tahun=TAHUN, use_llm=False, kota_id=malang.id, provinsi_id=malang.provinsi_id
    )
    assert priced[0].harga == 1450.0


@pytest.mark.asyncio
async def test_snapshot_lokasi_override_harga_satuan(ctx):
    """Snapshot lokasi (resolver) MENANG atas harga_satuan nasional (override per-kota)."""
    db, ahsp, malang, surabaya, v = ctx
    comp = (await db.execute(select(AHSPComponent).where(AHSPComponent.ahsp_id == ahsp.id))).scalar_one()
    comp.harga_satuan = 1450  # nasional
    for h in (1600, 1610, 1590):  # Surabaya lebih mahal
        db.add(_snap(v, h, surabaya.id))
    await db.flush()
    priced = await source_ahsp_components(
        ahsp, db, tahun=TAHUN, use_llm=False, kota_id=surabaya.id, provinsi_id=surabaya.provinsi_id
    )
    assert 1590 <= priced[0].harga <= 1610  # resolver lokasi menang, bukan 1450
