# Deploy ke Railway — Panduan Lengkap

Panduan deploy **BOQ Generator** ke [Railway](https://railway.com): 3 service dalam
satu project — **PostgreSQL 16** (managed), **backend** (FastAPI, Dockerfile), dan
**frontend** (Next.js 15 standalone, Dockerfile). Monorepo, jadi backend & frontend
pakai **Root Directory** berbeda di repo yang sama.

> Diverifikasi terhadap dokumentasi Railway terkini (2026). Config-as-code
> (`railway.json`) sudah disertakan di `backend/` dan `frontend/`.

---

## 0. Ringkasan arsitektur di Railway

```
Project "rabmax"
├── Postgres            (Railway managed plugin)   → expose DATABASE_URL (private)
├── backend             root: backend/   Dockerfile → uvicorn :$PORT, /health
└── frontend            root: frontend/  Dockerfile → next standalone :$PORT
```

Alur variabel:
- backend membaca `DATABASE_URL` dari Postgres (private networking).
- frontend memanggil backend lewat domain publik backend (`NEXT_PUBLIC_API_URL`).
- backend mengizinkan origin frontend lewat `CORS_ORIGINS`.

---

## 1. Hal penting yang sudah disiapkan di repo (jangan diubah tanpa alasan)

| Item | Di mana | Kenapa penting untuk Railway |
|---|---|---|
| Bind ke `$PORT` | `backend/Dockerfile` CMD `--port ${PORT:-8000}` | Railway inject `PORT` saat runtime; app **wajib** listen di situ + host `0.0.0.0`. Shell-form CMD agar `$PORT` ter-expand. |
| Migrasi otomatis | `backend/Dockerfile` `alembic upgrade head && uvicorn ...` | Skema DB ter-apply tiap deploy (single-user, aman). |
| URL → asyncpg | `app/db/session.py` & `alembic/env.py` | `DATABASE_URL` Railway berformat `postgresql://`; otomatis di-convert ke `postgresql+asyncpg://`. **Tidak perlu** ubah apa pun. |
| `NEXT_PUBLIC_API_URL` build arg | `frontend/Dockerfile` `ARG`/`ENV` sebelum `npm run build` | Variabel `NEXT_PUBLIC_*` di-**bake saat build**, bukan runtime. Railway menyuplai service variables sebagai build args. |
| `output: 'standalone'` | `frontend/next.config.js` | Wajib untuk image Next standalone (`node server.js`). |
| `railway.json` | `backend/`, `frontend/` | Builder = DOCKERFILE, healthcheck, restart policy. |

---

## 2. Prasyarat

- Akun Railway + repo sudah ada di GitHub (`topikuning/rabmax`).
- Minimal 1 API key AI: Anthropic / Mistral / OpenAI.
- (Opsional) Railway CLI: `npm i -g @railway/cli` lalu `railway login`.

---

## 3. Buat project + database

1. Railway → **New Project** → **Deploy PostgreSQL** (atau **Empty Project** lalu
   **+ New** → **Database** → **Add PostgreSQL**).
2. Service Postgres otomatis menyediakan variabel: `DATABASE_URL` (private),
   `DATABASE_PUBLIC_URL` (eksternal), `PGDATA`, dll.

---

## 4. Service backend

1. **+ New** → **GitHub Repo** → pilih `topikuning/rabmax`.
2. Buka service → **Settings**:
   - **Root Directory**: `backend`  ← wajib (monorepo).
   - **Build**: Railway mendeteksi `backend/railway.json` → builder DOCKERFILE.
     (Bila perlu, set **Config-as-code Path** = `railway.json`.)
3. **Variables** (tab Variables service backend) — set:

   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   APP_ENV=production
   STORAGE_PATH=/app/storage
   SECRET_KEY=<hasil `openssl rand -hex 32`>   # WAJIB acak — sign JWT auth
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ALLOW_OPEN_REGISTRATION=true                # set false setelah user dibuat
   ANTHROPIC_API_KEY=sk-ant-...        # isi minimal salah satu provider
   MISTRAL_API_KEY=
   OPENAI_API_KEY=
   DEFAULT_AI_PROVIDER=claude
   CORS_ORIGINS=["https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}"]
   ```

   > **Auth multi-user**: `SECRET_KEY` WAJIB di-set nilai acak; bila masih default,
   > backend log error saat startup (token JWT bisa dipalsukan). User pertama yang
   > register otomatis jadi superuser. Setelah semua user dibuat, set
   > `ALLOW_OPEN_REGISTRATION=false` agar publik tak bisa daftar sendiri.

   - `${{Postgres.DATABASE_URL}}` = **reference variable** (private network, cepat,
     tanpa biaya egress). Ganti `Postgres` bila nama service DB berbeda.
   - `CORS_ORIGINS` harus JSON array string. Referensikan domain publik frontend.
4. **Networking** → **Generate Domain** (buat domain publik backend, mis.
   `rabmax-backend-production.up.railway.app`). Healthcheck `/health` sudah diset
   via `railway.json`.
5. **Volume** (penting — storage Railway ephemeral): **+ Create Volume**, mount path
   **`/app/storage`** (sesuai `STORAGE_PATH`). Tanpa volume, file upload/output hilang
   tiap redeploy/restart.
   - Backend image jalan sebagai root, jadi tak perlu `RAILWAY_RUN_UID`.
6. Deploy. Cek logs: harus muncul `alembic upgrade head` sukses lalu uvicorn listen.

---

## 5. Service frontend

1. **+ New** → **GitHub Repo** → repo yang sama.
2. **Settings**:
   - **Root Directory**: `frontend`.
   - Builder DOCKERFILE via `frontend/railway.json`.
3. **Variables**:

   ```
   NEXT_PUBLIC_API_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}
   ```

   - Nilai ini dipakai **saat build** (di-bake ke bundle JS). Railway menyuplainya
     sebagai build arg ke Dockerfile (`ARG NEXT_PUBLIC_API_URL`).
   - Karena di-bake saat build: **kalau domain backend berubah, redeploy frontend**.
4. **Networking** → **Generate Domain** (domain publik frontend). Domain inilah yang
   harus ada di `CORS_ORIGINS` backend (langkah 4.3).
5. Deploy.

---

## 6. Finalisasi & urutan

Karena `CORS_ORIGINS` (backend) dan `NEXT_PUBLIC_API_URL` (frontend) saling
mereferensikan domain:
1. Deploy backend → Generate Domain.
2. Deploy frontend → Generate Domain.
3. Pastikan kedua reference variable terisi, lalu **redeploy** service yang perlu
   (frontend di-redeploy agar `NEXT_PUBLIC_API_URL` final ter-bake).

---

## 7. Smoke test

- `GET https://<backend-domain>/health` → `{"status":"ok"}`.
- `GET https://<backend-domain>/docs` → Swagger UI (16+ routes).
- Buka `https://<frontend-domain>` → dashboard memuat daftar project dari API
  (cek tidak ada error CORS di console browser).
