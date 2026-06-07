"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api import (
    admin,
    ahsp,
    auth,
    bahan_upah,
    geografi,
    matches,
    pricing,
    profit,
    projects,
    upload,
)
from app.api.deps import get_current_user
from app.config import settings


async def _auto_seed() -> None:
    """Isi DB dari seed bawaan bila tabel kosong (idempotent, no-console)."""
    import gzip

    from sqlalchemy import func, select

    from app.db.models import AHSPCode, BahanUpahItem, ItemCategory, Provinsi
    from app.db.session import AsyncSessionLocal
    from scripts.seed_ahsp import apply_ahsp, count_ahsp, parse_content
    from scripts.seed_bahan_upah import apply_bahan_upah, count_bahan_upah
    from scripts.seed_bahan_upah import parse_content as parse_bu
    from scripts.seed_bahan_upah_from_ahsp import derive_from_ahsp
    from scripts.seed_geografi import apply_geografi
    from scripts.seed_taxonomy import apply_taxonomy

    async def _load_gz_ahsp(db, fname, sentinel_kode):
        """Load AHSP .gz bila kode sentinel belum ada (idempotent)."""
        p = settings.seed_data_path / fname
        if not p.exists():
            return
        has = (await db.execute(
            select(func.count(AHSPCode.id)).where(AHSPCode.kode == sentinel_kode)
        )).scalar_one()
        if has:
            return
        meta, items = parse_content(gzip.decompress(p.read_bytes()).decode("utf-8"))
        s = await apply_ahsp(db, items, meta.get("source", "se_djbk_47_2026"), meta.get("version"))
        await db.commit()
        logger.info(f"Auto-seed AHSP {fname}: {s['created']} baru / {s['updated']} update.")

    async with AsyncSessionLocal() as db:
        # Geografi (38 provinsi + 514 kota/kab) bila kosong.
        if (await db.execute(select(func.count(Provinsi.id)))).scalar_one() == 0:
            logger.info("Auto-seed: geografi kosong → memuat 38 provinsi + 514 kota/kab…")
            g = await apply_geografi(db)
            await db.commit()
            logger.info(f"Auto-seed geografi selesai: {g}")

        # Taxonomy item_categories + material_logistics bila kosong.
        if (await db.execute(select(func.count(ItemCategory.id)))).scalar_one() == 0:
            t = await apply_taxonomy(db)
            await db.commit()
            logger.info(f"Auto-seed taxonomy selesai: {t}")

        # AHSP bawaan (AI-extracted SDA, kode huruf) bila tabel kosong.
        path = settings.seed_data_path / "ahsp_se_djbk_47_2026.jsonl.gz"
        if path.exists() and await count_ahsp(db) == 0:
            logger.info("Auto-seed: tabel AHSP kosong → memuat data bawaan…")
            meta, items = parse_content(gzip.decompress(path.read_bytes()).decode("utf-8"))
            summary = await apply_ahsp(db, items, meta.get("source", "se_djbk_47_2026"), meta.get("version"))
            await db.commit()
            logger.info(f"Auto-seed AHSP selesai: {summary['created']} item.")

        # AHSP CK 2026 RESMI (kode numerik, harga nasional terpasang) — selalu cek.
        await _load_gz_ahsp(db, "ahsp_ck_2026.jsonl.gz", "1.1.1.1")

        # Harga dasar nasional CK 2026 (tier A) → bahan_upah_items, bila belum ada.
        bu_ck = settings.seed_data_path / "bahan_upah_ck_2026_nasional.jsonl.gz"
        if bu_ck.exists():
            has_ck = (await db.execute(select(func.count(BahanUpahItem.id)).where(
                BahanUpahItem.source_label.like("AHSP CK 2026%")
            ))).scalar_one()
            if not has_ck:
                meta, items = parse_bu(gzip.decompress(bu_ck.read_bytes()).decode("utf-8"))
                d = await apply_bahan_upah(db, items, meta)
                await db.commit()
                logger.info(f"Auto-seed harga nasional CK 2026: {d}")

        # Harga SSH per-kota RESMI (tier A, FK geografi) → resolver Tier 0 lokasi.
        ssh = settings.seed_data_path / "bahan_upah_ssh_2026.jsonl.gz"
        if ssh.exists():
            has_ssh = (await db.execute(select(func.count(BahanUpahItem.id)).where(
                BahanUpahItem.source_label.like("SSH %")
            ))).scalar_one()
            if not has_ssh:
                meta, items = parse_bu(gzip.decompress(ssh.read_bytes()).decode("utf-8"))
                d = await apply_bahan_upah(db, items, meta)
                await db.commit()
                logger.info(f"Auto-seed SSH per-kota: {d}")

        # Bahan & Upah: turunkan dari komponen AHSP (harga 0) untuk sisa yang belum ada.
        if await count_bahan_upah(db) == 0 and await count_ahsp(db) > 0:
            d = await derive_from_ahsp(db)
            await db.commit()
            logger.info(f"Auto-seed Bahan & Upah dari AHSP: {d}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    logger.info(f"Starting {settings.app_name} ({settings.app_env})")
    logger.info(f"Storage path: {settings.storage_path}")
    if settings.secret_is_default:
        msg = "SECRET_KEY masih default — set SECRET_KEY acak (auth tidak aman tanpa ini)."
        if settings.app_env == "production":
            logger.error(msg)
        else:
            logger.warning(msg)
    # Ensure storage dirs exist (already handled in config but safe)
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.output_path.mkdir(parents=True, exist_ok=True)
    settings.master_data_path.mkdir(parents=True, exist_ok=True)
    if settings.auto_seed:
        try:
            await _auto_seed()
        except Exception as e:  # noqa: BLE001 — jangan gagalkan startup karena seed
            logger.warning(f"Auto-seed dilewati (error): {e}")
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    description="BOQ Generator backend for Indonesian government tender lelang (LKPP)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — daftar domain dari CORS_ORIGINS (atau "*" untuk semua).
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    # "*" tak boleh digabung allow_credentials; auth Bearer-token tak butuh cookie.
    allow_credentials=not settings.cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env, "version": "0.1.0"}


