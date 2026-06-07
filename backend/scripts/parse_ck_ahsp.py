"""Parser AHSP CK 2026 — ekstrak dari AHSP_CK_2026.xlsx (resmi SE 47/SE/Dk/2026).

Sumber: file Excel resmi "DAFTAR HARGA SATUAN PEKERJAAN BIDANG CIPTA KARYA".
Struktur:
  - Sheet "Daftar Harga Satuan Pekerjaan": master kode → uraian, satuan, harga final.
  - Sheet "Upah Bahan": daftar harga satuan UPAH/BAHAN/ALAT nasional (baseline).
  - 40 sheet kategori: blok AHSP (kode + rincian komponen TENAGA KERJA/BAHAN/PERALATAN
    dengan koefisien & harga satuan nasional), O&P, Harga Satuan Pekerjaan final.

Output (offline, dijalankan sekali → artefak masuk seed_data/):
  - ahsp_ck_2026.jsonl.gz             : AHSP code + components (format seed_ahsp).
  - bahan_upah_ck_2026_nasional.jsonl.gz : harga dasar nasional (format seed_bahan_upah).

Jalankan:
    cd backend
    python -m scripts.parse_ck_ahsp /path/AHSP_CK_2026.xlsx
"""

from __future__ import annotations

import gzip
import json
import re
import statistics
import sys
from pathlib import Path

import openpyxl

KODE_RE = re.compile(r"^\d+(\.\d+){1,}\s*[a-zA-Z]?\.?$")
SOURCE = "se_djbk_47_2026"
VERSION = "AHSP CK SE DJBK No. 47/SE/Dk/2026"
TAHUN = 2026

# Section marker (kolom A/B/C) → kategori komponen.
SECTION = {"TENAGA KERJA": "upah", "BAHAN": "bahan", "PERALATAN": "alat", "ALAT": "alat"}


def _num(v: object) -> float | None:
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        s = v.strip().replace("Rp", "").replace(" ", "")
        # "1.234.567,89" (ID) → 1234567.89
        if "," in s and s.count(".") >= 1:
            s = s.replace(".", "").replace(",", ".")
        else:
            s = s.replace(",", "")
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _clean(s: object) -> str:
    return re.sub(r"\s+", " ", str(s or "").replace("\n", " ")).strip()


def _find_header(row: list) -> dict | None:
    """Deteksi baris header tabel komponen → peta nama kolom ke index."""
    idx: dict[str, int] = {}
    for i, c in enumerate(row):
        if not c:
            continue
        s = str(c).strip().lower()
        if s == "no":
            idx["no"] = i
        elif s.startswith("uraian"):
            idx["uraian"] = i
        elif s.startswith("sat"):
            idx["sat"] = i
        elif "koefisien" in s:
            idx["koef"] = i
        elif "harga" in s and "satuan" in s:
            idx["harga"] = i
        elif "jumlah" in s:
            idx["jumlah"] = i
    if "koef" in idx and "uraian" in idx and "harga" in idx:
        return idx
    return None


def load_master(wb) -> dict[str, dict]:
    """Sheet master → {kode: {uraian, satuan, harga}}."""
    ws = wb["Daftar Harga Satuan Pekerjaan"]
    master: dict[str, dict] = {}
    for row in ws.iter_rows(values_only=True):
        kode = _clean(row[1]) if len(row) > 1 else ""
        if not KODE_RE.match(kode):
            continue
        uraian = _clean(row[2]) if len(row) > 2 else ""
        satuan = _clean(row[3]) if len(row) > 3 else ""
        harga = _num(row[4]) if len(row) > 4 else None
        master[kode] = {"uraian": uraian, "satuan": satuan, "harga": harga}
    return master


def load_upah_bahan_nasional(wb) -> list[dict]:
    """Sheet 'Upah Bahan' → daftar harga dasar nasional (upah/bahan/alat).

    Kolom tetap: NO | Kode | UPAH-MATERIAL-ALAT | SATUAN | HARGA. Section (UPAH/
    BAHAN/ALAT) ditandai baris tanpa harga yang nama-kolomnya = kata kunci section.
    """
    ws = wb["Upah Bahan"]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    # Cari header → index kolom.
    nama_i = sat_i = harga_i = None
    for row in rows:
        for i, c in enumerate(row):
            s = _clean(c).upper()
            if "MATERIAL" in s and "ALAT" in s:
                nama_i = i
            elif s == "SATUAN":
                sat_i = i
            elif s.startswith("HARGA"):
                harga_i = i
        if nama_i is not None and harga_i is not None:
            break
    if nama_i is None:
        return []
    out: list[dict] = []
    kat = "bahan"
    for row in rows:
        nama = _clean(row[nama_i]) if nama_i < len(row) else ""
        harga = _num(row[harga_i]) if harga_i < len(row) else None
        up = nama.upper().rstrip(".")
        sect = next((v for key, v in SECTION.items() if up == key or up == key.split()[0]), None)
        if sect and harga is None:
            kat = sect
            continue
        if not nama or harga is None or harga < 100:
            continue
        if KODE_RE.match(nama) or nama.upper() in ("NO", "KODE"):
            continue
        satuan = _clean(row[sat_i]) if sat_i is not None and sat_i < len(row) else ""
        out.append({"nama": nama, "satuan": satuan, "harga": harga, "category": kat})
    return out


