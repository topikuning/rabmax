# BOQ Generator App — Build Roadmap & Changelog

**WAJIB BACA SETIAP MULAI SESSION BARU**

Aplikasi ini di-build incrementally lintas multi-session Claude. File ini adalah single source of truth untuk progress, keputusan arsitektur, dan next steps.

---

## Tujuan Aplikasi

Web app full-auto untuk konsultan estimasi proyek lelang pemerintah Indonesia (LKPP):
1. **Mode A — Generate**: Upload file RAB kosong → aplikasi auto-generate BOQ lengkap (Bahan & Upah, ANALISA, Resume Analisa, paket sheets, RAB, REKAP, Sub Resume EE) dengan harga real distributor + AHSP Permen PUPR + TKDN.
2. **Mode B — Analisa Profit**: Upload file RAB terisi (HPS) → aplikasi hitung estimasi cost real → output profit margin breakdown per item + per paket.
3. Manual override UI untuk setiap match/harga sebelum finalisasi.

## Konteks regulasi

- **LKPP**: penawaran lelang valid dalam band 80-120% dari HPS.
- **Permen PUPR 8/2023**: standar AHSP.
- **SE DJBK 47/2026**: pedoman penyusunan AHSP terkini.
- **TKDN minimum**: 40-70% tergantung jenis proyek.
- **Item, satuan, volume di file lelang adalah PAKEM** — non-negotiable.

---

## Stack (FINAL — Session 1)

| Layer | Tech | Version |
|---|---|---|
| Backend | Python + FastAPI | 3.12 + 0.115.x |
| ORM | SQLAlchemy 2 + Alembic | 2.0.x + 1.13.x |
| Database | PostgreSQL | 16 (LTS until Nov 2028) |
| Frontend | Next.js + React + TypeScript | 15 + 19 + 5.x |
| UI | Tailwind CSS + shadcn/ui | 3.4 + latest |
| Excel | openpyxl | 3.1.x |
| AI providers | Claude + Mistral + OpenAI multi-provider | latest SDKs |
| Deploy | Railway (Postgres managed + Docker) | n/a |

**Auth**: single-user, no JWT/RBAC.
**Open-source only**, no paid stack.

---

## Database Schema

6 tables, lihat `backend/app/db/models/`:
- `projects` — top-level (name, lokasi, target_value, mode, status, file_paths)
- `ahsp_codes` — Permen PUPR catalogue
- `ahsp_components` — bahan/upah/alat per AHSP
- `bahan_upah_items` — master harga material (tier A/B/C/D, sumber, provinsi/tahun)
- `paket_items` — per-project parsed items
- `item_matches` — item → AHSP/LUMPSUM dengan confidence
- `profit_analyses` — Mode B output

Migration di `backend/alembic/versions/001_initial.py`.

---

## Progress per Session

### Session 1 ✅ COMPLETE

**Foundation built:**
- `build.md` master roadmap
- Folder structure (backend, frontend, storage, docs, scripts)
- `pyproject.toml` dengan deps LTS
- `config.py` Pydantic settings cached singleton
- `db/session.py` async SQLAlchemy 2.0
- All 6 DB models + enums
- AI multi-provider client (Claude/Mistral/OpenAI + retry + fallback + JSON parsing)
- Stage 1 parser (deterministic, handles multi-row parent/sub, broken images patch)
- Pydantic v2 API schemas
- 6 API route files: projects, upload, ahsp, bahan_upah, matches, profit
- `main.py` FastAPI app (lifespan, CORS, static files mount, /docs)
- Alembic env.py + initial migration creating all 6 tables + indexes
- Backend Dockerfile (Python 3.12-slim + uv)
- `docker-compose.yml` (postgres 16 + backend + frontend)
- Frontend skeleton (Next.js 15, Tailwind, dashboard listing projects from API)
- Frontend Dockerfile (multi-stage Next.js standalone)
- `README.md` (setup local + Railway)
- `.env.example`, `.gitignore`

**Verified**: 16 API routes registered. Backend imports clean.

### Session 2 ⏳ NEXT — Business logic

Priority order:

