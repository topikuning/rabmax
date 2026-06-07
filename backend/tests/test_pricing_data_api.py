"""Integration test panel Data Harga — endpoint read + filter (SQLite in-memory)."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.main as main_mod
from app.db.session import Base, get_db


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sm = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_db():
        async with sm() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    main_mod.app.dependency_overrides[get_db] = _override_db
    async with AsyncClient(transport=ASGITransport(app=main_mod.app), base_url="http://test") as c:
        yield c
    main_mod.app.dependency_overrides.clear()
    await engine.dispose()


async def _auth(client):
    await client.post("/api/auth/register", json={"email": "a@b.c", "password": "passw0rd!"})
    r = await client.post("/api/auth/login", data={"username": "a@b.c", "password": "passw0rd!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.asyncio
async def test_data_harga_endpoints(client):
    h = await _auth(client)
    # Seed 2 harga: Bandung & Surabaya (nama sama, kota beda).
    for kota, harga in [("Kota Bandung", 160500), ("Kota Surabaya", 175000)]:
        r = await client.post("/api/bahan-upah", headers=h, json={
            "nama": "Tukang Batu", "satuan": "OH", "harga": harga,
            "category": "upah", "tier": "A", "provinsi": "Jawa", "kota": kota, "tahun": 2026,
        })
        assert r.status_code == 201, r.text

    # Filter per kota.
    r = await client.get("/api/bahan-upah?kota=bandung", headers=h)
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1 and rows[0]["harga"] == 160500

    # Count dengan filter.
    r = await client.get("/api/bahan-upah/count?category=upah", headers=h)
    assert r.json()["count"] == 2

    # data-stats.
    r = await client.get("/api/pricing/data-stats", headers=h)
    assert r.status_code == 200
    js = r.json()
    assert js["bahan_upah_total"] == 2 and js["vendors"] == 0

    # vendors / snapshots / consensus kosong tapi 200.
    for path in ("vendors", "snapshots", "consensus"):
        r = await client.get(f"/api/pricing/{path}", headers=h)
        assert r.status_code == 200 and r.json() == []


@pytest.mark.asyncio
async def test_data_harga_requires_auth(client):
    r = await client.get("/api/pricing/data-stats")
    assert r.status_code == 401
