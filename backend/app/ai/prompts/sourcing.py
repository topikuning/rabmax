"""Prompt untuk Stage 3 — sourcing harga material yang tidak ada di DB.

LLM mengisi estimasi harga distributor terkini + TKDN + sitasi sumber.
"""

from __future__ import annotations

SYSTEM = (
    "Anda asisten pengadaan material konstruksi Indonesia. Berikan estimasi harga "
    "satuan WAJAR untuk material/upah/alat sesuai harga pasar/distributor terkini "
    "di Indonesia. Sertakan estimasi komponen TKDN (0-1, 1=100% produksi lokal) dan "
    "label sumber yang jelas. Jika ragu, beri rentang konservatif dan turunkan "
    "confidence. Jangan mengarang merk spesifik bila tidak diminta."
)

SCHEMA_HINT = (
    '{"harga": <number rupiah/satuan>, "satuan": "<satuan>", '
    '"tkdn_factor": <float 0-1>, "tier": "<A|B|C|D>", '
    '"source_label": "<sitasi singkat>", "confidence": <float 0-1>}'
)


def build_sourcing_prompt(
    nama: str,
    satuan: str,
    kategori: str,
    provinsi: str | None = None,
    tahun: int | None = None,
) -> str:
    ctx = []
    if provinsi:
        ctx.append(f"Provinsi: {provinsi}")
    if tahun:
        ctx.append(f"Tahun harga: {tahun}")
    ctx_str = (" (" + ", ".join(ctx) + ")") if ctx else ""
    return (
        f"Estimasi harga satuan untuk {kategori}{ctx_str}:\n"
        f"- Nama   : {nama}\n"
        f"- Satuan : {satuan}\n\n"
        "Berikan harga satuan wajar, komponen TKDN, tier sumber, dan sitasi."
    )
