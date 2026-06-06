# backend/app/services/risk_service.py
"""
Vendor Risk Prediction Service — wraps the trained ML model for use
inside FastAPI endpoints.

Usage::

    from backend.app.services.risk_service import RiskService

    svc = RiskService()
    result = svc.predict_vendor_risk(vendor_id=1, features={...}, db=session)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.models import RiskLabel, RiskPrediction, Vendor

logger = logging.getLogger(__name__)

# ── Label string → enum mapping ────────────────────────────────
_LABEL_MAP = {
    "low": RiskLabel.LOW,
    "medium": RiskLabel.MEDIUM,
    "high": RiskLabel.HIGH,
    "critical": RiskLabel.CRITICAL,
}


class RiskService:
    """Wraps the ML predictor and handles DB persistence.

    The service lazily loads the model on first prediction so that
    application startup is not blocked by model I/O.
    """

    def __init__(self) -> None:
        self._predictor: Optional[Any] = None

    # ─────────────────────────────────────────────────────────────
    #  Lazy model loading
    # ─────────────────────────────────────────────────────────────

    def _get_predictor(self) -> Any:
        """Return the RiskPredictor singleton, loading on first use."""
        if self._predictor is None:
            from ml.predict import RiskPredictor
            self._predictor = RiskPredictor()
            logger.info("Risk predictor initialised (version=%s).", self._predictor.model_version)
        return self._predictor

    # ─────────────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────────────

    def predict_vendor_risk(
        self,
        vendor_id: int,
        features: Dict[str, Any],
        db: Session,
    ) -> Dict[str, Any]:
        """Run risk prediction for a vendor and persist the result.

        Parameters
        ----------
        vendor_id : int
            The vendor to score.
        features : dict
            Vendor performance features.
        db : Session
            SQLAlchemy session for persistence.

        Returns
        -------
        dict
            Prediction result including risk_label, risk_score,
            probabilities, and the persisted prediction_id.
        """
        # Validate vendor exists
        vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
        if vendor is None:
            raise ValueError(f"Vendor {vendor_id} not found.")

        # Run ML prediction
        predictor = self._get_predictor()
        result = predictor.predict(features)

        # Map label string to enum
        label_str = result["risk_label"]
        risk_label = _LABEL_MAP.get(label_str, RiskLabel.MEDIUM)

        # Persist prediction
        prediction = RiskPrediction(
            vendor_id=vendor_id,
            risk_score=result["risk_score"],
            risk_label=risk_label,
            model_version=result["model_version"],
            feature_payload=result["feature_values"],
        )
        db.add(prediction)
        db.flush()

        logger.info(
            "Risk prediction: vendor=%d label=%s score=%.4f prediction_id=%d",
            vendor_id,
            label_str,
            result["risk_score"],
            prediction.id,
        )

        return {
            "prediction_id": prediction.id,
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "risk_label": label_str,
            "risk_score": result["risk_score"],
            "probabilities": result["probabilities"],
            "model_version": result["model_version"],
            "predicted_at": prediction.predicted_at.isoformat(),
            "feature_values": result["feature_values"],
        }

    def get_vendor_risk_history(
        self,
        vendor_id: int,
        db: Session,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return the prediction history for a vendor."""
        predictions = (
            db.query(RiskPrediction)
            .filter(RiskPrediction.vendor_id == vendor_id)
            .order_by(RiskPrediction.predicted_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "prediction_id": p.id,
                "risk_label": p.risk_label.value,
                "risk_score": p.risk_score,
                "model_version": p.model_version,
                "predicted_at": p.predicted_at.isoformat(),
                "feature_payload": p.feature_payload,
            }
            for p in predictions
        ]

    def get_risk_summary(self, db: Session) -> Dict[str, Any]:
        """Return an aggregate risk summary across all vendors.

        For each vendor, uses only the latest prediction.
        """
        # Get all vendors with their latest prediction
        vendors = db.query(Vendor).all()

        summary = {"low": 0, "medium": 0, "high": 0, "critical": 0, "unscored": 0}
        vendor_risks = []

        for vendor in vendors:
            if vendor.risk_predictions:
                # Latest prediction (already ordered by selectin)
                latest = max(vendor.risk_predictions, key=lambda p: p.predicted_at)
                label = latest.risk_label.value
                summary[label] += 1
                vendor_risks.append({
                    "vendor_id": vendor.id,
                    "vendor_name": vendor.name,
                    "risk_label": label,
                    "risk_score": latest.risk_score,
                    "predicted_at": latest.predicted_at.isoformat(),
                })
            else:
                summary["unscored"] += 1
                vendor_risks.append({
                    "vendor_id": vendor.id,
                    "vendor_name": vendor.name,
                    "risk_label": "unscored",
                    "risk_score": None,
                    "predicted_at": None,
                })

        return {
            "total_vendors": len(vendors),
            "distribution": summary,
            "vendors": vendor_risks,
        }

    def model_health(self) -> Dict[str, Any]:
        """Check if the ML model is available and healthy."""
        try:
            predictor = self._get_predictor()
            return predictor.health_check()
        except Exception as exc:
            return {
                "status": "error",
                "model_loaded": False,
                "error": str(exc),
            }
