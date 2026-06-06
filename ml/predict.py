# ml/predict.py
"""
Late-delivery risk inference module.

Loads the trained XGBoost model and sklearn preprocessor, then provides
a clean prediction API used by the backend RiskService.

The model predicts late-delivery probability (0-1). The risk_label is
derived by bucketing that probability into SupplyMind risk tiers:
  0.00 - 0.30  →  low
  0.30 - 0.55  →  medium
  0.55 - 0.80  →  high
  0.80 - 1.00  →  critical

Usage::

    from ml.predict import RiskPredictor

    predictor = RiskPredictor()
    result = predictor.predict({
        "Shipping Mode": "First Class",
        "Days for shipment (scheduled)": 1,
        "Order Item Quantity": 3,
        ...
    })
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import joblib
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ── Artifact paths ──────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR = _PROJECT_ROOT / "ml" / "models"
_MODEL_PATH = _MODELS_DIR / "vendor_risk_model.joblib"
_PREPROCESSOR_PATH = _MODELS_DIR / "preprocessor.joblib"
_METADATA_PATH = _MODELS_DIR / "training_metadata.json"


class RiskPredictor:
    """Loads the trained model + preprocessor once and provides prediction.

    Thread-safe for read-only inference.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        preprocessor_path: Optional[str] = None,
        metadata_path: Optional[str] = None,
    ) -> None:
        self._model_path = Path(model_path) if model_path else _MODEL_PATH
        self._preprocessor_path = Path(preprocessor_path) if preprocessor_path else _PREPROCESSOR_PATH
        self._metadata_path = Path(metadata_path) if metadata_path else _METADATA_PATH

        self._model: Optional[Any] = None
        self._preprocessor: Optional[Any] = None
        self._metadata: Optional[dict] = None

    # ─────────────────────────────────────────────────────────────
    #  Lazy loading
    # ─────────────────────────────────────────────────────────────

    def _ensure_loaded(self) -> None:
        """Load model and preprocessor artifacts if not already in memory."""
        if self._model is not None:
            return

        if not self._model_path.exists():
            raise FileNotFoundError(
                f"Model not found: {self._model_path}. "
                "Run 'python ml/train_risk_model.py' first."
            )
        if not self._preprocessor_path.exists():
            raise FileNotFoundError(
                f"Preprocessor not found: {self._preprocessor_path}. "
                "Run 'python ml/train_risk_model.py' first."
            )

        self._model = joblib.load(self._model_path)
        logger.info("Loaded risk model from %s", self._model_path)

        self._preprocessor = joblib.load(self._preprocessor_path)
        logger.info("Loaded preprocessor from %s", self._preprocessor_path)

        if self._metadata_path.exists():
            with open(self._metadata_path) as f:
                self._metadata = json.load(f)

    # ─────────────────────────────────────────────────────────────
    #  Public API
    # ─────────────────────────────────────────────────────────────

    def predict(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """Predict late-delivery risk from a feature dictionary.

        Parameters
        ----------
        features : dict
            Keys should match the DataCo training feature names.
            Missing numeric keys default to 0, missing categorical
            keys default to the most common training value.

        Returns
        -------
        dict with keys:
            risk_label, risk_score, late_probability, on_time_probability,
            model_version, feature_values
        """
        self._ensure_loaded()

        # Import here to avoid circular imports at module level
        from ml.feature_engineering import prepare_single_input, risk_label_from_score

        # Build single-row DataFrame with correct columns
        input_df = prepare_single_input(features)

        # Transform through the fitted preprocessor
        X_transformed = self._preprocessor.transform(input_df)

        # Predict probabilities
        proba = self._model.predict_proba(X_transformed)[0]
        on_time_prob = float(proba[0])
        late_prob = float(proba[1])

        # Risk score = late delivery probability
        risk_score = late_prob
        risk_label = risk_label_from_score(risk_score)

        return {
            "risk_label": risk_label,
            "risk_score": round(risk_score, 4),
            "probabilities": {
                "on_time": round(on_time_prob, 4),
                "late": round(late_prob, 4),
            },
            "model_version": self.model_version,
            "feature_values": {
                col: val for col, val in zip(input_df.columns, input_df.iloc[0])
            },
        }

    @property
    def model_version(self) -> str:
        """Return a version string for the loaded model."""
        self._ensure_loaded()
        if self._metadata and "model_version" in self._metadata:
            return self._metadata["model_version"]
        return "xgboost-dataco-v1"

    @property
    def is_loaded(self) -> bool:
        return self._model is not None

    def health_check(self) -> Dict[str, Any]:
        """Check if the model is loadable and return metadata."""
        try:
            self._ensure_loaded()
            return {
                "status": "ok",
                "model_loaded": True,
                "model_version": self.model_version,
                "model_path": str(self._model_path),
                "preprocessor_path": str(self._preprocessor_path),
                "training_accuracy": self._metadata.get("accuracy") if self._metadata else None,
                "training_f1": self._metadata.get("f1") if self._metadata else None,
            }
        except Exception as exc:
            return {
                "status": "error",
                "model_loaded": False,
                "error": str(exc),
            }
