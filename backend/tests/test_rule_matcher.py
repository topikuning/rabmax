"""Unit tests Stage 2 rule matcher (deterministik, tanpa DB/LLM)."""

from app.services.matcher.rule_matcher import (
    Candidate,
    match_item,
)
from app.services.matcher.rules import (
    classify_work_group,
    detect_kabel_nyy,
    tokenize,
    weak_override_penalty,
)


def _c(ahsp_id, kode, uraian, satuan, wg=None):
    return Candidate(ahsp_id, kode, uraian.lower(), satuan.lower(), wg)


def test_tokenize_drops_stopwords_keeps_dimension():
    toks = tokenize("pekerjaan galian tanah biasa kedalaman 1 m")
    assert "galian" in toks and "tanah" in toks
    assert "pekerjaan" not in toks  # stopword
    assert "1" in toks  # dimensi dipertahankan


def test_classify_work_group():
    assert classify_work_group("galian tanah biasa") == "tanah"
    assert classify_work_group("pembesian besi beton polos") == "pembesian"
    assert classify_work_group("plesteran dinding 1:4") == "plesteran"
    assert classify_work_group("pasang kabel nyy 4x25") == "listrik"


def test_weak_override_penalty_blocks_beton_to_pembesian():
    # "beton" item vs "pembesian" candidate -> penalti.
    p = weak_override_penalty("beton mutu rendah k100", "pembesian besi beton ulir")
    assert p < 1.0


def test_match_filters_by_work_group():
    item_u, item_s = "galian tanah biasa", "m3"
    cands = [
        _c(1, "A.1", "galian tanah biasa kedalaman 1 m", "m3"),
        _c(2, "B.1", "pembesian besi beton polos", "kg"),
        _c(3, "C.1", "plesteran dinding 1:4", "m2"),
    ]
    res = match_item(item_u, item_s, cands)
    assert res.best is not None
    assert res.best.candidate.ahsp_id == 1
    assert res.accepted
    assert res.method in ("rule_exact", "rule_token")


def test_kabel_nyy_remap_short_circuit():
    assert detect_kabel_nyy("kabel nyy 4x25 mm") == "5.1.1.1.36"
    item_u, item_s = "pasang kabel nyy 4x25 mm", "m"
    cands = [
        _c(10, "5.1.1.1.36", "pasang kabel nyy 4x25", "m", "listrik"),
        _c(11, "5.1.5.13", "pasang stop kontak", "buah", "listrik"),
    ]
    res = match_item(item_u, item_s, cands)
    assert res.best.candidate.ahsp_id == 10
    assert res.method == "rule_exact"


def test_low_score_not_accepted():
    item_u, item_s = "pekerjaan unik tanpa padanan xyz", "ls"
    cands = [_c(1, "A.1", "galian tanah biasa", "m3")]
    res = match_item(item_u, item_s, cands)
    assert not res.accepted  # skor rendah -> diteruskan ke LLM