- Uji pipeline: create project → upload → `/api/matches/{id}/run` →
  `/api/projects/{id}/price` → `/api/projects/{id}/generate` → unduh di `/files/...`.

---

## 8. Deploy via CLI (alternatif)

```bash
railway login
railway link                       # pilih project
# Backend
railway up --service backend       # dari folder backend/ atau set service
# Variables via CLI:
railway variables --service backend --set "APP_ENV=production"
```

> Catatan: `rootDirectory` belum bisa diset lewat `railway.json`/CLI (harus via
> Dashboard). Jadi untuk monorepo, set Root Directory tiap service di UI.

---

## 9. Troubleshooting

| Gejala | Penyebab & solusi |
|---|---|
| Deploy "active" tapi domain 502 / "Application failed to respond" | App tidak listen di `$PORT` atau bukan `0.0.0.0`. Sudah ditangani di Dockerfile; pastikan tidak meng-override CMD/`PORT`. |
| `alembic` gagal: connection refused | `DATABASE_URL` belum direferensikan dari Postgres, atau pakai public URL. Pakai `${{Postgres.DATABASE_URL}}`. |
| Frontend memanggil `localhost:8000` | `NEXT_PUBLIC_API_URL` tidak ter-set **saat build**. Set variable lalu redeploy frontend (bukan sekadar restart). |
| CORS error di browser | `CORS_ORIGINS` backend tidak memuat domain frontend (harus `https://`, JSON array). Update lalu redeploy backend. |
| File upload hilang setelah redeploy | Volume belum di-mount ke `/app/storage`. |
| Build frontend gagal di COPY public | Sudah difix (`mkdir -p public` sebelum build). |
| Healthcheck timeout | Pastikan path `/health` (backend) / `/` (frontend) reachable; naikkan `healthcheckTimeout` di `railway.json` bila cold start lama. |

---

## 10. Catatan biaya & data master

- Railway berbasis usage (Postgres + 2 service + 1 volume). Untuk single-user proyek
  estimasi, footprint kecil.
- Matcher & pricing baru berguna penuh setelah **AHSP + bahan_upah di-seed**
  (roadmap Session 4, `scripts/`). Scraper dijalankan manual dari mesin user karena
  beberapa domain sumber diblokir sandbox (lihat `build.md` Known Issue #10).

---

## Sumber (dokumentasi Railway, diakses 2026)

- [Railway — Dockerfiles](https://docs.railway.com/builds/dockerfiles)
- [Railway — Variables Reference](https://docs.railway.com/variables/reference)
- [Railway — Database Reference Variables](https://blog.railway.com/p/database-reference-variables)
- [Railway — Using Volumes](https://docs.railway.com/volumes)
- [Railway — Deploying a Monorepo](https://docs.railway.com/deployments/monorepo)
- [Railway — Config as Code](https://docs.railway.com/config-as-code)
- [Railway — Deploy a Next.js App](https://docs.railway.com/guides/nextjs)
- [Railway — PostgreSQL](https://docs.railway.com/databases/postgresql)
