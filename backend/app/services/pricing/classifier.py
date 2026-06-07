"""Stage 2 — Item Classifier (RABMAXPROMPT 4.1).

Cache lookup → (LLM bila ada) → fallback keyword match ke item_categories.
Hasil di-cache di item_classifications. Keyword fallback membuat ini tetap jalan
& testable tanpa LLM.
"""

from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIMessage, ai_client, any_provider_configured
from app.db.models import ItemCategory, ItemClassification
from app.services.parser import normalize_text


@dataclass
class ClassifyResult:
    classification_id: int
    category_id: int | None
    category_code: str | None
    detected_brand: str | None
    confidence: float
    method: str  # cache | llm | keyword | none


async def _keyword_category(db: AsyncSession, norm: str) -> tuple[ItemCategory | None, float]:
    """Cocokkan nama ter-normalisasi ke item_categories via keyword/nama (deterministik)."""
    cats = list((await db.execute(select(ItemCategory))).scalars().all())
    best: ItemCategory | None = None
    best_score = 0
    for c in cats:
        score = 0
        for kw in (c.search_keywords or []):
            if kw.lower() in norm:
                score += 2
        # nama kategori token overlap
        for tok in normalize_text(c.name).split():
            if len(tok) > 3 and tok in norm:
                score += 1
        if score > best_score:
            best_score, best = score, c
    conf = min(0.6, 0.3 + 0.1 * best_score) if best else 0.0
    return best, round(conf, 3)


async def classify_item(
    db: AsyncSession, nama_material: str, satuan: str, *, use_llm: bool = True
) -> ClassifyResult:
    norm = normalize_text(nama_material)
    sat = normalize_text(satuan)

    # 1) cache
    existing = (
        await db.execute(
            select(ItemClassification).where(
                ItemClassification.norm_item_name == norm,
                ItemClassification.satuan == sat,
            )
        )
    ).scalar_one_or_none()
    if existing:
        code = None
        if existing.category_id:
            cat = await db.get(ItemCategory, existing.category_id)
            code = cat.code if cat else None
        return ClassifyResult(existing.id, existing.category_id, code,
                              existing.detected_brand, float(existing.confidence), "cache")

    method = "keyword"
    brand = None
    cat_obj, conf = await _keyword_category(db, norm)
    category_id = cat_obj.id if cat_obj else None

    # 2) LLM (kalau ada provider) — boleh menimpa kategori keyword bila lebih yakin
    if use_llm and any_provider_configured():
        try:
            cats = list((await db.execute(select(ItemCategory))).scalars().all())
            catalogue = "\n".join(f"{c.code} = {c.name}" for c in cats[:80])
            data = await ai_client.complete_json(
                [
                    AIMessage(role="system", content="Anda pakar material konstruksi Indonesia. Jawab JSON."),
                    AIMessage(role="user", content=(
                        f"Klasifikasi item:\n- Nama: {nama_material}\n- Satuan: {satuan}\n\n"
                        f"Pilih category_code dari daftar:\n{catalogue}\n"
                    )),
                ],
                schema_hint='{"category_code": "<code|null>", "detected_brand": "<str|null>", "confidence": <0-1>}',
                max_tokens=200,
            )
            code = data.get("category_code")
            if code:
                m = next((c for c in cats if c.code == code), None)
                if m:
                    category_id, conf, method = m.id, float(data.get("confidence", 0.7) or 0.7), "llm"
            brand = data.get("detected_brand")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"LLM classify gagal '{nama_material}': {e}")

    row = ItemClassification(
        norm_item_name=norm, satuan=sat, category_id=category_id,
        detected_brand=brand, confidence=conf, classifier_llm=method,
    )
    db.add(row)
    await db.flush()
    code = cat_obj.code if (cat_obj and category_id == cat_obj.id) else None
    if category_id and not code:
        c = await db.get(ItemCategory, category_id)
        code = c.code if c else None
    return ClassifyResult(row.id, category_id, code, brand, conf, method if category_id else "none")
