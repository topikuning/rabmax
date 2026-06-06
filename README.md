# BOQ Generator

Web app full-auto untuk generate BOQ (Bill of Quantities / RAB) untuk tender lelang pemerintah Indonesia. Sesuai LKPP, Permen PUPR 8/2023, dan SE DJBK 47/2026.

## Fitur

**Mode A — Generate BOQ:**
- Upload file RAB kosong (template lelang dari pemda)
- Auto-parse struktur paket sheets, items, satuan, volume
- Auto-match item → AHSP Permen PUPR (rule + LLM)
- Auto-source harga material dari DB (SSH provinsi + distributor)
- Build Bahan & Upah, ANALISA, Resume Analisa, paket sheets, RAB, REKAP, Sub Resume EE
- Auto-calibrate ke target nilai penawaran
- Output: Excel lengkap, formula chain valid, TKDN tercatat

**Mode B — Analisa Profit:**
- Upload file RAB terisi (HPS)
- Auto-lookup harga distributor real saat ini
- Hitung profit margin per item + per paket
- Output: laporan analisa profit dengan rekomendasi

**Manual override**: setiap match dan harga bisa di-edit user sebelum finalisasi.

## Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16
- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, shadcn/ui
- **AI**: Multi-provider (Anthropic Claude, Mistral, OpenAI) dengan fallback chain
- **Excel I/O**: openpyxl 3.1
- **Deploy**: Railway (Postgres managed + Docker)

## Quick Start (local dev)

### Prerequisites
- Docker + Docker Compose
- AI API key (minimum 1 dari: Anthropic / Mistral / OpenAI)

### Setup

```bash
cp .env.example .env
# Edit .env, masukkan minimal 1 AI API key
```

```bash
docker compose up --build
```

Tunggu container ready. Access:
- Backend API: http://localhost:8000
- Backend docs (OpenAPI): http://localhost:8000/docs
- Frontend: http://localhost:3000
- PostgreSQL: localhost:5432 (user: boq_user, pass: boq_pass, db: boq)

### Manual setup (non-Docker)

Backend:
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# Pastikan PostgreSQL 16 running di localhost:5432
alembic upgrade head
uvicorn app.main:app --reload
```

Frontend:
```bash
cd frontend
npm install
npm run dev
```

## Deploy ke Railway

Target deploy utama. 3 service dalam 1 project: **PostgreSQL** (managed) + **backend**
(root `backend/`, Dockerfile) + **frontend** (root `frontend/`, Dockerfile). Config
sudah disiapkan: bind `$PORT`, migrasi otomatis, `railway.json`, build arg
`NEXT_PUBLIC_API_URL`, volume `/app/storage`.

Inti variabel (reference variables Railway):
```
# backend
DATABASE_URL=${{Postgres.DATABASE_URL}}
CORS_ORIGINS=["https://${{frontend.RAILWAY_PUBLIC_DOMAIN}}"]
ANTHROPIC_API_KEY=...            # minimal 1 provider
# frontend
NEXT_PUBLIC_API_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}
```

**Langkah lengkap, detail, beserta troubleshooting → [`docs/DEPLOY.md`](docs/DEPLOY.md).**
(Volume untuk `/app/storage` wajib agar file tidak hilang saat redeploy; `NEXT_PUBLIC_API_URL`
di-bake saat build jadi redeploy frontend bila domain backend berubah.)

## Struktur Folder

```
boq-app/
├── build.md                # Roadmap & changelog per session
├── README.md
├── docker-compose.yml
├── .env.example
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/            # DB migrations
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── db/             # Models + session
│   │   ├── api/            # FastAPI routes
│   │   ├── services/
│   │   │   ├── parser/     # Stage 1: parse Excel
│   │   │   ├── matcher/    # Stage 2: item → AHSP (Session 2)
│   │   │   ├── builder/    # Stage 3-5: build sheets (Session 2)
│   │   │   ├── calibrator/ # Stage 5: target calibration (Session 2)
│   │   │   ├── validator/  # Stage 6: sanity check (Session 2)
│   │   │   └── profit_analyzer/  # Mode B (Session 2)
│   │   ├── ai/             # Multi-provider LLM client
│   │   ├── scrapers/       # Seed master data (Session 4)
│   │   ├── core/
│   │   └── utils/
│   └── tests/
│
├── frontend/
│   ├── package.json
│   ├── Dockerfile
│   ├── next.config.js
│   └── src/
│       ├── app/            # Next.js App Router
│       ├── components/
│       ├── lib/
│       └── types/
│
├── storage/                # Local file storage (gitignored)
│   ├── uploads/            # User uploaded Excel
│   ├── outputs/            # Generated BOQ Excel
│   └── master_data/        # Scraped reference data
│
└── docs/
```

## Status Pengembangan

Lihat `build.md` untuk roadmap lengkap dan progress per session.

**Saat ini (Session 2 complete — pipeline Mode A end-to-end):**
- ✅ Foundation backend (FastAPI, models, API routes) + DB schema + Alembic
- ✅ Stage 1 parser (deterministic) + Mode B capture harga/jumlah
- ✅ AI multi-provider client + prompts (matcher, sourcing, profit, validator)
- ✅ Stage 2 Matcher (rule + LLM, work-group filter, kabel remap) — `POST /api/matches/{id}/run`
- ✅ Stage 3 Source + HSP calculator (DB + LLM fallback, O&P, TKDN)
- ✅ Stage 5 Calibrator (band 80-120% HPS) — `POST /api/projects/{id}/price`
- ✅ Stage 4 Excel builder + Stage 6 validator — `POST /api/projects/{id}/generate` (unduh via `/files/...`)
- ✅ Mode B Profit Analyzer — `POST /api/profit/{id}/run`
- ✅ Unit tests (23 pass) + Frontend API client/types + Docker
- ⏳ Sheet agregat tender penuh (Sub Resume EE / REKAP / RAB konsolidasi) — butuh file contoh
- ⏳ Manual override UI lengkap — Session 3
- ⏳ Scrapers untuk seed master data — Session 4

## Lisensi

Internal use, single user (untuk saat ini). Open source stack used.
