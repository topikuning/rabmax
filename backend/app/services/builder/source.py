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
from app.config import current_year, settings
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
    satuan: str | None = None,
) -> BahanUpahItem | None:
    """Cari harga material di DB by nama, prefer COCOK PERSIS (normalized), tier & lokasi.

    Substring (ILIKE) dipakai untuk menjaring kandidat, tapi ranking mengutamakan nama
    yang sama persis (normalized) agar 'Air' tak salah ambil 'Automatic Air Vent'.
    """
    norm = normalize_text(nama)
    # ilike contains pada nama; harga>0 saja (skip baris katalog kosong dari AHSP).
    stmt = select(BahanUpahItem).where(
        BahanUpahItem.nama.ilike(f"%{norm}%"), BahanUpahItem.harga > 0
    )
    if provinsi:
        stmt = stmt.where(
            (BahanUpahItem.provinsi == provinsi) | (BahanUpahItem.provinsi.is_(None))
        )
    rows = list((await db.execute(stmt)).scalars().all())
    if not rows:
        return None
    # Ranking: cocok-persis → satuan cocok → tier A>B>C>D → nama terpendek → tahun.
    tier_rank = {SourceTier.A: 0, SourceTier.B: 1, SourceTier.C: 2, SourceTier.D: 3}
    nsat = normalize_text(satuan) if satuan else None
    rows.sort(key=lambda r: (
        normalize_text(r.nama) != norm,
        bool(nsat) and normalize_text(r.satuan) != nsat,
        tier_rank.get(SourceTier(r.tier), 9),
        len(r.nama),
        -(r.tahun or 0),
    ))
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

    # Bila sudah ada baris katalog (harga 0) untuk material ini, ISI harganya
    # (bukan bikin duplikat). Match by nama persis.
    existing = (
        await db.execute(select(BahanUpahItem).where(BahanUpahItem.nama == nama))
    ).scalar_one_or_none()
    item = existing or BahanUpahItem(nama=nama)
    item.satuan = data.get("satuan") or satuan
    item.harga = harga
    item.category = (
        BahanUpahCategory(kategori) if kategori in {"bahan", "upah", "alat"}
        else BahanUpahCategory.BAHAN
    )
    item.tier = tier
    item.tkdn_factor = float(data.get("tkdn_factor", 1.0) or 1.0)
    item.source_label = str(data.get("source_label", "AI-sourced"))[:300]
    item.provinsi = provinsi
    item.tahun = tahun or current_year()
    item.ai_generated = True
    item.notes = f"AI-sourced (confidence={data.get('confidence', 0)})"
    if cache and existing is None:
        db.add(item)
    if cache:
        await db.flush()
    return item


async def source_ahsp_components(
    ahsp: AHSPCode,
    db: AsyncSession,
    provinsi: str | None = None,
    tahun: int | None = None,
    use_llm: bool = True,
    *,
    kota_id: int | None = None,
    provinsi_id: int | None = None,
    user_id: int | None = None,
    discovery=None,
) -> list[PricedComponent]:
    """Resolusi harga semua komponen sebuah AHSP -> PricedComponent list.

    Prioritas per komponen:
      1. Harga katalog ter-link (FK bahan_upah_id, harga>0).
      2. Resolver lokasi-aware (Tier 1-6: consensus kota/provinsi/tetangga/nasional
         + transport + discovery + manual) — hanya bila `kota_id`/`provinsi_id` diberi.
      3. Harga satuan nasional resmi (AHSP CK 2026, tersimpan di komponen) — baseline
         akurat tanpa lookup fuzzy.
      4. Lookup katalog by nama (nasional/curated) — untuk komponen tanpa harga resmi.
      5. Fallback LLM sourcing (interim).
    """
    # Lazy import: hindari circular (pricing.__init__ -> legacy -> builder.source).
    from app.services.pricing.resolver import resolve_price

    components = list(
        (
            await db.execute(
                select(AHSPComponent).where(AHSPComponent.ahsp_id == ahsp.id)
            )
        ).scalars().all()
    )
    use_resolver = kota_id is not None or provinsi_id is not None
    yr = tahun or current_year()
    priced: list[PricedComponent] = []
    for comp in components:
        harga = 0.0
        tkdn = 1.0
        src = "kosong"

        # 1. Harga katalog ter-link (FK).
        if comp.bahan_upah_id:
            bu = await db.get(BahanUpahItem, comp.bahan_upah_id)
            if bu and bu.harga and float(bu.harga) > 0:
                harga, tkdn, src = float(bu.harga), float(bu.tkdn_factor), "katalog"

        # 2. Resolver lokasi-aware (per-kota → beda Malang vs Surabaya).
        if harga <= 0 and use_resolver:
            rr = await resolve_price(
                db, comp.nama_material, comp.satuan, kota_id, provinsi_id, yr,
                user_id=user_id, discovery=discovery,
            )
            if rr.harga_final and rr.harga_final > 0:
                harga = float(rr.harga_final)
                src = rr.tier_used
                # Resolver tak bawa TKDN → best-effort dari katalog.
                cat = await _lookup_db_price(db, comp.nama_material, provinsi, tahun, comp.satuan)
                tkdn = float(cat.tkdn_factor) if cat else 1.0

        # 3. Harga satuan nasional resmi (baseline akurat, tanpa lookup fuzzy).
        if harga <= 0 and comp.harga_satuan and float(comp.harga_satuan) > 0:
            harga, src = float(comp.harga_satuan), "nasional"

        # 4. Lookup katalog by nama (nasional/curated) — komponen tanpa harga resmi.
        if harga <= 0:
            cat = await _lookup_db_price(db, comp.nama_material, provinsi, tahun, comp.satuan)
            if cat:
                harga, tkdn, src = float(cat.harga), float(cat.tkdn_factor), "katalog-nama"

        # 5. Fallback LLM sourcing (interim).
        if harga <= 0 and use_llm:
            llm = await _llm_source_price(
                db, comp.nama_material, comp.satuan, comp.kategori, provinsi, tahun
            )
            if llm:
                harga, tkdn, src = float(llm.harga), float(llm.tkdn_factor), "ai"

        priced.append(
            PricedComponent(
                kategori=str(comp.kategori),
                nama=comp.nama_material,
                koefisien=float(comp.koefisien),
                harga=harga,
                satuan=comp.satuan,
                formula_modifier=comp.formula_modifier,
                tkdn_factor=tkdn,
                source_tier=src,
            )
        )
    return priced


