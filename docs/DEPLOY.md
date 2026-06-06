# Deploy ke Railway

Panduan deploy BOQ Generator (backend FastAPI + frontend Next.js + PostgreSQL 16).

## 1. Persiapan

- Repo sudah di GitHub.
- Punya akun Railway.
- Minimal 1 AI API key (Anthropic / Mistral / OpenAI).

## 2. PostgreSQL

1. Railway dashboard → **New Project** → **Provision PostgreSQL**.
2. Railway otomatis menyediakan `DATABASE_URL`. Catat — backend butuh ini.
   - Catatan: app meng-convert `postgresql://` & `postgresql+psycopg://` ke
     `postgresql+asyncpg://` di runtime (lihat `app/db/session.py`), jadi URL
     standar Railway aman dipakai.

## 3. Backend service

1. **New** → **GitHub Repo** → pilih repo, set **Root Directory** = `backend`.
2. Railway mendeteksi `Dockerfile`. Build otomatis.
3. Set environment variables:
   - `DATABASE_URL` → referensikan dari service Postgres.
   - `ANTHROPIC_API_KEY` / `MISTRAL_API_KEY` / `OPENAI_API_KEY` (minimal 1).
   - `DEFAULT_AI_PROVIDER` (default `claude`).
   - `APP_ENV=production`.
   - `STORAGE_PATH=/app/storage`.
   - `CORS_ORIGINS=["https://<frontend-domain>"]` (isi setelah frontend deploy).
4. **Jalankan migrasi** (sekali, setelah DB siap):
   `alembic upgrade head` via Railway shell / one-off command.
5. Catat public URL backend (mis. `https://boq-backend.up.railway.app`).

> Storage Railup bersifat ephemeral. Untuk file upload/output persisten,
> tambahkan **Volume** dan mount ke `STORAGE_PATH`, atau pindah ke object
> storage (S3-compatible) di iterasi berikutnya.

## 4. Frontend service

1. **New** → **GitHub Repo** → repo sama, **Root Directory** = `frontend`.
2. Railway deteksi `Dockerfile` (Next.js standalone).
3. Set env:
   - `NEXT_PUBLIC_API_URL` = URL backend dari langkah 3.
4. Deploy, catat URL frontend.

## 5. Finalisasi CORS

Update `CORS_ORIGINS` di backend agar memuat domain frontend, lalu redeploy
backend.

## 6. Smoke test

- `GET https://<backend>/health` → `{"status":"ok"}`.
- `GET https://<backend>/docs` → OpenAPI UI.
- Buka frontend → dashboard memuat daftar project dari API.

## Catatan seeding master data

AHSP & harga bahan/upah perlu di-seed sebelum matcher/pricing berguna penuh
(lihat `scripts/` dan roadmap Session 4 di `build.md`). Scraper dijalankan
manual dari mesin user karena beberapa domain sumber diblokir di sandbox.