1. **Stage 2 — Matcher** (`services/matcher/`):
   - `rule_matcher.py`: token + work group filter; port WEAK_OVERRIDES + KABEL_REMAP dari skrip sebelumnya
   - `llm_matcher.py`: LLM verification untuk skor rendah, constrained generation (pilih dari kandidat list)
   - `orchestrator.py`: rule pass → LLM pass → write ItemMatch
   - API: `POST /api/matches/{project_id}/run`

2. **Stage 3 — Source** (`services/builder/source.py`):
   - DB lookup AHSP + bahan_upah
   - LLM fallback untuk material missing (cari distributor 2025/2026)

3. **Stage 4 — Builder** (`services/builder/`):
   - `bahan_upah_builder.py`, `analisa_builder.py`, `resume_analisa_builder.py`, `paket_sheets_builder.py`, `rab_builder.py`, `sub_resume_builder.py`, `rekap_builder.py`
   - **KRITIS**: Resume Analisa cols = A=NO, B=URAIAN, C=SAT, D=HARGA, E=NILAI TKDN, F=TIPE, G=KODE, H=SUMBER, I=TIER
   - **KRITIS**: grand JUMLAH HALAMAN = sum subtotals only, BUKAN range items+subtotals (double-count bug)
   - REKAP cols: G=Sub Resume!G, H=Sub Resume!H, I=`=(G/G$38)*H`

4. **Stage 5 — Calibrator** (`services/calibrator/calibrate.py`):
   - Hitung gap, apply multiplier ke HSP Resume Analisa
   - Track `ItemMatch.calibration_multiplier`, audit di kolom Sumber `[×X.XXX target-calibrated]`
   - Band check 80-120% HPS

5. **Stage 6 — Validator** (`services/validator/`):
   - `formula_check.py`, `subtotal_check.py`, `tkdn_check.py`, `llm_sanity.py`

6. **Mode B — Profit Analyzer** (`services/profit_analyzer/`):
   - Extend `parse_filled_rab` untuk capture harga/jumlah dari file terisi
   - DB + LLM lookup harga real per item
   - Aggregate per paket
   - LLM narrative summary
   - Persist `ProfitAnalysis`

7. **End-to-end orchestrator** (`services/orchestrator.py`):
   - `generate_boq(project_id)` chain Stage 1-6 → write Excel
   - API: `POST /api/projects/{project_id}/generate`

8. **AI prompts** (`ai/prompts/`): matcher, sourcing, validator, profit_summary

### Session 3 ⏳ Frontend lengkap

- `/projects/new` form create
- `/projects/{id}` detail (upload, parse summary, item list, filter)
- `/projects/{id}/review` manual override UI (AHSP search dropdown + lumpsum input)
- `/projects/{id}/generate` button + progress
- `/projects/{id}/profit` analysis report dengan chart breakdown
- `/ahsp`, `/bahan-upah` browse + admin

### Session 4 ⏳ Scrapers + seed

- `scrapers/permen_pupr.py` (PDF parser → seed AHSP)
- `scrapers/se_djbk_47_2026.py`
- `scrapers/ssh_provinsi.py` (per provinsi)
- `scrapers/distributor.py` (Toto, Onda, Schneider, dll)
- `scripts/seed_*.py`
- Admin panel CRUD di frontend
- **CATATAN**: scraper code only — user execute karena sandbox saya block domain `ehsd-pupr.id`, `jdihn.go.id`, dll

### Session 5+ ⏳ Polish + deploy

- Error handling granular, retry queue
- Caching AHSP lookups, parallel LLM
- Railway deploy doc lengkap
- E2E test dengan file Mataram dari project files
- Export ZIP (Excel + audit trail PDF)

---

## Known Issues / Lessons Learned (CRITICAL untuk Session 2)

1. **Formula AMPEAN punya divisor**: `'Bahan & Upah'!D12/1400` untuk unit conversion. Saat translate row reference, **JANGAN strip divisor**. Use AST parser, bukan regex naive.

2. **Sub-total double-counting**: paket sheet sering `=SUM(H13:H81)` mencakup item DAN subtotal → 2×. **FIX**: grand = `=H41+H49+H67+H82` (sum subtotal rows saja).

