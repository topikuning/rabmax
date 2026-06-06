"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from app.api import ahsp, auth, bahan_upah, matches, profit, projects, upload
from app.api.deps import get_current_user
from app.config import settings


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
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.app_name,
    description="BOQ Generator backend for Indonesian government tender lelang (LKPP)",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=True,
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

# Serve output files (generated BOQ Excel)
app.mount(
    "/files",
    StaticFiles(directory=str(settings.storage_path)),
    name="files",
)
