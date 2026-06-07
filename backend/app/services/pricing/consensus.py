"""Stage 5 — Cross-validation & consensus (RABMAXPROMPT 4.6).

Pure python (statistics) → unit-testable. Buang outlier (>2σ), hitung median +
range + confidence. Tiap snapshot harus sudah `harga_standar` (post-konversi).
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field


@dataclass
class SnapshotInput:
    harga_standar: float
    vendor_reliability: float = 0.5
    source_type: str = "unknown"


@dataclass
class ConsensusResult:
    n_sources: int = 0
    median_price: float = 0.0
    mean_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    std_deviation: float = 0.0
    variance_pct: float = 0.0
    confidence: float = 0.0
    needs_review: bool = True
    outlier_indices: list[int] = field(default_factory=list)
    used_indices: list[int] = field(default_factory=list)


def compute_consensus(snapshots: list[SnapshotInput]) -> ConsensusResult:
    """Hitung konsensus harga dari daftar snapshot (≥1)."""
    if not snapshots:
        return ConsensusResult()

    prices = [s.harga_standar for s in snapshots]
    n = len(prices)
    med = statistics.median(prices)
    std = statistics.pstdev(prices) if n > 1 else 0.0

    # Outlier: di luar [median - 2σ, median + 2σ]
    outliers: list[int] = []
    used: list[int] = []
    if std > 0:
        lo, hi = med - 2 * std, med + 2 * std
        for i, p in enumerate(prices):
            (outliers if (p < lo or p > hi) else used).append(i)
    else:
        used = list(range(n))

    if not used:  # semua "outlier" (mis. 2 nilai jauh) → pakai semua
        used = list(range(n))
        outliers = []

    kept = [prices[i] for i in used]
    med2 = statistics.median(kept)
    mean2 = statistics.fmean(kept)
    std2 = statistics.pstdev(kept) if len(kept) > 1 else 0.0
    variance_pct = round((std2 / med2 * 100) if med2 else 0.0, 2)

    # Confidence (RABMAXPROMPT 4.6)
    conf = 0.3
    if len(kept) >= 3:
        conf += 0.2
    if variance_pct < 15:
        conf += 0.2
    if any(snapshots[i].vendor_reliability > 0.7 for i in used):
        conf += 0.2
    if any(snapshots[i].source_type == "official_distributor" for i in used):
        conf += 0.1
    conf = min(1.0, round(conf, 3))

    return ConsensusResult(
        n_sources=len(kept),
        median_price=round(med2, 2),
        mean_price=round(mean2, 2),
        min_price=round(min(kept), 2),
        max_price=round(max(kept), 2),
        std_deviation=round(std2, 2),
        variance_pct=variance_pct,
        confidence=conf,
        needs_review=variance_pct > 30 or len(kept) < 2,
        outlier_indices=outliers,
        used_indices=used,
    )
