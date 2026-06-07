"""Tests classifier (keyword) + discovery (validate/save/hook), tanpa network."""

import pytest
import pytest_asyncio
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401
from app.db.models import KotaKabupaten, PriceSnapshot, Provinsi, Vendor
from app.db.session import Base
from app.services.pricing.classifier import classify_item
from app.services.pricing.discovery import (
    discover_prices,
    save_snapshots,
    validate_candidate,
)
from app.services.pricing.resolver import resolve_price
from scripts.seed_taxonomy import apply_taxonomy


@pytest_asyncio.fixture
async def db():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with eng.begin() as c:
        await c.run_sync(Base.metadata.create_all)
    Sm = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    async with Sm() as s:
        ntb = Provinsi(kode="52", nama="Nusa Tenggara Barat", nama_singkat="NTB")
        s.add(ntb)
        await s.flush()
        s.add(KotaKabupaten(provinsi_id=ntb.id, kode="5271", nama="Kota Mataram", tipe="kota"))
        await apply_taxonomy(s)
        await s.flush()
        yield s
    await eng.dispose()


def test_validate_rejects_no_url():
    assert validate_candidate({"page_quote": "Rp 1450 / kg ada di sini", "harga": 1450})[0] is False
    assert validate_candidate({"source_url": "https://x.id/p", "page_quote": "short", "harga": 1450})[0] is False
    assert validate_candidate({"source_url": "https://x.id/p", "page_quote": "Rp 1.450 per kg semen", "harga": 0})[0] is False
    ok, _ = validate_candidate({"source_url": "https://x.id/p", "page_quote": "Rp 1.450 per kg semen portland", "harga": 1450})
    assert ok


@pytest.mark.asyncio
async def test_classify_keyword(db):
    r = await classify_item(db, "Semen Tiga Roda 50kg", "kg", use_llm=False)
    assert r.category_code == "beton.semen.portland"
    assert r.method in ("keyword", "cache")
    # cache pada panggilan kedua
    r2 = await classify_item(db, "Semen Tiga Roda 50kg", "kg", use_llm=False)
    assert r2.method == "cache"


@pytest.mark.asyncio
async def test_save_snapshots_registers_vendor_and_skips_invalid(db):
    cands = [
        {"vendor_name": "TokoA", "vendor_domain": "tokoa.id", "source_url": "https://tokoa.id/semen",
         "page_quote": "Semen Portland Rp 1.450/kg di Mataram", "harga": 1450, "vendor_kota": "Kota Mataram"},
        {"vendor_name": "NoURL", "page_quote": "harga sekian", "harga": 1500},  # invalid
    ]
    created, warns = await save_snapshots(db, "Semen Portland", "kg", 2026, cands)
    assert created == 1 and len(warns) == 1
    assert (await db.execute(select(func.count(Vendor.id)))).scalar_one() == 1
    snap = (await db.execute(select(PriceSnapshot))).scalars().first()
    assert snap.vendor_kota_id is not None  # ter-link ke Kota Mataram


@pytest.mark.asyncio
async def test_discover_then_resolve(db):
    kota = (await db.execute(select(KotaKabupaten).where(KotaKabupaten.kode == "5271"))).scalar_one()
    ntb = (await db.execute(select(Provinsi).where(Provinsi.kode == "52"))).scalar_one()

    async def fake_ext(**kw):
        return [
            {"vendor_name": f"Toko{i}", "vendor_domain": f"toko{i}.id",
             "source_url": f"https://toko{i}.id/p", "page_quote": "Semen Portland Rp 1.4xx per kg Mataram",
             "harga": h, "vendor_kota": "Kota Mataram", "confidence": 0.8}
            for i, h in enumerate((1450, 1460, 1440))
        ]

    n = await discover_prices(db, nama_material="Semen Portland", satuan="kg",
                              kota_id=kota.id, provinsi_id=ntb.id, extractor=fake_ext)
    assert n == 3
    # resolver memakai snapshot hasil discovery
    async def hook(db2, **kw):
        return await discover_prices(db2, nama_material=kw["nama_material"], satuan=kw["satuan"],
                                     kota_id=kw["kota_id"], provinsi_id=kw["provinsi_id"], extractor=fake_ext)
    # snapshot sudah ada → Tier 1 langsung
    r = await resolve_price(db, "Semen Portland", "kg", kota.id, ntb.id, 2026, discovery=hook)
    assert r.tier_used == "kota_lokal" and 1440 <= r.harga_final <= 1460
