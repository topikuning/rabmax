# scripts/

Seeder data master ada di **`backend/scripts/`** (agar bisa import `app.*`).

## Mengisi data AHSP & harga (tanpa scraper)

1. Ekstrak AHSP resmi (PDF/Excel) → JSON pakai AI: lihat
   **`docs/PROMPT_EKSTRAK_AHSP.md`** (prompt siap-kirim ke ChatGPT) dan
   **`docs/SEED_FORMAT.md`** (skema file).
2. Seed ke database:
   ```bash
   cd backend
   python -m scripts.seed_ahsp        ../ahsp_pupr_8_2023.json
   python -m scripts.seed_bahan_upah  ../ssh_mataram_2025.json
   ```
   Pastikan `DATABASE_URL` ter-set & `alembic upgrade head` sudah jalan.
   Seeder idempotent (aman dijalankan berulang).

## Scraper otomatis (Session 4, opsional)

Kode scraper akan di `backend/app/scrapers/` — dijalankan manual oleh user karena
beberapa domain sumber diblokir sandbox (lihat build.md Known Issue #10).
