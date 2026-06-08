"""Test matcher tetap jalan TANPA AI (murni rule-based)."""

import pytest

import app.services.matcher.llm_matcher as lm
from app.services.matcher.llm_matcher import verify_match
from app.services.matcher.rule_matcher import Candidate, ScoredCandidate


def _cands():
    return [
        ScoredCandidate(Candidate(ahsp_id=10, kode="A.1", norm_uraian="pasang bata", norm_satuan="m2"), 0.82),
        ScoredCandidate(Candidate(ahsp_id=11, kode="A.2", norm_uraian="plester", norm_satuan="m2"), 0.55),
    ]


@pytest.mark.asyncio
async def test_match_tanpa_llm_pakai_rule_teratas(monkeypatch):
    """matching_use_llm=False → tak ada panggilan AI, ambil kandidat skor teratas."""
    monkeypatch.setattr(lm.settings, "matching_use_llm", False)

    async def _boom(*a, **k):
        raise AssertionError("ai_client.complete_json TIDAK boleh dipanggil saat LLM nonaktif")

    monkeypatch.setattr(lm.ai_client, "complete_json", _boom)

    d = await verify_match("pasang dinding bata", "m2", _cands())
    assert d.chosen_ahsp_id == 10
    assert d.confidence <= 0.6
    assert d.suggest_lumpsum is False


@pytest.mark.asyncio
async def test_match_tanpa_provider_siap_pakai_rule(monkeypatch):
    """LLM aktif tapi tak ada provider siap → tetap rule-based, tanpa panggil API."""
    monkeypatch.setattr(lm.settings, "matching_use_llm", True)
    monkeypatch.setattr(lm.ai_client, "has_usable_provider", lambda: False)

    async def _boom(*a, **k):
        raise AssertionError("tak boleh panggil API saat tak ada provider")

    monkeypatch.setattr(lm.ai_client, "complete_json", _boom)

    d = await verify_match("plesteran dinding", "m2", _cands())
    assert d.chosen_ahsp_id == 10


@pytest.mark.asyncio
async def test_match_tanpa_kandidat_lumpsum(monkeypatch):
    monkeypatch.setattr(lm.settings, "matching_use_llm", False)
    d = await verify_match("item aneh", "ls", [])
    assert d.chosen_ahsp_id is None and d.suggest_lumpsum is True
