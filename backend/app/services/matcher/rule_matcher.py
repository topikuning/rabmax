"""Stage 2a — deterministic rule matcher.

Sengaja decoupled dari ORM (input berupa dataclass biasa) supaya unit-testable
tanpa DB. Orchestrator yang adapt objek SQLAlchemy -> struktur di sini.

Algoritma (urutan sesuai Known Issue #4 — work group dulu, baru token):
  1. Kabel NYY remap -> exact kode (skor ~0.99).
  2. Filter kandidat ke work group yang sama dengan item.
  3. Skor token: blend Jaccard + coverage; bonus/penalti satuan; weak override.
  4. Tentukan method: rule_exact (skor tinggi + satuan match) / rule_token.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.services.matcher.rules import (
    classify_work_group,
    detect_kabel_nyy,
    tokenize,
    weak_override_penalty,
)

# Threshold skor.
SCORE_ACCEPT = 0.80  # >= ini diterima sebagai rule match (Known Issue #4: LLM utk < 0.8)
SCORE_EXACT = 0.95  # >= ini + satuan match -> rule_exact
SATUAN_BONUS = 0.10
SATUAN_PENALTY = 0.10
TOPK_FOR_LLM = 5  # kandidat yang diteruskan ke LLM saat skor rendah


@dataclass(frozen=True)
class Candidate:
    """Kandidat AHSP untuk matching (subset field, decoupled dari ORM)."""

    ahsp_id: int
    kode: str
    norm_uraian: str
    norm_satuan: str
    work_group: str | None = None


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: Candidate
    score: float
    reasons: tuple[str, ...] = ()


@dataclass
class RuleMatchResult:
    work_group: str | None
    best: ScoredCandidate | None
    ranked: list[ScoredCandidate] = field(default_factory=list)
    method: str = "none"  # rule_exact | rule_token | none
    accepted: bool = False

    @property
    def topk_for_llm(self) -> list[ScoredCandidate]:
        return self.ranked[:TOPK_FOR_LLM]


def _token_score(item_tokens: list[str], cand_tokens: list[str]) -> float:
    """Blend Jaccard similarity + coverage of item tokens. Range 0-1."""
    if not item_tokens or not cand_tokens:
        return 0.0
    si, sc = set(item_tokens), set(cand_tokens)
    inter = si & sc
    if not inter:
        return 0.0
    jaccard = len(inter) / len(si | sc)
    coverage = len(inter) / len(si)
    return 0.5 * jaccard + 0.5 * coverage


def _candidate_work_group(c: Candidate) -> str | None:
    return c.work_group or classify_work_group(c.norm_uraian)


def score_candidate(
    item_norm_uraian: str,
    item_norm_satuan: str,
    item_tokens: list[str],
    candidate: Candidate,
) -> ScoredCandidate:
    """Skor satu kandidat terhadap item. Asumsi sudah satu work group."""
    cand_tokens = tokenize(candidate.norm_uraian)
    base = _token_score(item_tokens, cand_tokens)
    reasons = [f"token={base:.2f}"]

    score = base
    if candidate.norm_satuan and item_norm_satuan:
        if candidate.norm_satuan == item_norm_satuan:
            score += SATUAN_BONUS
            reasons.append("satuan_match")
        else:
            score -= SATUAN_PENALTY
            reasons.append(f"satuan_mismatch({candidate.norm_satuan})")

    penalty = weak_override_penalty(item_norm_uraian, candidate.norm_uraian)
    if penalty < 1.0:
        score *= penalty
        reasons.append(f"weak_override×{penalty:.2f}")

    score = max(0.0, min(1.0, score))
    return ScoredCandidate(candidate=candidate, score=score, reasons=tuple(reasons))


def match_item(
    item_norm_uraian: str,
    item_norm_satuan: str,
    candidates: list[Candidate],
) -> RuleMatchResult:
    """Cari best AHSP match untuk satu item lewat aturan deterministik."""
    work_group = classify_work_group(item_norm_uraian)

    # 1) Kabel NYY remap — short-circuit ke exact kode jika ada di kandidat.
    kabel_kode = detect_kabel_nyy(item_norm_uraian)
    if kabel_kode:
        for c in candidates:
            if c.kode == kabel_kode:
                sc = ScoredCandidate(c, 0.99, ("kabel_nyy_remap",))
                return RuleMatchResult(
                    work_group="listrik",
                    best=sc,
                    ranked=[sc],
                    method="rule_exact",
                    accepted=True,
                )

    # 2) Filter ke work group yang sama (jika item terklasifikasi).
    if work_group is not None:
        pool = [c for c in candidates if _candidate_work_group(c) == work_group]
        # Fallback: kalau filter menghasilkan kosong, pakai semua (jangan buang item).
        if not pool:
            pool = candidates
    else:
        pool = candidates

    # 3) Skor semua kandidat di pool.
    item_tokens = tokenize(item_norm_uraian)
    scored = [
        score_candidate(item_norm_uraian, item_norm_satuan, item_tokens, c)
        for c in pool
    ]
    scored.sort(key=lambda s: s.score, reverse=True)

    if not scored:
        return RuleMatchResult(work_group=work_group, best=None, ranked=[], method="none")

    best = scored[0]
    accepted = best.score >= SCORE_ACCEPT
    if not accepted:
        method = "none"
    elif best.score >= SCORE_EXACT and item_norm_satuan == best.candidate.norm_satuan:
        method = "rule_exact"
    else:
        method = "rule_token"

    return RuleMatchResult(
        work_group=work_group,
        best=best,
        ranked=scored,
        method=method,
        accepted=accepted,
    )
