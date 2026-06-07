"""Stage 10 — Reliability updater (RABMAXPROMPT 4.7).

Vendor konvergen → skor naik; outlier → turun. Auto-deactivate yang gagal terus.
Delta murni (testable) + apply async ke DB.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Vendor

AUTO_DEACTIVATE_SCORE = 0.2
AUTO_DEACTIVATE_FAILS = 5


def reliability_delta(harga: float, median: float) -> float:
    """Penyesuaian skor berdasar deviasi harga vendor vs median konsensus."""
    if median <= 0:
        return 0.0
    dev = abs(harga - median) / median
    if dev <= 0.05:
        return 0.02
    if dev <= 0.15:
        return 0.01
    if dev > 0.30:
        return -0.05
    return 0.0


@dataclass
class ReliabilityChange:
    vendor_id: int
    old_score: float
    new_score: float
    deactivated: bool


async def apply_reliability(
    db: AsyncSession, median: float, contributions: list[tuple[int, float, bool]]
) -> list[ReliabilityChange]:
    """`contributions`: list (vendor_id, harga, converged). converged=False → fail."""
    changes: list[ReliabilityChange] = []
    for vendor_id, harga, converged in contributions:
        v = await db.get(Vendor, vendor_id)
        if v is None:
            continue
        old = float(v.reliability_score)
        delta = reliability_delta(harga, median)
        new = max(0.0, min(1.0, round(old + delta, 4)))
        v.reliability_score = new
        if converged:
            v.successful_scrapes += 1
            v.failed_scrapes = 0
        else:
            v.failed_scrapes += 1
        v.total_snapshots += 1
        deactivated = False
        if new < AUTO_DEACTIVATE_SCORE or v.failed_scrapes >= AUTO_DEACTIVATE_FAILS:
            v.is_active = False
            deactivated = True
        changes.append(ReliabilityChange(vendor_id, old, new, deactivated))
    await db.flush()
    return changes
