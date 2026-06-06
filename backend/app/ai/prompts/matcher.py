"""Prompt untuk Stage 2b — LLM verification matcher (constrained generation).

LLM HANYA boleh memilih dari kandidat yang diberikan (atau menyatakan tidak ada
yang cocok / lumpsum). Tidak boleh mengarang kode AHSP baru.
"""

from __future__ import annotations

SYSTEM = (
    "Anda asisten estimator konstruksi Indonesia yang ahli AHSP Permen PUPR 8/2023. "
    "Tugas Anda mencocokkan item pekerjaan dari file lelang ke kode AHSP yang tepat. "
    "Pilih HANYA dari daftar kandidat yang diberikan. Jangan mengarang kode. "
    "Jika tidak ada kandidat yang benar-benar sesuai jenis pekerjaan, kembalikan "
    "chosen_ahsp_id null dan set suggest_lumpsum sesuai penilaian Anda. "
    "Perhatikan: satuan (sat) harus konsisten; jenis pekerjaan (galian, beton, "
    "pembesian, plesteran, dll) tidak boleh tertukar."
)

SCHEMA_HINT = (
    '{"chosen_ahsp_id": <int|null>, "confidence": <float 0-1>, '
    '"suggest_lumpsum": <bool>, "reasoning": "<ringkas, bahasa Indonesia>"}'
)


def build_matcher_prompt(
    item_uraian: str,
    item_satuan: str,
    candidates: list[dict],
) -> str:
    """Susun prompt user. `candidates` = list {ahsp_id, kode, uraian, satuan}."""
    lines = [
        "ITEM PEKERJAAN (PAKEM, tidak bisa diubah):",
        f"- Uraian : {item_uraian}",
        f"- Satuan : {item_satuan}",
        "",
        "KANDIDAT AHSP (pilih salah satu ahsp_id, atau null):",
    ]
    for c in candidates:
        lines.append(
            f"- ahsp_id={c['ahsp_id']} | kode={c['kode']} | "
            f"sat={c['satuan']} | {c['uraian']}"
        )
    lines.append("")
    lines.append(
        "Pilih ahsp_id yang jenis pekerjaan & satuannya paling tepat untuk ITEM di atas."
    )
    return "\n".join(lines)
