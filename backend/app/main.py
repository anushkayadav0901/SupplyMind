# backend/app/main.py
"""
FastAPI application entrypoint for SupplyMind.

Run with:
    uvicorn backend.app.main:app --reload

Or from the backend/ directory:
    uvicorn app.main:app --reload
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import settings
from backend.app.database import create_all_tables
from backend.app.routers import health
from backend.app.routers import documents as documents_router
from backend.app import models as _models  # noqa: F401  — registers ORM tables on Base.metadata

logger = logging.getLogger(__name__)


# ── Lifespan (startup / shutdown) ──────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ANN001, ARG001
    """Runs once on startup and once on shutdown."""

    # ── Startup ─────────────────────────────────────────────────
    logger.info("Starting %s v%s …", settings.PROJECT_NAME, settings.VERSION)

    # 1. Ensure filesystem directories exist
    for dir_path in (settings.upload_path, settings.faiss_index_path):
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        logger.info("Directory ready: %s", dir_path)

    # 2. Create database tables (MVP — use Alembic in production)
    create_all_tables()
    logger.info("Database tables ensured.")

    yield  # ← application runs here

    # ── Shutdown ────────────────────────────────────────────────
    logger.info("Shutting down %s.", settings.PROJECT_NAME)


# ── App instance ───────────────────────────────────────────────
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)


# ── CORS ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routers ────────────────────────────────────────────────────
app.include_router(health.router, prefix=settings.API_V1_STR)
app.include_router(documents_router.router, prefix=settings.API_V1_STR)


# ── Root endpoint ──────────────────────────────────────────────
@app.get("/", tags=["root"])
def root() -> dict:
    """Welcome payload — confirms the API is reachable."""
    return {
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": f"{settings.API_V1_STR}/docs",
        "health": f"{settings.API_V1_STR}/health",
    }
