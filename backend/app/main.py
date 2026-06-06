"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api import admin, ahsp, auth, bahan_upah, matches, profit, projects, upload
from app.api.deps import get_current_user
from app.config import settings


async def _auto_seed() -> None:
    """Isi DB dari seed bawaan bila tabel AHSP kosong (idempotent, no-console)."""
    import gzip

    from app.db.session import AsyncSessionLocal
    from scripts.seed_ahsp import apply_ahsp, count_ahsp, parse_content

    path = settings.seed_data_path / "ahsp_se_djbk_47_2026.jsonl.gz"
    if not path.exists():
        return
    async with AsyncSessionLocal() as db:
        if await count_ahsp(db) > 0:
            return
        logger.info("Auto-seed: tabel AHSP kosong → memuat data bawaan…")
        meta, items = parse_content(gzip.decompress(path.read_bytes()).decode("utf-8"))
        summary = await apply_ahsp(db, items, meta.get("source", "se_djbk_47_2026"), meta.get("version"))
        await db.commit()
        logger.info(f"Auto-seed AHSP selesai: {summary['created']} item.")


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
# Admin (superuser-only — guard di router-nya sendiri).
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])

# Serve output files (generated BOQ Excel)
app.mount(
    "/files",
    StaticFiles(directory=str(settings.storage_path)),
    name="files",
)
