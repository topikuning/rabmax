# scripts/

Utility & seeding scripts (dijalankan manual, di luar request cycle FastAPI).

## Rencana (Session 4)

- `seed_ahsp.py` — load AHSP Permen PUPR 8/2023 hasil scrape ke `ahsp_codes` +
  `ahsp_components`.
- `seed_bahan_upah.py` — load SSH provinsi + harga distributor ke
  `bahan_upah_items`.
- `link_components.py` — autolink `ahsp_components.bahan_upah_id` ke master harga
  by nama (normalized match).

Scraper sumber ada di `backend/app/scrapers/` (kode only — eksekusi manual oleh
user karena domain sumber sering diblokir sandbox; lihat build.md Known Issue #10).

## Menjalankan

```bash
cd backend
python -m scripts.seed_ahsp   # contoh, setelah script tersedia
```

Pastikan `DATABASE_URL` ter-set dan `alembic upgrade head` sudah dijalankan.
