# backend/app/routers/health.py
"""
Health-check endpoint.

Returns service status, version, and a lightweight database
connectivity probe.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, status
from sqlalchemy import text

from backend.app.dependencies import AppSettings, DbSession
from backend.app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Service health check",
)
def health_check(db: DbSession, settings: AppSettings) -> HealthResponse:
    """Return service status and a quick DB connectivity probe."""

    # Lightweight DB probe — a single SELECT 1.
    db_status = "connected"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "unavailable"

    return HealthResponse(
        status="ok",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        database=db_status,
        timestamp=datetime.now(timezone.utc),
    )