# Tier sumber harga → label Indonesia untuk audit (sheet "Sumber Harga").
_SRC_LABEL = {
    "katalog": "Katalog harga",
    "katalog-nama": "Katalog (cocok nama)",
    "official_kota": "SSH resmi kota",
    "official_provinsi": "SSH resmi provinsi",
    "kota_lokal": "Konsensus kota",
    "provinsi_lokal": "Konsensus provinsi (+transport)",
    "provinsi_tetangga": "Provinsi tetangga (+transport)",
    "nasional_markup": "Nasional (+markup)",
    "nasional": "Baseline nasional (AHSP CK)",
    "discovery": "AI discovery (web)",
    "manual": "Override manual",
    "ai": "AI sourcing",
    "kosong": "Belum ada harga",
}


def summarize_sources(priced: list[PricedComponent]) -> str:
    """Ringkas tier sumber harga komponen → string audit, mis.
    'SSH resmi kota ×5 · Baseline nasional ×8'. Urut terbanyak dulu."""
    from collections import Counter

    counts = Counter(p.source_tier or "kosong" for p in priced)
    parts = [
        f"{_SRC_LABEL.get(tier, tier)} ×{n}"
        for tier, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    ]
    return " · ".join(parts)


async def price_match(
    match: ItemMatch,
    db: AsyncSession,
    provinsi: str | None = None,
    tahun: int | None = None,
    op_rate: float = 0.10,
    use_llm: bool = True,
    *,
    kota_id: int | None = None,
    provinsi_id: int | None = None,
    user_id: int | None = None,
    discovery=None,
) -> HSPResult | None:
    """Hitung & set final_hsp + tkdn_factor untuk satu ItemMatch.

    AHSP -> compute dari komponen (lokasi-aware bila kota_id/provinsi_id diberi).
    LUMPSUM -> pakai lumpsum_price langsung. Return HSPResult (None untuk
    lumpsum/unresolved).
    """
    if match.match_type == MatchType.LUMPSUM and match.lumpsum_price is not None:
        match.final_hsp = float(match.lumpsum_price)
        if match.tkdn_factor is None:
            match.tkdn_factor = 1.0
        match.price_source = "Lumpsum (input user)"
        return None

    if match.match_type == MatchType.AHSP and match.ahsp_id:
        ahsp = await db.get(AHSPCode, match.ahsp_id)
        if ahsp is None:
            return None
        priced = await source_ahsp_components(
            ahsp, db, provinsi, tahun, use_llm,
            kota_id=kota_id, provinsi_id=provinsi_id, user_id=user_id, discovery=discovery,
        )
        result = compute_hsp(priced, op_rate=op_rate)
        match.final_hsp = round(result.hsp, 2)
        match.tkdn_factor = result.tkdn_factor
        match.price_source = summarize_sources(priced)[:300]
        return result

    return None
