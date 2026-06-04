# backend/app/dependencies.py
"""
Shared FastAPI dependencies.

Keep this module thin — it should only contain reusable Depends()
callables that routers and services need.
"""

from __future__ import annotations

from collections.abc import Generator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.app.config import Settings, settings
from backend.app.database import SessionLocal


# ── Database session ────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed after use.

    Usage in routers::

        @router.get("/items")
        def list_items(db: DbSession):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Annotated shortcut — use as a type hint in route signatures.
DbSession = Annotated[Session, Depends(get_db)]


# ── Settings dependency ────────────────────────────────────────
@lru_cache
def get_settings() -> Settings:
    """Return the cached Settings singleton.

    Useful when you need to inject settings in tests
    (override this dependency with a test-specific Settings).
    """
    return settings


AppSettings = Annotated[Settings, Depends(get_settings)]
