"""Stage 2b — LLM verification untuk match skor rendah.

Constrained generation: LLM hanya boleh memilih dari kandidat (top-K) yang
diberikan rule_matcher, atau menyatakan tidak ada / lumpsum.
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger

from app.ai.client import AIMessage, ai_client
from app.ai.prompts import matcher as matcher_prompt
from app.config import settings
from app.services.matcher.rule_matcher import ScoredCandidate


@dataclass
class LLMMatchDecision:
    chosen_ahsp_id: int | None
    confidence: float
    suggest_lumpsum: bool
    reasoning: str


def _best_rule(candidates: list[ScoredCandidate], reason: str) -> LLMMatchDecision:
    """Keputusan murni rule-based: ambil kandidat skor teratas."""
    best = candidates[0]
    return LLMMatchDecision(
        chosen_ahsp_id=best.candidate.ahsp_id,
        confidence=min(best.score, 0.6),
        suggest_lumpsum=False,
        reasoning=reason,
    )


async def verify_match(
    item_uraian: str,
    item_satuan: str,
    candidates: list[ScoredCandidate],
) -> LLMMatchDecision:
    """Minta LLM memilih kandidat terbaik. Return keputusan ter-validasi.

    `candidates` = top-K hasil rule_matcher (sudah ranked). Bila kosong, langsung
    putuskan lumpsum.
    """
    if not candidates:
        return LLMMatchDecision(None, 0.0, True, "Tidak ada kandidat AHSP.")

    # Mode tanpa-AI: LLM dimatikan atau tak ada provider siap → murni rule-based.
    # Tak ada panggilan API sama sekali (cepat, tak ada badai retry per item).
    if not settings.matching_use_llm or not ai_client.has_usable_provider():
        return _best_rule(candidates, "Rule-based (LLM nonaktif/tidak tersedia).")

    cand_payload = [
        {
            "ahsp_id": sc.candidate.ahsp_id,
            "kode": sc.candidate.kode,
            "uraian": sc.candidate.norm_uraian,
            "satuan": sc.candidate.norm_satuan,
        }
        for sc in candidates
    ]
    valid_ids = {c["ahsp_id"] for c in cand_payload}

    messages = [
        AIMessage(role="system", content=matcher_prompt.SYSTEM),
        AIMessage(
            role="user",
            content=matcher_prompt.build_matcher_prompt(
                item_uraian, item_satuan, cand_payload
            ),
        ),
    ]

    try:
        data = await ai_client.complete_json(
            messages,
            schema_hint=matcher_prompt.SCHEMA_HINT,
            model=settings.default_ai_model_matcher,
            max_tokens=512,
        )
    except Exception as e:  # noqa: BLE001 — degrade gracefully ke best rule candidate
        logger.warning(f"LLM matcher gagal, fallback ke best rule candidate: {e}")
        return _best_rule(candidates, "LLM unavailable; pakai kandidat rule teratas.")

    chosen = data.get("chosen_ahsp_id")
    # Validasi: LLM tidak boleh mengarang id di luar kandidat.
    if chosen is not None and chosen not in valid_ids:
        logger.warning(f"LLM memilih ahsp_id {chosen} di luar kandidat; abaikan.")
        chosen = None

    return LLMMatchDecision(
        chosen_ahsp_id=chosen,
        confidence=float(data.get("confidence", 0.0) or 0.0),
        suggest_lumpsum=bool(data.get("suggest_lumpsum", chosen is None)),
        reasoning=str(data.get("reasoning", "")),
    )
