# Format Seed Data AHSP & Harga — untuk ekstraksi AI (ChatGPT) → seed DB

Dokumen ini mendefinisikan **format file JSON** yang dipakai untuk mengisi database
(`ahsp_codes` + `ahsp_components`, dan opsional `bahan_upah_items`). Output AI harus
PERSIS mengikuti skema ini supaya bisa langsung di-seed lewat:

```bash
cd backend
python -m scripts.seed_ahsp  /path/ahsp_pupr_8_2023.json
python -m scripts.seed_bahan_upah  /path/ssh_mataram_2025.json   # opsional
```

---

## 1. Skema JSON AHSP (`ahsp` file)

```jsonc
{
  "meta": {
    "source": "permen_pupr_8_2023",      // salah satu: permen_pupr_28_2016 | permen_pupr_8_2023 | se_djbk_47_2026 | custom
    "version": "Permen PUPR No. 8 Tahun 2023",
    "notes": "opsional"
  },
  "ahsp": [
    {
      "kode": "A.4.1.1.1",               // kode resmi PERSIS dari dokumen
      "uraian": "Membuat 1 m3 beton mutu f'c=7,4 MPa (K100), slump (12±2) cm",
      "satuan": "m3",                    // satuan pekerjaan (m3, m2, m', kg, bh, unit, ...)
      "work_group": "beton",             // dari daftar di bawah, atau null
      "confidence_tier": "single_source",// consistent | single_source | inconsistent | custom
      "notes": "Overhead & Profit 15% (diterapkan otomatis oleh app)",
      "components": [
        { "kategori": "bahan", "nama_material": "Semen Portland", "koefisien": 247.0,  "satuan": "kg", "formula_modifier": null, "urutan": 1 },
        { "kategori": "bahan", "nama_material": "Pasir beton",     "koefisien": 0.621, "satuan": "m3", "formula_modifier": null, "urutan": 2 },
        { "kategori": "bahan", "nama_material": "Agregat kasar",   "koefisien": 0.740, "satuan": "m3", "formula_modifier": null, "urutan": 3 },
        { "kategori": "upah",  "nama_material": "Pekerja",         "koefisien": 1.650, "satuan": "OH", "formula_modifier": null, "urutan": 10 },
        { "kategori": "upah",  "nama_material": "Tukang batu",     "koefisien": 0.275, "satuan": "OH", "formula_modifier": null, "urutan": 11 },
        { "kategori": "upah",  "nama_material": "Mandor",          "koefisien": 0.083, "satuan": "OH", "formula_modifier": null, "urutan": 13 },
        { "kategori": "alat",  "nama_material": "Concrete mixer",  "koefisien": 0.250, "satuan": "sewa-hari", "formula_modifier": null, "urutan": 20 }
      ]
    }
  ]
}
```

### Aturan field
- **kode**: salin persis (huruf/titik/angka). Jangan diformat ulang.
- **kategori**: hanya `bahan` | `upah` | `alat`.
  - "Tenaga Kerja" → `upah`; "Bahan" → `bahan`; "Peralatan/Alat" → `alat`.
- **koefisien**: angka koefisien PERSIS dari tabel AHSP. Pakai titik desimal (`0.621`),
  bukan koma. Jangan dikali harga — hanya koefisien.
- **satuan** (komponen): satuan asli (kg, m3, OH, sewa-hari, dst). `OH` = Orang-Hari.
- **formula_modifier**: hampir selalu `null`. Isi hanya bila dokumen menyatakan konversi
  satuan eksplisit pada komponen (mis. `"/1400"`). Kalau ragu → `null`.
- **work_group**: pilih satu dari daftar di §3, atau `null` jika tak yakin.
- **JANGAN** masukkan baris berikut sebagai component (dihitung otomatis oleh app):
  - "Jumlah Tenaga Kerja / Bahan / Peralatan", "Jumlah (A+B+C)", subtotal apa pun,
  - "Overhead & Profit", "Harga Satuan Pekerjaan" / HSP / total.
  - Jika ada % Overhead, catat di `notes` saja (mis. "Overhead & Profit 15%").

---

## 2. Skema JSON Bahan & Upah (opsional, `bahan_upah` file — dari SSH/distributor)

```jsonc
{
  "meta": { "provinsi": "Nusa Tenggara Barat", "kota": "Kota Mataram", "tahun": 2025,
            "source_label": "SHS Kota Mataram 2025" },
  "items": [
    { "nama": "Semen Portland", "satuan": "kg", "harga": 1450, "category": "bahan",
      "tier": "A", "tkdn_factor": 1.0, "aliases": ["Semen PC","Portland Cement"], "notes": null },
    { "nama": "Pekerja",        "satuan": "OH", "harga": 110000, "category": "upah",
      "tier": "A", "tkdn_factor": 1.0 }
  ]
}
```
- **harga**: angka rupiah per satuan (integer/desimal, tanpa "Rp"/titik ribuan).
- **category**: `bahan` | `upah` | `alat`. **tier**: `A` (SSH resmi) | `B` (distributor resmi) | `C` (marketplace) | `D` (tanpa keterangan).
- **tkdn_factor**: 0–1 (1 = 100% lokal). Upah biasanya 1.0.
- `meta.provinsi/kota/tahun/source_label` jadi default untuk semua item (boleh di-override per item).

---

## 3. Kosakata `work_group` (pakai PERSIS salah satu, atau null)

```
persiapan, bongkaran, tanah, pondasi, pembesian, bekisting, beton, dinding,
plesteran, lantai, atap, plafon, kusen, sanitasi, plumbing, listrik, drainase,
halaman, pengecatan, baja
```

---

## 4. Prompt siap-kirim ke ChatGPT

Lihat `docs/PROMPT_EKSTRAK_AHSP.md` (copy-paste utuh, lampirkan PDF/Excel AHSP-nya).
