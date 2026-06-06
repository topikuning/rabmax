"""Stage 3 — Source: lengkapi harga komponen AHSP.

Strategi per komponen:
  1. Jika sudah ter-link ke bahan_upah_items (FK), pakai harga itu.
  2. Cari di DB by nama (normalized contains).
  3. Fallback LLM (cari harga distributor terkini) -> cache ke DB (tier C/D).

Hasil di-feed ke `hsp_calculator.compute_hsp`.
"""

from __future__ import annotations

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIMessage, ai_client
from app.ai.prompts import sourcing as sourcing_prompt
from app.config import settings
from app.db.models import (
    AHSPCode,
    AHSPComponent,
    BahanUpahCategory,
    BahanUpahItem,
    ItemMatch,
    MatchType,
    SourceTier,
)
from app.services.builder.hsp_calculator import (
    HSPResult,
    PricedComponent,
    compute_hsp,
)
from app.services.parser import normalize_text


async def _lookup_db_price(
    db: AsyncSession,
    nama: str,
    provinsi: str | None,
    tahun: int | None,
) -> BahanUpahItem | None:
    """Cari harga material di DB by nama (normalized substring), prefer tier & lokasi."""
    norm = normalize_text(nama)
    # ilike contains pada nama; SQLite/Postgres sama-sama dukung.
    stmt = select(BahanUpahItem).where(BahanUpahItem.nama.ilike(f"%{norm}%"))
    if provinsi:
        stmt = stmt.where(
            (BahanUpahItem.provinsi == provinsi) | (BahanUpahItem.provinsi.is_(None))
        )
    rows = list((await db.execute(stmt)).scalars().all())
    if not rows:
        return None
    # Prefer tier A>B>C>D, lalu tahun terbaru.
    tier_rank = {SourceTier.A: 0, SourceTier.B: 1, SourceTier.C: 2, SourceTier.D: 3}
    rows.sort(key=lambda r: (tier_rank.get(SourceTier(r.tier), 9), -(r.tahun or 0)))
    return rows[0]


async def _llm_source_price(
    db: AsyncSession,
    nama: str,
    satuan: str,
    kategori: str,
    provinsi: str | None,
    tahun: int | None,
    cache: bool = True,
) -> BahanUpahItem | None:
    """Cari harga via LLM, lalu cache ke DB supaya lookup berikutnya hit."""
    messages = [
        AIMessage(role="system", content=sourcing_prompt.SYSTEM),
        AIMessage(
            role="user",
            content=sourcing_prompt.build_sourcing_prompt(
                nama, satuan, kategori, provinsi, tahun
            ),
        ),
    ]
    try:
        data = await ai_client.complete_json(
            messages,
            schema_hint=sourcing_prompt.SCHEMA_HINT,
            model=settings.default_ai_model_profit,
            max_tokens=400,
        )
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM sourcing gagal untuk '{nama}': {e}")
        return None

    try:
        harga = float(data["harga"])
    except (KeyError, TypeError, ValueError):
        logger.warning(f"LLM sourcing tak punya harga valid untuk '{nama}'")
        return None

    tier_raw = str(data.get("tier", "D")).upper()
    tier = SourceTier(tier_raw) if tier_raw in {"A", "B", "C", "D"} else SourceTier.D

    item = BahanUpahItem(
        nama=nama,
        satuan=data.get("satuan") or satuan,
        harga=harga,
        category=BahanUpahCategory(kategori) if kategori in {"bahan", "upah", "alat"} else BahanUpahCategory.BAHAN,
        tier=tier,
        tkdn_factor=float(data.get("tkdn_factor", 1.0) or 1.0),
        source_label=str(data.get("source_label", "AI-sourced"))[:300],
        provinsi=provinsi,
        tahun=tahun or 2025,
        ai_generated=True,
        notes=f"AI-sourced (confidence={data.get('confidence', 0)})",
    )
    if cache:
        db.add(item)
        await db.flush()
    return item


async def source_ahsp_components(
    ahsp: AHSPCode,
    db: AsyncSession,
    provinsi: str | None = None,
    tahun: int | None = None,
    use_llm: bool = True,
) -> list[PricedComponent]:
    """Resolusi harga semua komponen sebuah AHSP -> PricedComponent list."""
    components = list(
        (
            await db.execute(
                select(AHSPComponent).where(AHSPComponent.ahsp_id == ahsp.id)
            )
        ).scalars().all()
    )
    priced: list[PricedComponent] = []
    for comp in components:
        bu: BahanUpahItem | None = None
        if comp.bahan_upah_id:
            bu = await db.get(BahanUpahItem, comp.bahan_upah_id)
        if bu is None:
            bu = await _lookup_db_price(db, comp.nama_material, provinsi, tahun)
        if bu is None and use_llm:
            bu = await _llm_source_price(
                db, comp.nama_material, comp.satuan, comp.kategori, provinsi, tahun
            )

        harga = float(bu.harga) if bu else 0.0
        tkdn = float(bu.tkdn_factor) if bu else 1.0
        priced.append(
            PricedComponent(
                kategori=str(comp.kategori),
                nama=comp.nama_material,
                koefisien=float(comp.koefisien),
                harga=harga,
                satuan=comp.satuan,
                formula_modifier=comp.formula_modifier,
                tkdn_factor=tkdn,
            )
        )
    return priced


async def price_match(
    match: ItemMatch,
    db: AsyncSession,
    provinsi: str | None = None,
    tahun: int | None = None,
    op_rate: float = 0.10,
    use_llm: bool = True,
) -> HSPResult | None:
    """Hitung & set final_hsp + tkdn_factor untuk satu ItemMatch.

    AHSP -> compute dari komponen. LUMPSUM -> pakai lumpsum_price langsung.
    Return HSPResult (None untuk lumpsum/unresolved).
    """
    if match.match_type == MatchType.LUMPSUM and match.lumpsum_price is not None:
        match.final_hsp = float(match.lumpsum_price)
        if match.tkdn_factor is None:
            match.tkdn_factor = 1.0
        return None

    if match.match_type == MatchType.AHSP and match.ahsp_id:
        ahsp = await db.get(AHSPCode, match.ahsp_id)
        if ahsp is None:
            return None
        priced = await source_ahsp_components(ahsp, db, provinsi, tahun, use_llm)
        result = compute_hsp(priced, op_rate=op_rate)
        match.final_hsp = round(result.hsp, 2)
        match.tkdn_factor = result.tkdn_factor
        return result

    return None
