# backend/app/routers/vendors.py
"""
Vendor management and risk prediction API.

Endpoints:
    GET    /vendors                          — list all vendors
    GET    /vendors/risk-summary             — aggregate risk distribution
    GET    /vendors/{vendor_id}              — vendor details + latest risk
    POST   /vendors/{vendor_id}/predict-risk — run ML risk prediction
    GET    /vendors/{vendor_id}/risk-history — prediction history
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.dependencies import DbSession
from backend.app.models import Vendor
from backend.app.schemas import (
    RiskPredictionRead,
    RiskPredictionRequest,
    RiskPredictionResponse,
    RiskSummaryResponse,
    VendorListItem,
    VendorDetailRead,
)
from backend.app.services.risk_service import RiskService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vendors", tags=["vendors"])

# ── Service singleton ──────────────────────────────────────────
_risk_service: Optional[RiskService] = None


def _get_risk_service() -> RiskService:
    global _risk_service
    if _risk_service is None:
        _risk_service = RiskService()
    return _risk_service


# =====================================================================
#  GET /vendors
# =====================================================================

@router.get(
    "",
    response_model=List[VendorListItem],
    summary="List all vendors",
)
def list_vendors(
    db: DbSession,
    skip: int = 0,
    limit: int = 50,
) -> list:
    """Return a paginated list of vendors with their latest risk status."""
    vendors = (
        db.query(Vendor)
        .order_by(Vendor.name.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    result = []
    for v in vendors:
        latest_risk = None
        latest_score = None
        if v.risk_predictions:
            latest = max(v.risk_predictions, key=lambda p: p.predicted_at)
            latest_risk = latest.risk_label.value
            latest_score = latest.risk_score

        result.append(VendorListItem(
            id=v.id,
            name=v.name,
            gstin=v.gstin,
            contact_email=v.contact_email,
            contact_phone=v.contact_phone,
            latest_risk_label=latest_risk,
            latest_risk_score=latest_score,
            prediction_count=len(v.risk_predictions),
            document_count=len(v.extracted_entities),
            created_at=v.created_at,
        ))

    return result


# =====================================================================
#  GET /vendors/risk-summary
# =====================================================================

@router.get(
    "/risk-summary",
    response_model=RiskSummaryResponse,
    summary="Aggregate risk distribution across all vendors",
)
def get_risk_summary(db: DbSession) -> dict:
    """Return a count of vendors in each risk category."""
    svc = _get_risk_service()
    return svc.get_risk_summary(db)


# =====================================================================
#  GET /vendors/{vendor_id}
# =====================================================================

@router.get(
    "/{vendor_id}",
    response_model=VendorDetailRead,
    summary="Get vendor details with latest risk",
)
def get_vendor(vendor_id: int, db: DbSession) -> dict:
    """Return full vendor details including latest prediction."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found.",
        )

    latest_prediction = None
    if vendor.risk_predictions:
        latest = max(vendor.risk_predictions, key=lambda p: p.predicted_at)
        latest_prediction = {
            "prediction_id": latest.id,
            "risk_label": latest.risk_label.value,
            "risk_score": latest.risk_score,
            "model_version": latest.model_version,
            "predicted_at": latest.predicted_at.isoformat(),
            "feature_payload": latest.feature_payload,
        }

    return VendorDetailRead(
        id=vendor.id,
        name=vendor.name,
        gstin=vendor.gstin,
        pan=vendor.pan,
        contact_email=vendor.contact_email,
        contact_phone=vendor.contact_phone,
        address=vendor.address,
        website=vendor.website,
        document_count=len(vendor.extracted_entities),
        prediction_count=len(vendor.risk_predictions),
        latest_prediction=latest_prediction,
        created_at=vendor.created_at,
        updated_at=vendor.updated_at,
    )


# =====================================================================
#  POST /vendors/{vendor_id}/predict-risk
# =====================================================================

@router.post(
    "/{vendor_id}/predict-risk",
    response_model=RiskPredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run ML risk prediction for a vendor",
)
def predict_vendor_risk(
    vendor_id: int,
    body: RiskPredictionRequest,
    db: DbSession,
) -> dict:
    """Accept vendor performance features and return a risk prediction.

    The prediction is persisted in the database for history tracking.
    """
    svc = _get_risk_service()

    try:
        result = svc.predict_vendor_risk(
            vendor_id=vendor_id,
            features=body.features,
            db=db,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"ML model not available: {exc}",
        )
    except Exception as exc:
        logger.exception("Risk prediction failed for vendor %d", vendor_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {exc}",
        )

    db.commit()
    return result


# =====================================================================
#  GET /vendors/{vendor_id}/risk-history
# =====================================================================

@router.get(
    "/{vendor_id}/risk-history",
    summary="Get risk prediction history for a vendor",
)
def get_risk_history(
    vendor_id: int,
    db: DbSession,
    limit: int = 20,
) -> dict:
    """Return historical risk predictions for a vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vendor {vendor_id} not found.",
        )

    svc = _get_risk_service()
    history = svc.get_vendor_risk_history(vendor_id, db, limit=limit)

    return {
        "vendor_id": vendor_id,
        "vendor_name": vendor.name,
        "prediction_count": len(history),
        "predictions": history,
    }
