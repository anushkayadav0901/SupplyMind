# backend/app/config.py
"""
Application configuration via environment variables.

Uses pydantic-settings so every value can be overridden with an env var
or a .env file at the project root.  Defaults are tuned for local MVP
development with SQLite.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ── Resolve project root (two levels up from this file) ─────────
# d:\SupplyMind\backend\app\config.py  →  d:\SupplyMind
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Central configuration consumed by every module."""

    # ── General ─────────────────────────────────────────────────
    PROJECT_NAME: str = "SupplyMind"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # ── Database ────────────────────────────────────────────────
    # SQLite for MVP.  Switch to PostgreSQL by changing this single
    # value, e.g.  postgresql+psycopg2://user:pass@host/db
    DATABASE_URL: str = f"sqlite:///{_PROJECT_ROOT / 'data' / 'supplymind.db'}"

    # ── CORS ────────────────────────────────────────────────────
    # Accepts a JSON list *or* a comma-separated string.
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _parse_cors(cls, v: str | List[str]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    # ── AI / API Keys ──────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""

    # ── File Storage ───────────────────────────────────────────
    UPLOAD_DIR: str = str(_PROJECT_ROOT / "data" / "uploads")
    FAISS_INDEX_DIR: str = str(_PROJECT_ROOT / "data" / "faiss_index")

    # ── Pydantic-settings config ───────────────────────────────
    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── Convenience helpers ────────────────────────────────────
    @property
    def upload_path(self) -> Path:
        return Path(self.UPLOAD_DIR)

    @property
    def faiss_index_path(self) -> Path:
        return Path(self.FAISS_INDEX_DIR)

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


# Module-level singleton — import this everywhere.
settings = Settings()
