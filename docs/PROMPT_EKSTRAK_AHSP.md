# Prompt siap-kirim ke ChatGPT — Ekstraksi AHSP → JSONL (versi batch + checkpoint)

Copy SEMUA isi blok bawah, tempel ke ChatGPT, lalu **lampirkan dokumen AHSP resmi**.
Format output = **JSONL** (1 baris = 1 item AHSP) supaya tahan terhadap output terpotong
dan bisa di-resume per batch. Hasilnya langsung di-seed:

```bash
cd backend
python -m scripts.seed_ahsp  ../se_djbk_47_cipta_karya.jsonl  se_djbk_47_2026
```

> Saran alur: simpan tiap batch ke satu file `.jsonl` (append), simpan `checkpoint`
> dari batch terakhir, lalu mulai batch berikutnya dengan menempelkan checkpoint itu.

---

```text
PERAN: Kamu data extractor AHSP konstruksi Indonesia. Baca dokumen resmi terlampir dan
keluarkan data terstruktur. Akurasi KODE dan KOEFISIEN adalah prioritas tertinggi.

SUMBER (khusus SE DJBK No. 47/SE/Dk/2026):
Ekstrak HANYA dari Lampiran IV, V, VI:
- Lampiran IV = AHSP Bidang Sumber Daya Air (bidang: "sumber_daya_air")
- Lampiran V  = AHSP Bidang Bina Marga       (bidang: "bina_marga")
- Lampiran VI = AHSP Bidang Cipta Karya       (bidang: "cipta_karya")
JANGAN jadikan Lampiran I/II/III/VII sebagai item AHSP (hanya acuan, bukan output).

FORMAT OUTPUT: JSONL — SATU BARIS = SATU OBJEK JSON, tanpa teks lain, tanpa markdown.
- Baris pertama batch = objek meta:
  {"meta":{"source":"se_djbk_47_2026","version":"SE DJBK No. 47/SE/Dk/2026"}}
- Lalu tiap item AHSP satu baris dengan skema PERSIS:
  {"kode":"<persis>","uraian":"<lengkap>","satuan":"<m3|m2|m'|kg|bh|titik|...>",
   "bidang":"<cipta_karya|bina_marga|sumber_daya_air>","divisi":"<nama divisi>",
   "work_group":"<satu dari WORK_GROUP, atau null>","confidence_tier":"single_source",
   "notes":<string|null>,
   "components":[
     {"kategori":"<bahan|upah|alat>","nama_material":"<nama>","koefisien":<angka titik desimal>,
      "satuan":"<kg|m3|OH|sewa-hari|...>","formula_modifier":null,"urutan":<int>}
   ]}
- Baris terakhir batch = checkpoint:
  {"checkpoint":{"source_file":"<nama file>","bidang":"<...>","divisi":"<...>",
   "halaman_terakhir":<int>,"kode_terakhir":"<...>","jumlah_item_terekstrak":<int>}}

BATAS BATCH: maksimal 50 item AHSP per batch.
MULAI DARI: Bidang Cipta Karya → DIVISI 1 (Persiapan Lapangan/Site Work) → awal divisi.
Bila aku menempelkan objek checkpoint, LANJUTKAN tepat setelah kode_terakhir.

ATURAN VALIDASI (wajib):
1. "kode": salin PERSIS (huruf, titik, angka). Jangan diformat ulang.
2. "uraian": lengkap. "satuan" pekerjaan: persis.
3. "kategori" komponen: hanya "bahan"|"upah"|"alat". "Tenaga Kerja"->"upah",
   "Peralatan"->"alat".
4. "koefisien": salin PERSIS dari kolom koefisien, pakai TITIK desimal (0.621),
   JANGAN dikali harga, JANGAN dibulatkan.
5. "satuan" komponen: pakai asli ("OH" = Orang-Hari).
6. "formula_modifier": null (isi "/<angka>" hanya bila dokumen menyatakan konversi).
7. JANGAN masukkan ke components: "Jumlah Tenaga Kerja/Bahan/Peralatan", subtotal,
   "Overhead & Profit" (catat %-nya di "notes"), "Harga Satuan Pekerjaan"/total.
8. Pertahankan SEMUA komponen riil; jangan disingkat/digabung.
9. "work_group": pilih PERSIS satu dari WORK_GROUP, atau null bila ragu.
10. Bila ada angka tidak terbaca: "koefisien": null DAN jelaskan di "notes" item tsb.
11. Output HARUS JSONL valid: setiap baris bisa di-parse json.loads sendiri.

WORK_GROUP (pilih satu / null):
persiapan, bongkaran, tanah, pondasi, pembesian, bekisting, beton, dinding, plesteran,
lantai, atap, plafon, kusen, sanitasi, plumbing, listrik, drainase, halaman, pengecatan,
baja

CONTOH (format acuan, jangan disalin):
{"meta":{"source":"se_djbk_47_2026","version":"SE DJBK No. 47/SE/Dk/2026"}}
{"kode":"A.1.1.1","uraian":"Pembersihan lapangan dan perataan","satuan":"m2","bidang":"cipta_karya","divisi":"DIVISI 1 Persiapan","work_group":"persiapan","confidence_tier":"single_source","notes":null,"components":[{"kategori":"upah","nama_material":"Pekerja","koefisien":0.05,"satuan":"OH","formula_modifier":null,"urutan":1},{"kategori":"upah","nama_material":"Mandor","koefisien":0.005,"satuan":"OH","formula_modifier":null,"urutan":2}]}
{"checkpoint":{"source_file":"SE_DJBK_47_2026.pdf","bidang":"cipta_karya","divisi":"DIVISI 1 Persiapan","halaman_terakhir":12,"kode_terakhir":"A.1.1.1","jumlah_item_terekstrak":1}}

Sekarang mulai batch pertama (maks 50 item) dari Cipta Karya / DIVISI 1.
```

---

## Daftar harga (SSH provinsi / distributor) — prompt terpisah (JSONL juga)

```text
Keluarkan JSONL. Baris pertama meta, lalu satu item per baris:
{"meta":{"provinsi":"Nusa Tenggara Barat","kota":"Kota Mataram","tahun":2025,"source_label":"SHS Kota Mataram 2025"}}
{"nama":"Semen Portland","satuan":"kg","harga":1450,"category":"bahan","tier":"A","tkdn_factor":1.0,"aliases":["Semen PC"],"notes":null}
Aturan: harga = angka rupiah/satuan tanpa "Rp"/titik ribuan. category: bahan|upah|alat.
tier: A=SSH resmi, B=distributor resmi, C=marketplace, D=tanpa keterangan. tkdn 0-1 (upah=1.0).
Hanya JSONL valid.
```

Seed: `python -m scripts.seed_bahan_upah ../ssh_mataram_2025.jsonl`

---

## Cara resume antar batch
1. Simpan tiap batch (append) ke file `.jsonl` yang sama (boleh ada beberapa baris `meta`/`checkpoint`; seeder otomatis skip yang bukan item).
2. Untuk lanjut, tempel baris `checkpoint` terakhir ke ChatGPT dan ketik:
   "lanjutkan dari checkpoint ini, batch berikutnya maks 50 item".
3. Setelah semua batch terkumpul, jalankan seeder sekali pada file gabungan.
