# Prompt siap-kirim ke ChatGPT — Ekstraksi AHSP → JSON

Copy SEMUA teks di blok bawah ini, tempel ke ChatGPT, lalu **lampirkan file PDF/Excel
AHSP resmi** (Permen PUPR 8/2023, Permen PUPR 28/2016, atau SE DJBK). Kalau dokumennya
besar, kirim per bab/kelompok pekerjaan (mis. khusus "Pekerjaan Beton") agar akurat.

> Tips: pakai model dengan kemampuan baca file (GPT-4o/o-series). Minta dia proses
> 20–40 AHSP per batch, lalu lanjut "lanjutkan" untuk batch berikutnya.

---

```text
PERAN: Kamu data extractor untuk database AHSP konstruksi Indonesia. Tugasmu membaca
dokumen AHSP resmi pemerintah (terlampir) dan mengeluarkan data terstruktur JSON
PERSIS sesuai skema di bawah. Akurasi koefisien & kode adalah prioritas tertinggi.

OUTPUT: HANYA satu blok JSON valid (tanpa teks lain, tanpa komentar, tanpa markdown
fence). Gunakan struktur ini:

{
  "meta": {
    "source": "permen_pupr_8_2023",
    "version": "<judul dokumen, mis. Permen PUPR No. 8 Tahun 2023>",
    "notes": null
  },
  "ahsp": [
    {
      "kode": "<kode AHSP persis dari dokumen>",
      "uraian": "<uraian lengkap pekerjaan>",
      "satuan": "<satuan pekerjaan: m3, m2, m', kg, bh, unit, titik, ...>",
      "work_group": "<satu dari daftar WORK_GROUP, atau null>",
      "confidence_tier": "single_source",
      "notes": "<catatan singkat, mis. 'Overhead & Profit 15%'. Boleh null>",
      "components": [
        {
          "kategori": "<bahan|upah|alat>",
          "nama_material": "<nama material/tenaga/alat>",
          "koefisien": <angka desimal, titik sebagai pemisah>,
          "satuan": "<kg, m3, m2, OH, sewa-hari, ...>",
          "formula_modifier": null,
          "urutan": <integer urut tampil>
        }
      ]
    }
  ]
}

ATURAN WAJIB:
1. "kode": salin PERSIS (huruf, titik, angka). Jangan diformat ulang.
2. "kategori": hanya "bahan", "upah", atau "alat".
   - Kelompok "Tenaga Kerja" -> "upah". "Bahan" -> "bahan". "Peralatan"/"Alat" -> "alat".
3. "koefisien": salin angka koefisien PERSIS dari kolom koefisien tabel AHSP.
   - Gunakan TITIK desimal (contoh 0.621), bukan koma. JANGAN dikali harga.
   - Jangan membulatkan; pertahankan semua angka di belakang koma.
4. "satuan" komponen: pakai satuan asli. "OH" = Orang-Hari. Pertahankan apa adanya.
5. "formula_modifier": isi null. Hanya isi string (mis. "/1400") bila dokumen secara
   eksplisit menyatakan faktor konversi pada komponen. Kalau ragu -> null.
6. JANGAN memasukkan baris berikut sebagai komponen (ini dihitung otomatis sistem):
   - "Jumlah Tenaga Kerja", "Jumlah Harga Bahan", "Jumlah Peralatan",
   - "Jumlah (A+B+C)", subtotal apa pun,
   - "Overhead & Profit" (catat persen-nya di "notes" saja),
   - "Harga Satuan Pekerjaan" / HSP / total.
7. Pertahankan SEMUA komponen riil tiap AHSP. Jangan menyingkat/menggabung.
8. "work_group": pilih PERSIS satu dari daftar WORK_GROUP. Bila tak yakin -> null.
9. Jika satu angka tidak terbaca jelas di dokumen, isi koefisien-nya null dan tambahkan
   keterangan singkat di "notes" AHSP tsb (mis. "koef pasir tidak terbaca").
10. Output harus JSON valid yang bisa di-parse json.loads tanpa perbaikan.

WORK_GROUP (pilih salah satu, atau null):
persiapan, bongkaran, tanah, pondasi, pembesian, bekisting, beton, dinding,
plesteran, lantai, atap, plafon, kusen, sanitasi, plumbing, listrik, drainase,
halaman, pengecatan, baja

CONTOH SATU ENTRI (sebagai acuan format, bukan untuk disalin):
{
  "kode": "A.4.1.1.1",
  "uraian": "Membuat 1 m3 beton mutu f'c=7,4 MPa (K100), slump (12±2) cm",
  "satuan": "m3",
  "work_group": "beton",
  "confidence_tier": "single_source",
  "notes": "Overhead & Profit 15%",
  "components": [
    { "kategori": "bahan", "nama_material": "Semen Portland", "koefisien": 247.0, "satuan": "kg", "formula_modifier": null, "urutan": 1 },
    { "kategori": "bahan", "nama_material": "Pasir beton", "koefisien": 0.621, "satuan": "m3", "formula_modifier": null, "urutan": 2 },
    { "kategori": "upah", "nama_material": "Pekerja", "koefisien": 1.65, "satuan": "OH", "formula_modifier": null, "urutan": 10 },
    { "kategori": "upah", "nama_material": "Mandor", "koefisien": 0.083, "satuan": "OH", "formula_modifier": null, "urutan": 12 }
  ]
}

Sekarang baca dokumen AHSP yang kulampirkan dan keluarkan JSON sesuai skema di atas.
Mulai dari kelompok pekerjaan pertama. Bila terpotong, aku akan menulis "lanjutkan".
```

---

## Untuk daftar harga (SSH provinsi / distributor) — prompt terpisah

Sama seperti di atas, tapi minta skema berikut (file `bahan_upah`):

```text
Keluarkan JSON: { "meta": {"provinsi":"...","kota":"...","tahun":2025,"source_label":"..."},
"items": [ {"nama":"...","satuan":"...","harga":<angka rupiah>,"category":"bahan|upah|alat",
"tier":"A","tkdn_factor":1.0,"aliases":[],"notes":null} ] }
Aturan: harga = angka rupiah per satuan tanpa "Rp"/titik ribuan. tier: A=SSH resmi,
B=distributor resmi, C=marketplace, D=tanpa keterangan. tkdn_factor 0-1 (upah=1.0).
HANYA JSON valid.
```

---

## Setelah dapat JSON dari ChatGPT

1. Simpan ke file, mis. `ahsp_pupr_8_2023.json`.
2. Seed ke database:
   ```bash
   cd backend
   python -m scripts.seed_ahsp  ../ahsp_pupr_8_2023.json
   python -m scripts.seed_bahan_upah  ../ssh_mataram_2025.json   # bila ada
   ```
3. Cek di UI: halaman **AHSP** dan **Bahan & Upah** akan terisi; lalu Matcher & Harga
   di workspace proyek baru menghasilkan angka nyata.
