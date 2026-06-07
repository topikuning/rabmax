"""Tests resolver Tier 1-6 (synthetic snapshots, SQLite)."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401
from app.db.models import (
    BahanUpahItem,
    KotaKabupaten,
    ManualPriceOverride,
    PriceSnapshot,
    Provinsi,
    Vendor,
)
from app.db.session import Base
from app.services.parser import normalize_text
from app.services.pricing.resolver import resolve_price

NAMA, SAT, TAHUN = "Semen Portland", "kg", 2026
NORM = normalize_text(NAMA)


@pytest_asyncio.fixture
async def ctx():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    Sm = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with Sm() as db:
        ntb = Provinsi(kode="52", nama="NTB", nama_singkat="NTB")
        db.add(ntb)
        await db.flush()
        kota = KotaKabupaten(provinsi_id=ntb.id, kode="5271", nama="Kota Mataram", tipe="kota")
        db.add(kota)
        v = Vendor(name="TokoX", domain="tokox.id", reliability_score=0.8, source_type="official_distributor")
        db.add(v)
        await db.flush()
        yield db, ntb, kota, v
    await eng.dispose()


def _snap(v, harga, *, kota_id=None, prov_id=None, scope=None):
    return PriceSnapshot(
        vendor_id=v.id, nama_material=NAMA, norm_nama=NORM, satuan=SAT,
        harga=harga, harga_standar=harga, source_url="https://tokox.id/p", page_quote="Rp " + str(harga),
        discovered_via="ai_discovery", tahun=TAHUN,
        vendor_kota_id=kota_id, vendor_provinsi_id=prov_id, delivery_scope=scope,
    )


@pytest.mark.asyncio
async def test_tier1_kota_lokal(ctx):
    db, ntb, kota, v = ctx
    for h in (1450, 1460, 1440):
        db.add(_snap(v, h, kota_id=kota.id))
    await db.flush()
    r = await resolve_price(db, NAMA, SAT, kota.id, ntb.id, TAHUN)
    assert r.tier_used == "kota_lokal"
    assert 1440 <= r.harga_final <= 1460
    assert r.markup_transport == 0


@pytest.mark.asyncio
async def test_tier4_nasional_markup(ctx):
    db, ntb, kota, v = ctx
    for h in (1400, 1410, 1390):
        db.add(_snap(v, h, scope="nasional"))
    await db.flush()
    r = await resolve_price(db, NAMA, SAT, kota.id, ntb.id, TAHUN)
    assert r.tier_used == "nasional_markup"
    assert r.harga_final > r.harga_base  # + markup NTB
    assert r.markup_transport > 0


@pytest.mark.asyncio
async def test_tier6_manual(ctx):
    db, ntb, kota, v = ctx
    db.add(ManualPriceOverride(
        user_id=1, nama_material=NAMA, norm_nama=NORM, satuan=SAT, harga=1500,
        source_label="Survey toko", reason="discovery gagal",
    ))
    await db.flush()
    r = await resolve_price(db, NAMA, SAT, kota.id, ntb.id, TAHUN, user_id=1)
    assert r.tier_used == "manual" and r.harga_final == 1500


@pytest.mark.asyncio
async def test_unresolved(ctx):
    db, ntb, kota, v = ctx
    r = await resolve_price(db, NAMA, SAT, kota.id, ntb.id, TAHUN, user_id=1)
    assert r.tier_used == "unresolved" and r.harga_final is None


@pytest.mark.asyncio
async def test_tier0_official_ssh_kota(ctx):
    """Tier 0 — harga SSH resmi per kota (single-source, tier A) menang & tak butuh konsensus."""
    db, ntb, kota, v = ctx
    db.add(BahanUpahItem(
        nama=NAMA, satuan=SAT, harga=1700, category="bahan", tier="A",
        tkdn_factor=1.0, source_label="SSH Kota Mataram 2026", tahun=TAHUN,
        provinsi_id=ntb.id, kota_kabupaten_id=kota.id,
    ))
    await db.flush()
    r = await resolve_price(db, NAMA, SAT, kota.id, ntb.id, TAHUN)
    assert r.tier_used == "official_kota"
    assert r.harga_final == 1700 and r.n_sources == 1


@pytest.mark.asyncio
async def test_tier0_official_ssh_provinsi_fallback(ctx):
    """Tanpa harga kota → pakai harga SSH level provinsi (kota_id null)."""
    db, ntb, kota, v = ctx
    db.add(BahanUpahItem(
        nama=NAMA, satuan=SAT, harga=1650, category="bahan", tier="A",
        tkdn_factor=1.0, source_label="SSH NTB 2026", tahun=TAHUN,
        provinsi_id=ntb.id, kota_kabupaten_id=None,
    ))
    await db.flush()
    r = await resolve_price(db, NAMA, SAT, kota.id, ntb.id, TAHUN)
    assert r.tier_used == "official_provinsi" and r.harga_final == 1650


@pytest.mark.asyncio
async def test_tier5_discovery_then_recurse(ctx):
    db, ntb, kota, v = ctx

    async def fake_discovery(db, nama_material, satuan, kota_id, provinsi_id, tahun):
        for h in (1455, 1465, 1445):
            db.add(_snap(v, h, kota_id=kota_id))
        await db.flush()
        return 3

    r = await resolve_price(db, NAMA, SAT, kota.id, ntb.id, TAHUN, discovery=fake_discovery)
    assert r.tier_used == "kota_lokal"  # setelah discovery menambah snapshot kota
    assert 1445 <= r.harga_final <= 1465
