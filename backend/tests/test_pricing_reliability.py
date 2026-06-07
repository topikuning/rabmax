"""Tests reliability updater (RABMAXPROMPT 4.7)."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.db.models  # noqa: F401
from app.db.models import Vendor
from app.db.session import Base
from app.services.pricing.reliability import apply_reliability, reliability_delta


def test_delta_thresholds():
    assert reliability_delta(100, 100) == 0.02       # tepat median
    assert reliability_delta(110, 100) == 0.01       # 10% → +0.01
    assert reliability_delta(140, 100) == -0.05      # 40% outlier → -0.05
    assert reliability_delta(120, 100) == 0.0        # 20% → netral


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
async def test_increments_on_convergence(db):
    v = Vendor(name="A", domain="a.id", reliability_score=0.5)
    db.add(v)
    await db.flush()
    ch = await apply_reliability(db, 100, [(v.id, 100, True)])
    assert ch[0].new_score == 0.52
    assert v.successful_scrapes == 1


@pytest.mark.asyncio
async def test_auto_deactivate_low_score(db):
    v = Vendor(name="B", domain="b.id", reliability_score=0.22)
    db.add(v)
    await db.flush()
    ch = await apply_reliability(db, 100, [(v.id, 200, False)])  # outlier -0.05 → 0.17
    assert ch[0].deactivated and v.is_active is False
