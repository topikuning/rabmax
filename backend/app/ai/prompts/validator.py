"""Prompt untuk Stage 6 — LLM sanity check hasil BOQ.

Dipakai untuk pengecekan kewajaran yang sulit dengan aturan deterministik
(mis. harga satuan janggal, mismatch jenis pekerjaan vs satuan).
"""

from __future__ import annotations

SYSTEM = (
    "Anda QA estimator konstruksi Indonesia. Periksa kewajaran daftar harga "
    "satuan pekerjaan (HSP) hasil generate BOQ. Soroti item dengan harga satuan "
    "tidak wajar (terlalu tinggi/rendah untuk satuannya), satuan yang tidak cocok "
    "dengan jenis pekerjaan, atau TKDN mencurigakan. Jawab JSON saja."
)

SCHEMA_HINT = (
    '{"flags": [{"uraian": "<str>", "issue": "<str>", "severity": "<low|med|high>"}], '
    '"overall_ok": <bool>, "note": "<ringkas>"}'
)


def build_validator_prompt(items: list[dict]) -> str:
    """`items` = list {uraian, satuan, harga, tkdn}."""
    lines = ["Periksa kewajaran HSP berikut:"]
    for it in items[:80]:
        lines.append(
            f"- {it.get('uraian', '?')} | sat={it.get('satuan', '?')} | "
            f"HSP=Rp {it.get('harga', 0):,.0f} | TKDN={it.get('tkdn', 0)}"
        )
    lines.append("")
    lines.append("Tandai hanya yang benar-benar janggal.")
    return "\n".join(lines)
