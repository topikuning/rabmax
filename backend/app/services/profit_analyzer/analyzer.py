"""Mode B — Profit Analyzer.

Pipeline:
  1. Parse RAB terisi -> HPS per item (harga × volume).
  2. Estimasi biaya real per item:
       a. pakai ItemMatch.final_hsp bila pricing sudah jalan (Stage 3),
       b. fallback LLM (estimasi biaya material+upah, tanpa profit),
       c. last-resort: rasio asumsi terhadap HPS (low confidence).
  3. Profit per item & agregasi per paket.
  4. Identifikasi item berisiko (margin tipis/negatif).
  5. Narasi ringkasan (LLM).
  6. Persist ProfitAnalysis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import AIMessage, ai_client
from app.ai.prompts import profit_summary as ps_prompt
from app.config import settings
from app.db.models import (
    ItemMatch,
    PaketItem,
    ProfitAnalysis,
    Project,
)
from app.services.parser import parse_filled_rab

# Asumsi default.
PPN_RATE = 0.11
DEFAULT_COST_RATIO = 0.85  # fallback: cost ≈ 85% HPS (low confidence)
RISK_MARGIN_PCT = 5.0  # item dengan margin < 5% dianggap berisiko

_COST_SYSTEM = (
    "Anda estimator konstruksi Indonesia. Estimasi BIAYA REAL (material + upah + "
    "alat, TANPA profit kontraktor) per satuan untuk item pekerjaan, berdasarkan "
    "harga pasar terkini. Jawab JSON saja."
)
_COST_SCHEMA = '{"unit_cost": <number rupiah/satuan>, "confidence": <float 0-1>}'


@dataclass
class _ItemCost:
    uraian: str
    satuan: str
    volume: float
    hps_unit: float
    hps_jumlah: float
    cost_unit: float
    resolved: bool
    sheet_name: str

    @property
    def cost_total(self) -> float:
        return self.cost_unit * self.volume

    @property
    def profit(self) -> float:
        return self.hps_jumlah - self.cost_total

    @property
    def margin_pct(self) -> float:
        if self.hps_jumlah <= 0:
            return 0.0
        return self.profit / self.hps_jumlah * 100.0


@dataclass
class ProfitRunResult:
    analysis_id: int | None = None
    items_total: int = 0
    items_resolved: int = 0
    warnings: list[str] = field(default_factory=list)


async def _estimate_unit_cost(uraian: str, satuan: str, use_llm: bool) -> tuple[float, bool]:
    """Return (unit_cost, resolved). resolved=False berarti pakai fallback rasio."""
    if not use_llm:
        return 0.0, False
    messages = [
        AIMessage(role="system", content=_COST_SYSTEM),
        AIMessage(
            role="user",
            content=f"Item: {uraian}\nSatuan: {satuan}\nEstimasi biaya real per satuan.",
        ),
    ]
    try:
        data = await ai_client.complete_json(
            messages,
            schema_hint=_COST_SCHEMA,
            model=settings.default_ai_model_profit,
            max_tokens=200,
        )
        cost = float(data["unit_cost"])
        return cost, cost > 0
    except Exception as e:  # noqa: BLE001
        logger.warning(f"LLM cost estimate gagal '{uraian}': {e}")
        return 0.0, False


async def run_profit_analysis(
    project_id: int,
    db: AsyncSession,
    use_llm: bool = True,
) -> ProfitRunResult:
    """Jalankan analisa profit Mode B, persist ProfitAnalysis."""
    project = await db.get(Project, project_id)
    if project is None:
        raise ValueError(f"Project {project_id} tidak ditemukan")
    if not project.input_file_path:
        raise ValueError("Project belum punya file RAB terisi yang di-upload.")

    file_path = settings.storage_path / project.input_file_path
    if not Path(file_path).exists():
        raise ValueError(f"File tidak ditemukan: {file_path}")

    parsed = parse_filled_rab(file_path)

    # Map paket_item -> final_hsp (jika pricing/match sudah jalan), keyed by (sheet,row).
    match_rows = list(
        (
            await db.execute(
                select(PaketItem, ItemMatch)
                .join(ItemMatch, ItemMatch.paket_item_id == PaketItem.id)
                .where(PaketItem.project_id == project_id)
            )
        ).all()
    )
    hsp_by_loc = {
        (pi.sheet_name, pi.excel_row): float(m.final_hsp)
        for pi, m in match_rows
        if m.final_hsp is not None
    }

    # Cache estimasi cost per unique uraian.
    cost_cache: dict[tuple[str, str], tuple[float, bool]] = {}
    item_costs: list[_ItemCost] = []

    for it in parsed.items:
        if it.harga is None and it.jumlah is None:
            continue  # bukan baris berharga
        hps_unit = float(it.harga or 0.0)
        hps_jumlah = float(it.jumlah if it.jumlah is not None else hps_unit * it.volume)

        loc_hsp = hsp_by_loc.get((it.sheet_name, it.excel_row))
        if loc_hsp and loc_hsp > 0:
            cost_unit, resolved = loc_hsp, True
        else:
            key = (it.norm_uraian, it.norm_satuan)
            if key not in cost_cache:
                cost_cache[key] = await _estimate_unit_cost(it.uraian, it.satuan, use_llm)
            cost_unit, resolved = cost_cache[key]
            if not resolved:
                cost_unit = hps_unit * DEFAULT_COST_RATIO  # fallback rasio

        item_costs.append(
            _ItemCost(
                uraian=it.uraian,
                satuan=it.satuan,
                volume=it.volume,
                hps_unit=hps_unit,
                hps_jumlah=hps_jumlah,
                cost_unit=cost_unit,
                resolved=resolved,
                sheet_name=it.sheet_name,
            )
        )

    if not item_costs:
        raise ValueError("Tidak ada item berharga ditemukan di file (cek apakah RAB terisi).")

    hps_total = sum(c.hps_jumlah for c in item_costs)
    cost_total = sum(c.cost_total for c in item_costs)
    gross_profit = hps_total - cost_total
    margin_pct = (gross_profit / hps_total * 100.0) if hps_total > 0 else 0.0

    # Per paket breakdown.
    per_paket: dict[str, dict] = {}
    for c in item_costs:
        p = per_paket.setdefault(
            c.sheet_name, {"nama": c.sheet_name, "hps": 0.0, "cost": 0.0}
        )
        p["hps"] += c.hps_jumlah
        p["cost"] += c.cost_total
    per_paket_list = []
    for p in per_paket.values():
        profit = p["hps"] - p["cost"]
        p["profit"] = round(profit, 2)
        p["margin_pct"] = round(profit / p["hps"] * 100.0, 2) if p["hps"] > 0 else 0.0
        p["hps"] = round(p["hps"], 2)
        p["cost"] = round(p["cost"], 2)
        per_paket_list.append(p)

    # Risk items.
    risk_items = [
        {
            "uraian": c.uraian,
            "sheet": c.sheet_name,
            "hps": round(c.hps_jumlah, 2),
            "cost": round(c.cost_total, 2),
            "margin_pct": round(c.margin_pct, 2),
        }
        for c in item_costs
        if c.margin_pct < RISK_MARGIN_PCT
    ]
    risk_items.sort(key=lambda r: r["margin_pct"])

    items_resolved = sum(1 for c in item_costs if c.resolved)
    confidence = round(items_resolved / len(item_costs), 3) if item_costs else 0.0

    # AI narrative.
    ai_summary = None
    if use_llm:
        try:
            resp = await ai_client.complete(
                [
                    AIMessage(role="system", content=ps_prompt.SYSTEM),
                    AIMessage(
                        role="user",
                        content=ps_prompt.build_profit_summary_prompt(
                            hps_total, cost_total, gross_profit, margin_pct,
                            per_paket_list, risk_items,
                        ),
                    ),
                ],
                model=settings.default_ai_model_profit,
                max_tokens=1024,
            )
            ai_summary = resp.text.strip()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"LLM profit summary gagal: {e}")

    analysis = ProfitAnalysis(
        project_id=project_id,
        hps_total=round(hps_total, 2),
        hps_total_incl_ppn=round(hps_total * (1 + PPN_RATE), 2),
        estimated_cost_total=round(cost_total, 2),
        estimated_cost_breakdown={
            "total": round(cost_total, 2),
            "method": "match_hsp+llm+ratio_fallback",
        },
        gross_profit=round(gross_profit, 2),
        gross_profit_margin_pct=round(margin_pct, 2),
        risk_items=risk_items,
        per_paket_breakdown=per_paket_list,
        assumptions={
            "ppn_rate": PPN_RATE,
            "default_cost_ratio_fallback": DEFAULT_COST_RATIO,
            "risk_margin_pct": RISK_MARGIN_PCT,
        },
        ai_summary=ai_summary,
        confidence=confidence,
        items_resolved=items_resolved,
        items_total=len(item_costs),
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    logger.info(
        f"Profit analysis project {project_id}: HPS={hps_total:.0f} cost={cost_total:.0f} "
        f"margin={margin_pct:.1f}% resolved={items_resolved}/{len(item_costs)}"
    )
    return ProfitRunResult(
        analysis_id=analysis.id,
        items_total=len(item_costs),
        items_resolved=items_resolved,
        warnings=parsed.warnings,
    )
