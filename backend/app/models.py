# backend/app/models.py
"""
SQLAlchemy ORM models.

Four core tables that every future module plugs into:

  Document         – uploaded procurement files + OCR state
  Vendor           – supplier master data
  ExtractedEntity  – structured JSON extracted from a document
  RiskPrediction   – ML risk score for a vendor
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Any, List, Optional

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


# ── Helpers ─────────────────────────────────────────────────────
def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Enums ───────────────────────────────────────────────────────
class OCRStatus(str, enum.Enum):
    """Processing state of a document's text extraction."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RiskLabel(str, enum.Enum):
    """Human-readable risk bucket."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ── Document ───────────────────────────────────────────────────
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # File metadata
    filename: Mapped[str] = mapped_column(String(512), nullable=False, comment="Stored filename (UUID-based)")
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False, comment="User-uploaded name")
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Size in bytes")
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # OCR / text
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_status: Mapped[OCRStatus] = mapped_column(
        Enum(OCRStatus, native_enum=False, length=20),
        nullable=False,
        default=OCRStatus.PENDING,
        server_default=OCRStatus.PENDING.value,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    extracted_entities: Mapped[List["ExtractedEntity"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_documents_ocr_status", "ocr_status"),
        Index("ix_documents_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.original_filename!r} status={self.ocr_status.value}>"


# ── Vendor ─────────────────────────────────────────────────────
class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True, unique=True, comment="15-char Indian GST ID")
    pan: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, unique=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    extracted_entities: Mapped[List["ExtractedEntity"]] = relationship(
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    risk_predictions: Mapped[List["RiskPrediction"]] = relationship(
        back_populates="vendor",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    __table_args__ = (
        Index("ix_vendors_gstin", "gstin"),
    )

    def __repr__(self) -> str:
        return f"<Vendor id={self.id} name={self.name!r}>"


# ── ExtractedEntity ────────────────────────────────────────────
class ExtractedEntity(Base):
    __tablename__ = "extracted_entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    document_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("vendors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    entity_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="E.g. invoice, quotation, rfq, contract",
    )
    entity_data: Mapped[Any] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Structured extraction payload",
    )
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    document: Mapped["Document"] = relationship(back_populates="extracted_entities")
    vendor: Mapped[Optional["Vendor"]] = relationship(back_populates="extracted_entities")

    def __repr__(self) -> str:
        return f"<ExtractedEntity id={self.id} type={self.entity_type!r} doc={self.document_id}>"


# ── RiskPrediction ─────────────────────────────────────────────
class RiskPrediction(Base):
    __tablename__ = "risk_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    vendor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    risk_score: Mapped[float] = mapped_column(Float, nullable=False, comment="0.0 (safe) → 1.0 (critical)")
    risk_label: Mapped[RiskLabel] = mapped_column(
        Enum(RiskLabel, native_enum=False, length=10),
        nullable=False,
    )
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    feature_payload: Mapped[Any] = mapped_column(
        JSON,
        nullable=True,
        comment="Input features used for this prediction",
    )

    # Timestamps
    predicted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    vendor: Mapped["Vendor"] = relationship(back_populates="risk_predictions")

    __table_args__ = (
        Index("ix_risk_predictions_vendor_predicted", "vendor_id", "predicted_at"),
    )

    def __repr__(self) -> str:
        return f"<RiskPrediction id={self.id} vendor={self.vendor_id} label={self.risk_label.value}>"
