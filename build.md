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

**Auth**: MULTI-USER — bcrypt + JWT HS256 (stdlib), project per-owner. (Sebelumnya
single-user; diubah atas permintaan user. Detail di Known Issue #12.)
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

### Session 2 — Part 1 ✅ COMPLETE — Engine analitik (match → price → calibrate)

**Dibangun (Part 1):**
- **Stage 2 Matcher** (`services/matcher/`):
  - `rules.py`: tokenizer + stopwords ID, `classify_work_group` (20+ work group),
    `WEAK_OVERRIDES` (Known Issue #4), `KABEL_NYY_REMAP` per ukuran (Known Issue #5).
  - `rule_matcher.py`: pure-python, decoupled dari ORM (unit-testable). Work-group
    filter dulu → blend Jaccard+coverage → bonus/penalti satuan → weak override.
    Threshold SCORE_ACCEPT=0.8 (di bawah itu → LLM).
  - `llm_matcher.py`: constrained generation — LLM HANYA pilih dari kandidat top-K,
    validasi id, graceful fallback ke best rule candidate kalau LLM error.
  - `orchestrator.py`: rule→LLM pass, dedup per unique key, JANGAN timpa match yang
    sudah `reviewed_by_user`. API: `POST /api/matches/{project_id}/run`.
- **Stage 3 Source** (`services/builder/source.py`): lookup bahan_upah di DB (prefer
  tier A>B>C>D + tahun terbaru) → fallback LLM → cache hasil LLM ke DB. `price_match`
  set `final_hsp` + `tkdn_factor` per match.
- **HSP calculator** (`services/builder/hsp_calculator.py`): Σ(koef×harga×modifier)
  per kategori + O&P; `apply_modifier` hormati `/1400` (Known Issue #1); TKDN tertimbang.
- **Stage 5 Calibrator** (`services/calibrator/calibrate.py`): uniform multiplier ke
  target, guard rail 0.5–2.0, band check 80-120% HPS, audit label `[×X.XXX target-calibrated]`.
- **Pricing orchestrator** (`services/pricing.py`): source semua match → kalibrasi →
  set `final_hsp` + `calibration_multiplier`. API: `POST /api/projects/{project_id}/price`.
- **Mode B Profit Analyzer** (`services/profit_analyzer/analyzer.py`): `parse_filled_rab`
  kini capture harga(G)/jumlah(H); estimasi cost (match HSP → LLM → rasio fallback);
  per-paket breakdown; risk items; narasi AI; persist `ProfitAnalysis`.
  API: `POST /api/profit/{project_id}/run` (sebelumnya 501).
- **AI prompts** (`ai/prompts/`): `matcher.py`, `sourcing.py`, `profit_summary.py`.
- **Struktur dilengkapi**: `.gitignore`, `.env.example`, `storage/*/.gitkeep`,
  `docs/DEPLOY.md`, `scripts/README.md`, `frontend/src/lib/api.ts`, `frontend/src/types/index.ts`.
- **Tests** (15, semua hijau): `test_rule_matcher.py`, `test_hsp_calculator.py`, `test_calibrate.py`.

**Verified**: full `app.main` import clean, 24 routes. `pytest` 15 passed. ruff clean di file baru.

**Pipeline yang sudah jalan end-to-end (JSON, belum tulis Excel):**
`upload/parse` → `POST /matches/{id}/run` → `POST /projects/{id}/price` → review via `PATCH /matches/{id}`.
Mode B: `upload (mode=profit_analysis)` → `POST /profit/{id}/run`.

> **Catatan**: matcher & pricing baru berguna penuh setelah AHSP + bahan_upah di-seed
> (Session 4). Tanpa seed, kandidat kosong → item jadi LUMPSUM/UNRESOLVED, harga 0.

### Session 2 — Part 2 ✅ COMPLETE — Excel builder + validator + generate

**Dibangun (Part 2):**
- **Stage 4 Builder** (`services/builder/`):
  - `formulas.py`: helper pure (quote_sheet, cell_ref, mul, `sum_of_rows` anti
    double-count Known Issue #2, `sum_range`, `weighted_rekap` Known Issue #8, ppn). Unit-tested.
  - `excel_writer.py`: **kerja di atas SALINAN file upload** (PAKEM terjaga). Buat sheet
    `Resume Analisa` (cols A=NO B=URAIAN C=SAT D=HARGA E=NILAI TKDN F=TIPE G=KODE H=SUMBER I=TIER),
    lalu inject formula ke baris asli tiap item (`excel_row`): G=ref Resume!D, H=`=G*E` (bukan
    range → anti double-count), I=ref Resume!E (faktor TKDN 0-1, Known Issue #7).
- **Stage 6 Validator** (`services/validator/checks.py`): `check_records` (pure: unpriced,
  TKDN di luar 0-1, TKDN proyek tertimbang < min) + `check_workbook_formulas` (pastikan tiap
  item punya formula JUMLAH, Known Issue #9). Prompt `ai/prompts/validator.py` (llm_sanity).
- **End-to-end orchestrator** (`services/orchestrator.py`): `generate_boq` → build records dari
  DB (audit Sumber + `[×X.XXX target-calibrated]`) → tulis ke `storage/outputs` → set
  `output_file_path` + status FINALIZED. API: `POST /api/projects/{id}/generate`
  (return juga `download_url` `/files/...` + report validasi).
- **Tests**: +8 (formulas 6, excel_writer end-to-end 2). Total **23 pass**.

**Verified**: import clean 25 routes; pytest 23 passed; test sintetis menulis workbook nyata
(openpyxl) lalu verifikasi sheet Resume Analisa + formula G/H/I + validator.

**Pipeline penuh (Mode A) sekarang jalan:**
`upload` → `POST /matches/{id}/run` → `POST /projects/{id}/price` → `POST /projects/{id}/generate`
→ unduh di `/files/{output_file_path}`.

**Deteksi struktur DINAMIS (RAB beda-beda tiap proyek — prinsip inti):**
- `parser.analyze_sheet_layout(ws, header_row)` + `classify_row`: deteksi baris item /
  subtotal / grand-total **per-file, tanpa hardcode nomor baris**. Kelompokkan item ke seksi,
  tiap subtotal menutup seksi, grand-total terakhir = `total_row`. Teruji dengan workbook
  bergeometri acak (`tests/test_sheet_layout.py`).
- `validator.check_workbook_double_count`: scan tiap paket sheet, baca formula subtotal/total,
  flag bila range SUM ikut menelan baris subtotal lain → double-count (Known Issue #2),
  sepenuhnya dinamis. Sudah di-wire ke response `POST /generate` (validation.warnings).

**Sisa untuk iterasi lanjut (bukan blocker):**
- Sheet agregat lengkap gaya tender (Sub Resume EE, REKAP weighted, RAB konsolidasi, Bahan &
  Upah, ANALISA terurai) belum ditulis penuh. Fondasi sudah ada: `SheetLayout` (seksi+subtotal
  per file) + helper `weighted_rekap`/`sum_of_rows`. Builder agregat tinggal pakai layout
  dinamis ini — TIDAK perlu file referensi tetap.

### Session 3 ✅ Frontend inti (workspace + auth UI + katalog)

**Dibangun** (Next 15 App Router, Tailwind, lucide, design system dark-aware):
- Design system: `globals.css` (token + dark via prefers-color-scheme, aksen biru),
  `tailwind.config.ts` (card/accent/ring/success/warning/destructive/radius),
  `lib/utils.ts` (cn, formatRupiah, formatDate), `components/ui.tsx`
  (Button/Card/Badge/StatusBadge/ModeBadge/Input/Field/Spinner/EmptyState),
  `components/nav.tsx` (sticky nav, active link, auth-aware, logout).
- Halaman: `/login` (login+register), `/` dashboard (grid kartu proyek + status/mode badge),
  `/projects/new` (pilih mode + form), **`/projects/[id]` workspace** = stepper pipeline
  Upload→Match→Price→Generate(+unduh) untuk Mode A; Upload→Profit untuk Mode B, dengan
  statistik & warning per langkah. `/ahsp` + `/bahan-upah` (search + list).
- `lib/api.ts`: tambah `generate`, `fileUrl`, `listAhsp`, `listBahanUpah` + token Bearer
  otomatis + auto-redirect `/login` saat 401.
- **Verified**: `npm run build` sukses (8 route compile), `tsc --noEmit` clean.
  `package-lock.json` di-commit (Dockerfile pakai `npm ci`).

**Sisa frontend (iterasi lanjut, bukan blocker):**
- `/projects/[id]/review` UI override match per item (dropdown AHSP search + lumpsum input).
- `/projects/[id]/profit` laporan + chart breakdown (sekarang baru trigger + pesan sukses).
- Admin CRUD AHSP/bahan-upah (sekarang read-only browse).

> **Catatan keamanan**: endpoint statis `/files/*` (unduh output) saat ini TIDAK di-auth
> (StaticFiles mount). Untuk produksi multi-user, ganti dengan endpoint download
> ber-auth + cek owner. Dicatat agar tidak lupa.

### Session 4 ⏳ Scrapers + seed (sekarang prioritas — UI butuh data AHSP/harga)

**Sudah siap (jalur tanpa scraper):** ekstraksi AHSP via AI → JSON → seed.
- `docs/SEED_FORMAT.md` (skema JSON AHSP + bahan_upah, patok ke DB models).
- `docs/PROMPT_EKSTRAK_AHSP.md` (prompt siap-kirim ke ChatGPT, copy-paste).
- `backend/scripts/seed_ahsp.py` + `seed_bahan_upah.py` (idempotent upsert,
  `python -m scripts.seed_ahsp file.json`). Import-checked.

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

12. ~~Single user, no auth~~ **DIUBAH (user): MULTI-USER auth**. Sekarang ada
    tabel `users`, register/login, password di-hash **bcrypt**, sesi **JWT HS256**
    (implementasi stdlib `app/core/security.py` — TANPA PyJWT/`cryptography` agar
    bebas dependency native rapuh). Semua endpoint `/api/*` (kecuali `/api/auth/*`,
    `/health`, `/docs`) wajib `Authorization: Bearer`. Project di-scope per pemilik
    (`Project.owner_id`) — user lain dapat 404 (tidak membocorkan keberadaan).
    User pertama yang register otomatis superuser. `SECRET_KEY` WAJIB acak di prod
    (warning/error saat startup bila default). `ALLOW_OPEN_REGISTRATION=false` untuk
    matikan pendaftaran publik. Lihat `api/auth.py`, `api/deps.py`, migration `002_auth`,
    `tests/test_security.py` + `tests/test_auth_api.py` (isolasi multi-user diuji).

13. **rule_matcher decoupled dari ORM** (Part 1): input berupa dataclass `Candidate`,
    bukan objek SQLAlchemy → unit-testable tanpa DB. Orchestrator yang adapt. Pertahankan
    pola ini untuk semua logika murni (hsp_calculator, calibrate juga pure).

14. **Weak override penalty** (Part 1): penalti HARUS jalan walau kandidat mengandung
    keyword item. Kasus targetnya justru "pembesian besi beton" yang MENGANDUNG "beton".
    Jangan tambah guard `left not in cand_uraian` (itu mematikan rule). Lihat
    `rules.weak_override_penalty` + `tests/test_rule_matcher.py`.

15. **Matcher tak timpa review user** (Part 1): `orchestrator.run_matching` skip match
    dengan `reviewed_by_user=True`. Pricing & re-match aman dijalankan ulang.

16. **Stage 4 butuh file template Mataram**: geometri sel (row subtotal, range RAB,
    posisi kolom) belum bisa di-hardcode tanpa file referensi. Minta user upload file
    contoh sebelum tulis Excel builder, atau derive dari `PaketItem.excel_row` saat parse.
    **STATUS Part 2**: diselesaikan dengan pendekatan inject ke salinan template di
    `excel_row` (tak perlu file referensi). Sheet agregat penuh masih perlu file contoh.

17. **Excel writer = inject, bukan rebuild** (Part 2): `excel_writer.generate_workbook`
    load salinan file upload (formula existing dipertahankan, `data_only=False`), buat sheet
    `Resume Analisa`, lalu set G/H/I per item di `excel_row`. JUMLAH `=G*E` per baris (bukan
    SUM range) → tak ada double-count by construction. Jangan ubah jadi rebuild from scratch
    tanpa alasan — itu mengancam PAKEM & format tender.

18. **RAB SANGAT DINAMIS** (user, Part 2): tiap proyek beda jumlah paket/item/subtotal/posisi
    total. PRINSIP: JANGAN pernah hardcode nomor baris atau andalkan satu file referensi.
    Semua struktur diturunkan runtime via `parser.analyze_sheet_layout` + `classify_row`
    (deteksi item/subtotal/total dari isi). Builder agregat & validator HARUS pakai
    `SheetLayout` dinamis ini. Lihat `tests/test_sheet_layout.py` (geometri acak).

19. **DEPLOY = RAILWAY** (user, target sejak awal). Panduan lengkap+terkini di
    `docs/DEPLOY.md`. Hal kritis yang JANGAN diregres:
    - `backend/Dockerfile` CMD bind `--port ${PORT:-8000}` host `0.0.0.0` (Railway inject
      `$PORT` runtime; shell-form wajib). Jangan hardcode 8000.
    - `frontend/Dockerfile`: `ARG/ENV NEXT_PUBLIC_API_URL` SEBELUM `npm run build`
      (NEXT_PUBLIC di-bake saat build, bukan runtime). `mkdir -p public` agar COPY aman.
    - Reference variables: `DATABASE_URL=${{Postgres.DATABASE_URL}}`,
      `NEXT_PUBLIC_API_URL=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}`.
    - `CORS_ORIGINS` = daftar domain frontend dipisah koma (mis.
      `https://rabmax.cvbintang.com`) atau `*` (semua; aman karena auth Bearer-token,
      bukan cookie). Parser terima koma/JSON/`*`. JANGAN balik ke regex (user benci).
    - Volume mount `/app/storage` (storage ephemeral). Root Directory per service
      (backend/ & frontend/) diset di Dashboard (config-as-code belum dukung rootDirectory).
    - `railway.json` ada di backend/ & frontend/ (builder DOCKERFILE + healthcheck).
    - `DATABASE_URL` Railway `postgresql://` → auto-convert ke asyncpg (session.py & env.py).

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
CORS_ORIGINS=*                  # daftar domain dipisah koma, atau * untuk semua
SECRET_KEY=                     # wajib acak di production (openssl rand -hex 32)
```

---

## Cara melanjutkan di session baru

1. Baca `build.md` ini full
2. Cek "Progress per Session" — mana ✅, mana TODO
3. Pilih next milestone dari Session N (NEXT)
4. Sebelum coding, ringkas plan ke user kalau scope besar
5. Akhir session: WAJIB update "Progress per Session" + "Known Issues" + ringkasan file changed

---

## File Inventory (Session 2 Part 1 end)

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
│   │   ├── core/security.py                 ← bcrypt + JWT HS256 stdlib (tested)
│   │   ├── api/                             ← routers + auth
│   │   │   ├── deps.py                      ← get_current_user, get_owned_project
│   │   │   ├── auth.py                      ← register/login/me
│   │   │   ├── schemas.py
│   │   │   ├── projects.py
│   │   │   ├── upload.py
│   │   │   ├── ahsp.py
│   │   │   ├── bahan_upah.py
│   │   │   ├── matches.py
│   │   │   └── profit.py
│   │   ├── services/
│   │   │   ├── parser/excel_parser.py       ← Stage 1 + analyze_sheet_layout DINAMIS (subtotal/total/seksi)
│   │   │   ├── matcher/                     ← Stage 2 DONE
│   │   │   │   ├── rules.py                 (work group, weak override, kabel remap)
│   │   │   │   ├── rule_matcher.py          (deterministik, unit-tested)
│   │   │   │   ├── llm_matcher.py           (constrained generation)
│   │   │   │   └── orchestrator.py          (run_matching)
│   │   │   ├── builder/                     ← Stage 3+4 DONE
│   │   │   │   ├── hsp_calculator.py        (compute_hsp, modifier, TKDN — tested)
│   │   │   │   ├── source.py                (price_match, sourcing DB+LLM)
│   │   │   │   ├── formulas.py              (helper formula pure — tested)
│   │   │   │   └── excel_writer.py          (Resume Analisa + inject formula — tested)
│   │   │   ├── calibrator/calibrate.py      ← Stage 5 DONE (tested)
│   │   │   ├── pricing.py                   ← orchestrator source+calibrate DONE
│   │   │   ├── orchestrator.py              ← generate_boq DONE (Stage 4 chain)
│   │   │   ├── validator/checks.py          ← Stage 6 + double-count dinamis (tested)
│   │   │   └── profit_analyzer/analyzer.py  ← Mode B DONE
│   │   ├── ai/
│   │   │   ├── client.py                    ← multi-provider DONE
│   │   │   └── prompts/                     ← matcher, sourcing, profit_summary, validator DONE
│   │   ├── scrapers/                        ← Session 4
│   │   ├── core/
│   │   └── utils/
│   └── tests/                              ← rule_matcher, hsp_calculator, calibrate, formulas, excel_writer (23 pass)
│
├── frontend/
│   ├── package.json / tsconfig / next.config / tailwind / postcss / Dockerfile
│   └── src/
│       ├── app/{layout,page,globals.css}    ← dashboard
│       ├── lib/api.ts                        ← API client DONE
│       ├── types/index.ts                    ← shared types DONE
│       └── components/                        ← Session 3
│
├── storage/{uploads,outputs,master_data}/.gitkeep
├── docs/DEPLOY.md
└── scripts/README.md
```

Total Session 1: ~30 file. Session 2 Part 1: +~20 file (matcher, builder/source, calibrator,
pricing, profit_analyzer, prompts). Part 2: +~7 file (formulas, excel_writer, orchestrator,
validator, validator prompt, tests). Pipeline Mode A penuh jalan: upload→match→price→generate
→ unduh Excel. 23 unit test hijau. Next: Session 3 frontend + seeding (Session 4).

---

**End of build.md — keep this updated!**
