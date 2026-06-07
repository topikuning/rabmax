"""Seed taxonomy item_categories (top kategori material konstruksi) + material_logistics.

Idempotent (upsert by code). Inti `apply_taxonomy(db)` dipakai CLI & auto-seed.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ItemCategory, MaterialLogistics
from app.db.session import AsyncSessionLocal

# (code, name, standard_unit, brands, keywords, berat_jenis_kg_per_m3, preferred_mode)
TAXONOMY: list[tuple] = [
    ("beton.semen.portland", "Semen Portland", "kg", ["Tiga Roda", "Holcim", "Conch", "Gresik"], ["semen", "pc", "portland"], 1250, "truk_fuso"),
    ("beton.readymix", "Beton Ready Mix", "m3", ["Pionir", "Holcim", "SCG"], ["readymix", "beton cor", "k-225", "fc"], 2400, "truk_tronton"),
    ("beton.agregat.pasir", "Pasir Beton/Pasang", "m3", [], ["pasir", "pasir beton", "pasir pasang"], 1400, "truk_fuso"),
    ("beton.agregat.kerikil", "Agregat Kasar/Kerikil/Split", "m3", [], ["split", "kerikil", "batu pecah", "agregat kasar"], 1350, "truk_fuso"),
    ("baja.tulangan.polos", "Besi Beton Polos", "kg", ["KS", "Master Steel", "Hanil"], ["besi polos", "tulangan polos", "bjtp"], 7856, "truk_tronton"),
    ("baja.tulangan.ulir", "Besi Beton Ulir", "kg", ["KS", "Master Steel", "Cakratunggal"], ["besi ulir", "tulangan ulir", "bjts", "d10", "d13"], 7856, "truk_tronton"),
    ("baja.wiremesh", "Wiremesh", "m2", [], ["wiremesh", "wire mesh", "m8", "m10"], 7856, "truk_tronton"),
    ("baja.profil", "Baja Profil (WF/H/Kanal)", "kg", ["KS", "Gunung Garuda"], ["wf", "h beam", "cnp", "unp", "siku"], 7850, "truk_tronton"),
    ("baja.ringan", "Baja Ringan", "m", ["Taso", "Kencana", "Bluescope"], ["baja ringan", "kanal c", "reng", "truss"], 7850, "truk_fuso"),
    ("kayu.balok", "Kayu Balok", "m3", [], ["kayu", "balok kayu", "kaso", "reng kayu"], 800, "truk_fuso"),
    ("kayu.papan", "Kayu Papan/Multipleks", "lembar", ["Sengon", "Meranti"], ["multiplek", "triplek", "plywood", "papan"], 700, "truk_fuso"),
    ("bata.merah", "Bata Merah", "buah", [], ["bata merah", "batu bata"], 1700, "truk_fuso"),
    ("bata.ringan", "Bata Ringan (Hebel)", "m3", ["Citicon", "Hebel", "Falcon"], ["bata ringan", "hebel", "celcon", "aac"], 600, "truk_fuso"),
    ("bata.batako", "Batako", "buah", [], ["batako", "conblock"], 2000, "truk_fuso"),
    ("dinding.semen_instan", "Semen Instan/Mortar", "kg", ["MU", "Drymix", "Aplus"], ["mortar", "semen instan", "perekat bata"], 1300, "truk_fuso"),
    ("lantai.keramik", "Keramik Lantai/Dinding", "m2", ["Roman", "Mulia", "Platinum"], ["keramik", "tile", "granit tile"], 1800, "truk_fuso"),
    ("lantai.granit", "Granit Tile/Homogeneous", "m2", ["Granito", "Niro", "Indogress"], ["granit", "homogeneous", "ht"], 2000, "truk_fuso"),
    ("atap.genteng", "Genteng", "buah", ["KIA", "Kanmuri", "Jatiwangi"], ["genteng", "atap genteng"], 1900, "truk_fuso"),
    ("atap.metal", "Atap Metal/Spandek", "m2", ["Bluescope", "Sakura Roof"], ["spandek", "atap metal", "zincalume"], 7850, "truk_fuso"),
    ("plafon.gypsum", "Gypsum Board", "lembar", ["Jayaboard", "Knauf", "Aplus"], ["gypsum", "gipsum", "plafon"], 700, "truk_fuso"),
    ("plafon.grc", "GRC Board", "lembar", ["GRC", "Kalsi", "Versaboard"], ["grc", "kalsiboard", "papan semen"], 1200, "truk_fuso"),
    ("plafon.rangka_hollow", "Besi Hollow", "batang", [], ["hollow", "besi hollow", "rangka plafon"], 7850, "truk_fuso"),
    ("cat.tembok", "Cat Tembok", "kg", ["Dulux", "Nippon", "Avian", "Mowilex"], ["cat tembok", "cat dinding"], 1300, "truk_cdd"),
    ("cat.kayu_besi", "Cat Kayu/Besi", "kg", ["Avian", "Emco", "Nippon"], ["cat kayu", "cat besi", "duco"], 1300, "truk_cdd"),
    ("cat.waterproofing", "Waterproofing", "kg", ["Aquaproof", "No Drop", "Sika"], ["waterproofing", "pelapis anti bocor"], 1300, "truk_cdd"),
    ("pipa.pvc", "Pipa PVC", "batang", ["Rucika", "Wavin", "Maspion"], ["pipa pvc", "pralon", "paralon"], 800, "truk_fuso"),
    ("pipa.ppr", "Pipa PPR", "batang", ["Rucika", "Wavin", "SD"], ["ppr", "pipa air panas"], 900, "truk_fuso"),
    ("pipa.gip", "Pipa Galvanis/GIP", "batang", ["Bakrie", "Spindo"], ["pipa gip", "pipa galvanis", "besi galvanis"], 7850, "truk_tronton"),
    ("sanitary.kloset", "Kloset", "unit", ["Toto", "American Standard", "Onda"], ["kloset", "closet", "wc"], 2000, "truk_cdd"),
    ("sanitary.wastafel", "Wastafel", "unit", ["Toto", "American Standard"], ["wastafel", "washtafel"], 2000, "truk_cdd"),
    ("sanitary.kran", "Kran/Faucet", "unit", ["Toto", "Onda", "San-Ei"], ["kran", "keran", "faucet"], 5000, "truk_cdd"),
    ("alat_listrik.kabel", "Kabel Listrik", "m", ["Supreme", "Eterna", "Kabelmetal"], ["kabel", "nyy", "nym", "nya"], 8900, "truk_fuso"),
    ("alat_listrik.saklar_stopkontak", "Saklar/Stop Kontak", "buah", ["Broco", "Schneider", "Panasonic"], ["saklar", "stop kontak", "stopkontak"], 1500, "truk_cdd"),
    ("alat_listrik.lampu", "Lampu/Armatur", "buah", ["Philips", "Panasonic", "Hannochs"], ["lampu", "led", "armatur", "downlight"], 1500, "truk_cdd"),
    ("alat_listrik.mcb_panel", "MCB/Panel", "buah", ["Schneider", "Broco"], ["mcb", "panel listrik", "box mcb"], 2000, "truk_cdd"),
    ("kusen.aluminium", "Kusen Aluminium", "m", ["YKK", "Alexindo", "Alcomexindo"], ["kusen aluminium", "alumunium"], 2700, "truk_fuso"),
    ("kusen.kaca", "Kaca", "m2", ["Asahimas", "Mulia"], ["kaca", "kaca polos", "kaca tempered"], 2500, "truk_fuso"),
    ("kusen.pintu", "Pintu", "unit", [], ["pintu", "daun pintu"], 700, "truk_fuso"),
    ("aspal.hotmix", "Aspal Hotmix", "ton", [], ["aspal", "hotmix", "ac-wc", "ac-bc"], 2300, "truk_tronton"),
    ("aspal.curah", "Aspal Curah", "kg", ["Pertamina"], ["aspal curah", "bitumen"], 1030, "truk_tronton"),
    ("tanah.urug", "Tanah Urug/Sirtu", "m3", [], ["tanah urug", "sirtu", "timbunan"], 1600, "truk_fuso"),
    ("upah.pekerja", "Upah Pekerja", "OH", [], ["pekerja", "tenaga"], None, None),
    ("upah.tukang", "Upah Tukang", "OH", [], ["tukang"], None, None),
    ("upah.kepala_tukang", "Upah Kepala Tukang", "OH", [], ["kepala tukang"], None, None),
    ("upah.mandor", "Upah Mandor", "OH", [], ["mandor"], None, None),
    ("alat.sewa", "Sewa Alat", "sewa-hari", [], ["sewa alat", "molen", "concrete mixer", "excavator"], None, None),
]


async def apply_taxonomy(db: AsyncSession) -> dict:
    cat_created = cat_updated = log_created = 0
    for code, name, unit, brands, keywords, berat, mode in TAXONOMY:
        existing = (await db.execute(select(ItemCategory).where(ItemCategory.code == code))).scalar_one_or_none()
        cat = existing or ItemCategory(code=code)
        cat.name = name
        cat.level = code.count(".")
        cat.standard_unit = unit
        cat.typical_brands = brands or None
        cat.search_keywords = keywords or None
        if existing:
            cat_updated += 1
        else:
            db.add(cat)
            cat_created += 1
        await db.flush()

        if berat is not None or mode is not None:
            log = (await db.execute(select(MaterialLogistics).where(MaterialLogistics.category_id == cat.id))).scalar_one_or_none()
            if not log:
                db.add(MaterialLogistics(
                    category_id=cat.id, berat_jenis_kg_per_m3=berat, preferred_mode=mode,
                ))
                log_created += 1

    await db.flush()
    return {"categories": {"created": cat_created, "updated": cat_updated}, "logistics_created": log_created}


async def seed() -> dict:
    async with AsyncSessionLocal() as db:
        s = await apply_taxonomy(db)
        await db.commit()
    print(f"✓ Taxonomy seeded: {s}")
    return s


def main() -> None:
    asyncio.run(seed())


if __name__ == "__main__":
    main()