# Routes
# Auth: terbuka (register/login). Sisanya wajib bearer token.
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])

_auth = [Depends(get_current_user)]
app.include_router(projects.router, prefix="/api/projects", tags=["projects"], dependencies=_auth)
app.include_router(upload.router, prefix="/api/upload", tags=["upload"], dependencies=_auth)
app.include_router(ahsp.router, prefix="/api/ahsp", tags=["ahsp"], dependencies=_auth)
app.include_router(bahan_upah.router, prefix="/api/bahan-upah", tags=["bahan-upah"], dependencies=_auth)
app.include_router(matches.router, prefix="/api/matches", tags=["matches"], dependencies=_auth)
app.include_router(profit.router, prefix="/api/profit", tags=["profit"], dependencies=_auth)
app.include_router(geografi.router, prefix="/api/geografi", tags=["geografi"], dependencies=_auth)
app.include_router(pricing.router, prefix="/api/pricing", tags=["pricing"], dependencies=_auth)
# Admin (superuser-only — guard di router-nya sendiri).
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Serve output files (generated BOQ Excel)
app.mount(
    "/files",
    StaticFiles(directory=str(settings.storage_path)),
    name="files",
)

# Frontend (React + AG Grid, di-build Vite) di-serve same-origin.
# Aset di /assets/*, dan SEMUA rute lain → index.html (SPA client-side routing).
_webui = Path(__file__).resolve().parents[1] / "webui"
_index = _webui / "index.html"
if _index.is_file():
    if (_webui / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=str(_webui / "assets")), name="assets")

    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        # Jangan tangkap rute API/file — biar 404 JSON yang benar.
        if full_path.startswith(("api/", "files/", "assets/")):
            raise HTTPException(status_code=404, detail="Not found")
        candidate = _webui / full_path
        if full_path and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_index))
else:
    logger.warning(f"webui/index.html tidak ada di {_webui} (UI tak ter-serve; jalankan build)")
