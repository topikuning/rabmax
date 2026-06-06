"""Integration test auth + multi-user isolation (SQLite in-memory)."""

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
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_db():
        async with session_maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    main_mod.app.dependency_overrides[get_db] = _override_db
    transport = ASGITransport(app=main_mod.app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    main_mod.app.dependency_overrides.clear()
    await engine.dispose()


async def _register_login(client, email, password="passw0rd!"):
    r = await client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    r = await client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.mark.asyncio
async def test_register_login_me(client):
    token = await _register_login(client, "a@example.com")
    r = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "a@example.com"
    assert r.json()["is_superuser"] is True  # user pertama = superuser


@pytest.mark.asyncio
async def test_protected_requires_token(client):
    assert (await client.get("/api/projects")).status_code == 401


@pytest.mark.asyncio
async def test_duplicate_email_conflict(client):
    await _register_login(client, "dup@example.com")
    r = await client.post(
        "/api/auth/register", json={"email": "dup@example.com", "password": "passw0rd!"}
    )
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_wrong_password_401(client):
    await _register_login(client, "b@example.com")
    r = await client.post(
        "/api/auth/login", data={"username": "b@example.com", "password": "nope"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_multiuser_isolation(client):
    # User A buat project.
    ta = await _register_login(client, "owner@example.com")
    ha = {"Authorization": f"Bearer {ta}"}
    r = await client.post("/api/projects", json={"name": "Proyek A"}, headers=ha)
    assert r.status_code == 201
    pid = r.json()["id"]
    assert (await client.get("/api/projects", headers=ha)).json()[0]["id"] == pid

    # User B tidak boleh lihat / akses project user A.
    tb = await _register_login(client, "intruder@example.com")
    hb = {"Authorization": f"Bearer {tb}"}
    assert (await client.get("/api/projects", headers=hb)).json() == []
    assert (await client.get(f"/api/projects/{pid}", headers=hb)).status_code == 404
    assert (await client.delete(f"/api/projects/{pid}", headers=hb)).status_code == 404
    # Pemilik tetap bisa akses.
    assert (await client.get(f"/api/projects/{pid}", headers=ha)).status_code == 200
