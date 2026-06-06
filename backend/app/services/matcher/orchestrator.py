"""Stage 2 orchestrator — rule pass -> LLM pass -> tulis ItemMatch.

Dedup: item berulang di banyak paket sheet. Keputusan match dihitung sekali per
unique key (norm_uraian, norm_satuan), lalu di-apply ke SEMUA item yang share key.
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    AHSPCode,
    ItemMatch,
    MatchMethod,
    MatchType,
    PaketItem,
    Project,
    ProjectStatus,
)
from app.services.matcher.llm_matcher import verify_match
from app.services.matcher.rule_matcher import (
    Candidate,
    RuleMatchResult,
    match_item,
)
from app.services.parser import normalize_text


@dataclass
class MatchRunSummary:
    project_id: int
    items_total: int
    unique_keys: int
    rule_matched: int
    llm_matched: int
    lumpsum: int
    unresolved: int


async def _load_candidates(db: AsyncSession) -> list[Candidate]:
    """Ambil semua AHSP dari DB sebagai Candidate (normalisasi on-the-fly)."""
    result = await db.execute(select(AHSPCode))
    out: list[Candidate] = []
    for a in result.scalars().all():
        out.append(
            Candidate(
                ahsp_id=a.id,
                kode=a.kode,
                norm_uraian=normalize_text(a.uraian),
                norm_satuan=normalize_text(a.satuan),
                work_group=a.work_group,
            )
        )
    return out


@dataclass
class _Decision:
    match_type: MatchType
    method: MatchMethod
    ahsp_id: int | None
    confidence: float


async def _decide(
    norm_uraian: str,
    norm_satuan: str,
    candidates: list[Candidate],
) -> _Decision:
    """Hitung keputusan match untuk satu unique key."""
    rule: RuleMatchResult = match_item(norm_uraian, norm_satuan, candidates)

    if rule.accepted and rule.best is not None:
        method = (
            MatchMethod.RULE_EXACT
            if rule.method == "rule_exact"
            else MatchMethod.RULE_TOKEN
        )
        return _Decision(
            MatchType.AHSP, method, rule.best.candidate.ahsp_id, rule.best.score
        )

    # Skor rendah -> LLM verify dari top-K kandidat.
    decision = await verify_match(norm_uraian, norm_satuan, rule.topk_for_llm)
    if decision.chosen_ahsp_id is not None:
        method = (
            MatchMethod.LLM_VERIFIED
            if decision.confidence >= 0.7
            else MatchMethod.LLM_SUGGESTED
        )
        return _Decision(
            MatchType.AHSP, method, decision.chosen_ahsp_id, decision.confidence
        )

    if decision.suggest_lumpsum:
        return _Decision(MatchType.LUMPSUM, MatchMethod.LLM_SUGGESTED, None, decision.confidence)

    return _Decision(MatchType.UNRESOLVED, MatchMethod.RULE_TOKEN, None, 0.0)


async def run_matching(project_id: int, db: AsyncSession) -> MatchRunSummary:
    """Jalankan Stage 2 untuk seluruh item di project."""
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} tidak ditemukan")

    project.status = ProjectStatus.MATCHING
    await db.flush()

    items = list(
        (
            await db.execute(
                select(PaketItem).where(PaketItem.project_id == project_id)
            )
        ).scalars().all()
    )
    candidates = await _load_candidates(db)
    logger.info(
        f"Matching project {project_id}: {len(items)} items, "
        f"{len(candidates)} AHSP candidates"
    )

    # Dedup decisions per unique key.
    decisions: dict[tuple[str, str], _Decision] = {}
    summary = MatchRunSummary(project_id, len(items), 0, 0, 0, 0, 0)

    for item in items:
        key = (item.norm_uraian, item.norm_satuan)
        if key not in decisions:
            decisions[key] = await _decide(item.norm_uraian, item.norm_satuan, candidates)
            summary.unique_keys += 1
            d = decisions[key]
            if d.method in (MatchMethod.RULE_EXACT, MatchMethod.RULE_TOKEN) and d.ahsp_id:
                summary.rule_matched += 1
            elif d.match_type == MatchType.AHSP:
                summary.llm_matched += 1
            elif d.match_type == MatchType.LUMPSUM:
                summary.lumpsum += 1
            else:
                summary.unresolved += 1

        d = decisions[key]

        # Ambil/lengkapi match row (dibuat saat upload, atau buat baru).
        existing = (
            await db.execute(
                select(ItemMatch).where(ItemMatch.paket_item_id == item.id)
            )
        ).scalar_one_or_none()
        match = existing or ItemMatch(project_id=project_id, paket_item_id=item.id)

        # Jangan timpa match yang sudah di-review manual user.
        if match.reviewed_by_user:
            if existing is None:
                db.add(match)
            continue

        match.match_type = d.match_type
        match.method = d.method
        match.ahsp_id = d.ahsp_id
        match.confidence = round(d.confidence, 3)
        if existing is None:
            db.add(match)

    project.status = ProjectStatus.READY_FOR_REVIEW
    await db.flush()
    logger.info(
        f"Match done: rule={summary.rule_matched} llm={summary.llm_matched} "
        f"lumpsum={summary.lumpsum} unresolved={summary.unresolved} "
        f"(unique={summary.unique_keys})"
    )
    return summary
