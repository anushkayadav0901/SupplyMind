# backend/app/database.py
"""
Database engine, session factory, and declarative base.

This is the single source of truth for all database connectivity.
SQLite is used for MVP; swap to PostgreSQL by changing DATABASE_URL
in config / .env — no code changes required.
"""

from __future__ import annotations

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.config import settings

# ── Ensure SQLite parent directory exists ──────────────────────
# The engine is created at import time.  If the directory containing
# the SQLite file does not exist, sqlite3 raises OperationalError.
if settings.is_sqlite:
    from pathlib import Path as _Path

    _db_path = settings.DATABASE_URL.replace("sqlite:///", "")
    _Path(_db_path).parent.mkdir(parents=True, exist_ok=True)

# ── Engine ──────────────────────────────────────────────────────
_connect_args: dict = {}
if settings.is_sqlite:
    # SQLite requires this for multi-threaded FastAPI usage.
    _connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=settings.DEBUG,
    pool_pre_ping=True,
)

# ── Enable WAL mode + foreign keys for SQLite ──────────────────
if settings.is_sqlite:

    @event.listens_for(Engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


# ── Session factory ─────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ── Declarative Base ───────────────────────────────────────────
class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


# ── Table creation helper (MVP convenience) ────────────────────
def create_all_tables() -> None:
    """Create every table that inherits from Base.

    Called once at application startup.  In production you would
    use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)