3. **Multi-row parent/sub**: di 8.Parkir dst, item parent tanpa vol/sat, sub-row punya vol/sat tapi uraian = lokasi. Parser harus lookback parent. **DITERAPKAN** di `parser/excel_parser.py:find_parent_uraian`.

4. **WEAK matches salah**: "Beton mutu rendah" → "Pembesian Besi Beton" karena keyword overlap. **FIX matcher**: work group filter dulu, baru token. LLM untuk skor < 0.8.

5. **Mass-mapping Kabel NYY**: semua ukuran → 1 AHSP salah (`5.1.5.13 stop kontak`). **Encoded di rules**: per ukuran ke `5.1.1.1.18/20/34/36`.

6. **REKAP col C HARUS formula** `='Sub Resume EE'!C<row>`. Sub Resume EE col C → `='paket'!B<row>` = nama pekerjaan resmi ("PEKERJAAN PERSIAPAN" dst). Pernah saya overwrite jadi literal "1.Persiapan" — user marah.

7. **TKDN per item dari Resume Analisa col E**: paket sheet col I = `='Resume Analisa'!$E$<row>`. **Resume Analisa col E HARUS = TKDN factor** (0-1, bukan tipe).

8. **REKAP cols**: G=Sub Resume!G, H=Sub Resume!H, I=`=(G/G$38)*H` (weighted). Col M, N legacy garbage, hapus.

9. **RAB total row** (file Mataram = 1658): `=SUM(J14:J1656)`. Setiap item paket harus punya 1 row RAB (no missing).

10. **SSH database tidak ada API**: scrape per provinsi. Domain block dari sandbox, user execute.

11. **Calibration uniform multiplier** valid sebagai last resort, audit trail wajib `[×X.XXX target-calibrated]` di col Sumber.

12. **Single user, no auth**. Jangan tambah JWT/RBAC.

---

## Env Variables (`.env.example`)

```
DATABASE_URL=postgresql+psycopg://boq_user:boq_pass@localhost:5432/boq
APP_ENV=development
STORAGE_PATH=./storage
ANTHROPIC_API_KEY=
MISTRAL_API_KEY=
OPENAI_API_KEY=
DEFAULT_AI_PROVIDER=claude
CORS_ORIGINS=["http://localhost:3000"]
```

---

## Cara melanjutkan di session baru

1. Baca `build.md` ini full
2. Cek "Progress per Session" — mana ✅, mana TODO
3. Pilih next milestone dari Session N (NEXT)
4. Sebelum coding, ringkas plan ke user kalau scope besar
5. Akhir session: WAJIB update "Progress per Session" + "Known Issues" + ringkasan file changed

---

## File Inventory (Session 1 end)

```
boq-app/
├── build.md                                  ← this file
├── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
│
├── backend/
│   ├── pyproject.toml
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/001_initial.py
│   ├── app/
│   │   ├── main.py                          ← FastAPI app
│   │   ├── config.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── models/                      ← 6 models
│   │   ├── api/                             ← 6 routers
│   │   │   ├── schemas.py
│   │   │   ├── projects.py
│   │   │   ├── upload.py
│   │   │   ├── ahsp.py
│   │   │   ├── bahan_upah.py
│   │   │   ├── matches.py
│   │   │   └── profit.py
│   │   ├── services/
│   │   │   ├── parser/excel_parser.py       ← Stage 1 DONE
│   │   │   ├── matcher/                     ← Session 2
│   │   │   ├── builder/                     ← Session 2
│   │   │   ├── calibrator/                  ← Session 2
│   │   │   ├── validator/                   ← Session 2
│   │   │   └── profit_analyzer/             ← Session 2
│   │   ├── ai/client.py                     ← multi-provider DONE
│   │   ├── scrapers/                        ← Session 4
│   │   ├── core/
│   │   └── utils/
│   └── tests/
│
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── postcss.config.js
│   ├── Dockerfile
│   └── src/app/
│       ├── layout.tsx
│       ├── page.tsx                         ← dashboard
│       └── globals.css
│
├── storage/{uploads,outputs,master_data}/.gitkeep
├── docs/
└── scripts/
```

Total Session 1: ~30 source files. Backend siap `docker compose up`. Frontend skeleton render dashboard from API.

---

**End of build.md — keep this updated!**
