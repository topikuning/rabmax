"""Prompt untuk Mode B — narasi ringkasan analisa profit."""

from __future__ import annotations

SYSTEM = (
    "Anda konsultan estimasi proyek lelang pemerintah Indonesia (LKPP). Buat "
    "ringkasan analisa profit yang ringkas, tajam, dan actionable untuk pengambil "
    "keputusan. Soroti margin keseluruhan, paket dengan margin tipis/negatif "
    "(risiko), dan rekomendasi strategi penawaran dalam band 80-120% HPS. "
    "Gunakan Bahasa Indonesia, format ringkas berbutir."
)


def build_profit_summary_prompt(
    hps_total: float,
    estimated_cost: float,
    gross_profit: float,
    margin_pct: float,
    per_paket: list[dict],
    risk_items: list[dict],
) -> str:
    lines = [
        "DATA ANALISA PROFIT:",
        f"- HPS total          : Rp {hps_total:,.0f}",
        f"- Estimasi cost real : Rp {estimated_cost:,.0f}",
        f"- Gross profit       : Rp {gross_profit:,.0f}",
        f"- Margin             : {margin_pct:.2f}%",
        "",
        "PER PAKET:",
    ]
    for p in per_paket[:30]:
        lines.append(
            f"- {p.get('nama', '?')}: HPS Rp {p.get('hps', 0):,.0f}, "
            f"cost Rp {p.get('cost', 0):,.0f}, margin {p.get('margin_pct', 0):.1f}%"
        )
    if risk_items:
        lines.append("")
        lines.append(f"ITEM BERISIKO ({len(risk_items)}):")
        for r in risk_items[:15]:
            lines.append(
                f"- {r.get('uraian', '?')}: margin {r.get('margin_pct', 0):.1f}%"
            )
    lines.append("")
    lines.append(
        "Buat ringkasan eksekutif (maks ~200 kata) + 3-5 rekomendasi konkret."
    )
    return "\n".join(lines)
