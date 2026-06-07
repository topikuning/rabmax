"""Stage 4 — Vendor Discovery Agent (RABMAXPROMPT 4.3).

Lokasi-biased web search → ekstrak harga (WAJIB source_url + page_quote) → validasi
(tolak tanpa URL) → register vendor → simpan PriceSnapshot. Self-learning.

Web search via provider yang TERKONFIGURASI (Claude / OpenAI / Mistral — urut
default→fallback), bukan dipaksa satu provider. Ekstraktor di-inject agar testable;
default = live. Bila AI tak tersedia → 0 snapshot (resolver lanjut ke manual).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import current_year
from app.db.models import (
    KotaKabupaten,
    PriceSnapshot,
    Provinsi,
    Vendor,
)
from app.services.parser import normalize_text

SNAPSHOT_TTL_DAYS = 30
# Ekstraktor: (item, satuan, queries, lokasi) -> list[candidate dict]
ExtractorFn = Callable[..., Awaitable[list[dict]]]


def validate_candidate(c: dict) -> tuple[bool, str]:
    """Anti-halusinasi: WAJIB source_url + page_quote + harga>0 (RABMAXPROMPT §5)."""
    if not c.get("source_url"):
        return False, "tanpa source_url"
    if not str(c.get("page_quote", "")).strip() or len(str(c["page_quote"])) < 20:
        return False, "page_quote kosong/terlalu pendek"
    try:
        if float(c.get("harga", 0)) <= 0:
            return False, "harga <= 0"
    except (TypeError, ValueError):
        return False, "harga tidak valid"
    return True, ""


def build_queries(item: str, kota: str | None, provinsi: str | None, neighbors: list[str]) -> list[str]:
    y = current_year()
    areas = [a for a in [kota, provinsi, *neighbors] if a]
    q = [f"harga {item} {kota or ''} {provinsi or ''} {y}".strip()]
    if areas:
        q.append(f"jual {item} " + " OR ".join(areas[:4]))
    q.append(f"distributor {item} {provinsi or 'Indonesia'}")
    if kota:
        q.append(f"{item} kirim ke {kota}")
    return q


async def _provinsi_id_by_name(db: AsyncSession, name: str | None) -> int | None:
    if not name:
        return None
    n = normalize_text(name)
    rows = (await db.execute(select(Provinsi))).scalars().all()
    for p in rows:
        if n in normalize_text(p.nama) or n == normalize_text(p.nama_singkat or ""):
            return p.id
    return None


async def _kota_id_by_name(db: AsyncSession, name: str | None) -> tuple[int | None, int | None]:
    if not name:
        return None, None
    n = normalize_text(name)
    rows = (await db.execute(select(KotaKabupaten))).scalars().all()
    for k in rows:
        if n in normalize_text(k.nama):
            return k.id, k.provinsi_id
    return None, None


def _guess_source_type(domain: str) -> str:
    d = domain.lower()
    if any(x in d for x in ("tokopedia", "shopee", "bukalapak", "blibli", "lazada")):
        return "retail_marketplace"
    if any(x in d for x in ("indotrading", "ralali", "mbizmarket")):
        return "b2b_marketplace"
    if "lkpp" in d or "ekatalog" in d:
        return "lkpp"
    return "unknown"


async def register_vendor(db: AsyncSession, name: str, domain: str) -> Vendor:
    domain = (domain or "").lower().strip()
    v = (await db.execute(select(Vendor).where(Vendor.domain == domain))).scalar_one_or_none()
    if v:
        return v
    v = Vendor(name=name or domain, domain=domain, source_type=_guess_source_type(domain),
               reliability_score=0.5)
    db.add(v)
    await db.flush()
    return v


async def save_snapshots(
    db: AsyncSession, nama_material: str, satuan: str, tahun: int,
    candidates: list[dict], *, category_id: int | None = None,
    llm_provider: str | None = None, llm_model: str | None = None,
) -> tuple[int, list[str]]:
    """Validasi + register vendor + simpan PriceSnapshot. Return (jumlah, warnings)."""
    norm = normalize_text(nama_material)
    now = datetime.now(UTC)
    created = 0
    warnings: list[str] = []
    for c in candidates:
        ok, reason = validate_candidate(c)
        if not ok:
            warnings.append(f"ditolak: {reason}")
            continue
        domain = c.get("vendor_domain") or urlparse(c["source_url"]).netloc
        vendor = await register_vendor(db, c.get("vendor_name", ""), domain)
        prov_id = await _provinsi_id_by_name(db, c.get("vendor_provinsi"))
        kota_id, kota_prov = await _kota_id_by_name(db, c.get("vendor_kota"))
        prov_id = prov_id or kota_prov
        harga = float(c["harga"])
        harga_std = float(c.get("harga_standar") or harga)
        db.add(PriceSnapshot(
            vendor_id=vendor.id, category_id=category_id,
            nama_material=nama_material[:300], norm_nama=norm, satuan=satuan,
            merek=c.get("merek"), harga=harga,
            satuan_jual=c.get("satuan_jual"), konversi_factor=c.get("konversi_factor"),
            harga_standar=harga_std,
            source_url=str(c["source_url"])[:1000], page_quote=str(c["page_quote"]),
            discovered_via="ai_discovery",
            vendor_provinsi_id=prov_id, vendor_kota_id=kota_id,
            delivery_scope=c.get("delivery_scope"),
            expires_at=now + timedelta(days=SNAPSHOT_TTL_DAYS), tahun=tahun,
            confidence=float(c.get("confidence", 0.5) or 0.5),
            llm_provider=llm_provider, llm_model=llm_model, raw_response=c,
        ))
        vendor.total_snapshots += 1
        created += 1
    await db.flush()
    return created, warnings


async def discover_prices(
    db: AsyncSession, *, nama_material: str, satuan: str,
    kota_id: int | None, provinsi_id: int | None, tahun: int | None = None,
    extractor: ExtractorFn | None = None,
) -> int:
    """Discovery 1 material. extractor di-inject (test) / default live web_search."""
    tahun = tahun or current_year()
    kota = await db.get(KotaKabupaten, kota_id) if kota_id else None
    prov = await db.get(Provinsi, provinsi_id) if provinsi_id else None
    queries = build_queries(nama_material, kota.nama if kota else None,
                            prov.nama if prov else None, [])
    ext = extractor or _live_extractor
    try:
        candidates = await ext(item=nama_material, satuan=satuan, queries=queries,
                               kota=kota.nama if kota else None, provinsi=prov.nama if prov else None)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"Discovery extractor gagal '{nama_material}': {e}")
        return 0
    created, warnings = await save_snapshots(db, nama_material, satuan, tahun, candidates)
    if warnings:
        logger.info(f"Discovery '{nama_material}': {created} disimpan, {len(warnings)} ditolak")
    return created


def _extract_prompt(item: str, satuan: str, kota: str | None, provinsi: str | None) -> str:
    return (
        f"Cari harga terkini produk/jasa konstruksi '{item}' (satuan {satuan}) untuk lokasi "
        f"{kota or '-'}, {provinsi or '-'} Indonesia. Gunakan web search.\n"
        "Untuk tiap hasil dengan HARGA verifiable, keluarkan JSON array objek: "
        '{"vendor_name","vendor_domain","source_url","page_quote","harga",'
        '"satuan_jual","konversi_factor","harga_standar","vendor_kota","vendor_provinsi",'
        '"delivery_scope","merek","confidence"}. '
        "WAJIB source_url + page_quote (kutipan asli). Tanpa harga/URL → skip. "
        "Balas HANYA JSON array."
    )


def _parse_json_array(text: str) -> list[dict]:
    import json

    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1:
        return []
    try:
        out = json.loads(text[start : end + 1])
        return out if isinstance(out, list) else []
    except json.JSONDecodeError:
        return []


async def _ws_claude(prompt: str) -> str:
    from anthropic import AsyncAnthropic

    from app.config import settings

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=settings.default_ai_model_matcher, max_tokens=2048,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")


async def _ws_openai(prompt: str) -> str:
    from openai import AsyncOpenAI

    from app.config import settings

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    # Responses API + built-in web_search tool.
    resp = await client.responses.create(
        model="gpt-4o", tools=[{"type": "web_search"}], input=prompt,
    )
    return getattr(resp, "output_text", "") or ""


async def _ws_mistral(prompt: str) -> str:
    from app.ai.client import _import_mistral
    from app.config import settings

    mistral_cls = _import_mistral()
    client = mistral_cls(api_key=settings.mistral_api_key)
    # Agents API: agent dengan connector web_search → conversation.
    agent = await client.beta.agents.create_async(
        model="mistral-large-latest", name="rabmax-pricing",
        description="Cari harga material konstruksi", tools=[{"type": "web_search"}],
    )
    conv = await client.beta.conversations.start_async(agent_id=agent.id, inputs=prompt)
    out = ""
    for entry in getattr(conv, "outputs", []) or []:
        content = getattr(entry, "content", None)
        if isinstance(content, str):
            out += content
        elif isinstance(content, list):
            out += "".join(getattr(x, "text", "") for x in content)
    return out


_WS = {"claude": _ws_claude, "openai": _ws_openai, "mistral": _ws_mistral}


async def _live_extractor(*, item, satuan, queries, kota, provinsi) -> list[dict]:
    """Discovery via web search provider YANG TERKONFIGURASI (urut: default → fallback).

    Tidak dipaksa Anthropic — pakai Claude / OpenAI / Mistral sesuai key yang ada.
    Final-verify di deploy (sandbox blokir jaringan)."""
    from app.ai.client import provider_status
    from app.config import settings

    prompt = _extract_prompt(item, satuan, kota, provinsi)
    st = provider_status()
    order = [settings.default_ai_provider] + [
        p for p in settings.ai_fallback_order if p != settings.default_ai_provider
    ]
    for prov in order:
        if not st.get(prov, {}).get("configured"):
            continue
        try:
            text = await _WS[prov](prompt)
            cands = _parse_json_array(text)
            if cands:
                logger.info(f"Discovery web_search via {prov}: {len(cands)} kandidat")
                return cands
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Discovery {prov} web_search gagal: {e}")
            continue
    return []