def parse_category_sheet(ws, sheet_name: str) -> list[dict]:
    """Sheet kategori → list blok AHSP {kode, components:[{kategori,nama,satuan,koef,harga}]}."""
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    blocks: list[dict] = []
    i, n = 0, len(rows)
    while i < n:
        hdr = _find_header(rows[i])
        if not hdr:
            i += 1
            continue
        # kode row: scan ≤4 baris di atas header.
        kode = ""
        for j in range(i - 1, max(-1, i - 5), -1):
            for c in rows[j]:
                if isinstance(c, str) and KODE_RE.match(c.strip()):
                    kode = c.strip()
                    break
            if kode:
                break
        # komponen sampai header berikutnya.
        comps: list[dict] = []
        kat = None
        k = i + 1
        while k < n:
            if _find_header(rows[k]):
                break
            row = rows[k]
            joined = _clean(" ".join(str(x) for x in row if x))
            up = joined.upper()
            sec = next((v for key, v in SECTION.items()
                        if (up == key or up.endswith(" " + key)) and len(joined) < 30), None)
            if sec and "JUMLAH" not in up:
                kat = sec
                k += 1
                continue
            if up.startswith("HARGA SATUAN PEKERJAAN") or re.match(r"^F\b", joined):
                k += 1
                break
            if up.startswith("JUMLAH") or "BIAYA UMUM" in up or re.match(r"^[DE]\b", joined):
                k += 1
                continue
            nama = row[hdr["uraian"]] if hdr["uraian"] < len(row) else None
            koef = _num(row[hdr["koef"]]) if hdr["koef"] < len(row) else None
            if nama and isinstance(nama, str) and _clean(nama) and koef is not None and kat:
                sat = row[hdr["sat"]] if "sat" in hdr and hdr["sat"] < len(row) else ""
                harga = _num(row[hdr["harga"]]) if hdr["harga"] < len(row) else None
                comps.append({"kategori": kat, "nama": _clean(nama), "satuan": _clean(sat),
                              "koef": koef, "harga": harga})
            k += 1
        if kode and comps:
            blocks.append({"kode": kode, "sheet": sheet_name, "components": comps})
        i = k
    return blocks


def build(xlsx_path: str) -> tuple[list[dict], list[dict]]:
    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    master = load_master(wb)
    nasional_seed = load_upah_bahan_nasional(wb)

    ahsp_items: list[dict] = []
    # (nama, satuan, kategori) → list harga (untuk dedup harga dasar nasional).
    price_pool: dict[tuple, list[float]] = {}

    for sn in wb.sheetnames:
        if sn in ("Daftar Harga Satuan Pekerjaan", "Upah Bahan"):
            continue
        for blk in parse_category_sheet(wb[sn], sn):
            m = master.get(blk["kode"], {})
            comps_out = []
            for idx, c in enumerate(blk["components"]):
                comps_out.append({
                    "kategori": c["kategori"], "nama_material": c["nama"],
                    "satuan": c["satuan"], "koefisien": c["koef"], "urutan": idx,
                    "harga_satuan": c["harga"],  # harga nasional resmi (baseline)
                })
                # Upah: hanya tarif harian (OH) kanonik; lewati subdivisi OJ (per-jam)
                # agar tak mencemari katalog (mis. 'Tukang batu' OJ 18.750).
                if c["kategori"] == "upah" and c["satuan"].strip().upper() != "OH":
                    continue
                if c["harga"] and c["harga"] >= 1:
                    price_pool.setdefault((c["nama"], c["satuan"], c["kategori"]), []).append(c["harga"])
            ahsp_items.append({
                "kode": blk["kode"],
                "uraian": m.get("uraian") or "",
                "satuan": m.get("satuan") or "",
                "bidang": "cipta_karya",
                "work_group": _clean(blk["sheet"]).lower()[:50],
                "confidence_tier": "consistent",
                "version": VERSION,
                "components": comps_out,
            })
    wb.close()

    # Harga dasar nasional: sheet 'Upah Bahan' (kanonik, menang) + median harga komponen.
    def _k(nama: str, satuan: str) -> tuple[str, str]:
        return (nama.strip().lower(), satuan.strip().lower())

    seen = {_k(b["nama"], b["satuan"]) for b in nasional_seed}
    bahan_upah = list(nasional_seed)
    for (nama, satuan, kat), prices in price_pool.items():
        if _k(nama, satuan) in seen:
            continue
        seen.add(_k(nama, satuan))
        bahan_upah.append({"nama": nama, "satuan": satuan,
                           "harga": round(statistics.median(prices), 2), "category": kat})
    return ahsp_items, bahan_upah


def _write_gz(path: Path, meta: dict, key: str, items: list[dict]) -> None:
    lines = [json.dumps({"meta": meta}, ensure_ascii=False)]
    lines += [json.dumps(it, ensure_ascii=False) for it in items]
    path.write_bytes(gzip.compress(("\n".join(lines) + "\n").encode("utf-8")))
    print(f"  ✓ {path.name}: {len(items)} {key} ({path.stat().st_size // 1024} KB)")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.parse_ck_ahsp <AHSP_CK_2026.xlsx> [out_dir]")
        raise SystemExit(2)
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parent.parent / "seed_data"
    out_dir.mkdir(parents=True, exist_ok=True)
    ahsp, bahan = build(sys.argv[1])
    ncomp = sum(len(a["components"]) for a in ahsp)
    print(f"Parsed: {len(ahsp)} AHSP / {ncomp} komponen / {len(bahan)} harga dasar nasional")
    _write_gz(out_dir / "ahsp_ck_2026.jsonl.gz",
              {"source": SOURCE, "version": VERSION, "bidang": "cipta_karya"}, "AHSP", ahsp)
    _write_gz(out_dir / "bahan_upah_ck_2026_nasional.jsonl.gz",
              {"source_label": "AHSP CK 2026 (nasional)", "tahun": TAHUN, "tier": "A"},
              "harga", bahan)


if __name__ == "__main__":
    main()
