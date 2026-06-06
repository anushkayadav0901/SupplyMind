# ml/feature_engineering.py
"""
Feature engineering for the DataCo Supply Chain late-delivery risk model.

This module defines the canonical feature schema, preprocessing pipeline,
and utility functions used by both training and inference.

Dataset: DataCoSupplyChainDataset.csv (180,519 rows, 53 columns)
Target:  Late_delivery_risk (binary — 0 = on-time, 1 = late)

Safe features (13):
  Numeric (8):  Days for shipment (scheduled), Order Item Quantity,
                Order Item Discount, Order Item Discount Rate,
                Order Item Product Price, Sales, Order Profit Per Order,
                Product Price
  Categorical (5): Shipping Mode, Type, Market, Customer Segment,
                    Category Name

Leakage columns removed:
  - Delivery Status       (perfect 1:1 mapping with target)
  - Days for shipping (real)  (post-hoc — only known after delivery)
  - Order Status          (CANCELED/SUSPECTED_FRAUD encode outcome)
  - All PII / identifier columns
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logger = logging.getLogger(__name__)

# ── Artifact paths ──────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MODELS_DIR = _PROJECT_ROOT / "ml" / "models"
_PREPROCESSOR_PATH = _MODELS_DIR / "preprocessor.joblib"

# =====================================================================
#  Canonical Feature Definitions
# =====================================================================

TARGET_COLUMN = "Late_delivery_risk"

NUMERIC_FEATURES = [
    "Days for shipment (scheduled)",
    "Order Item Quantity",
    "Order Item Discount",
    "Order Item Discount Rate",
    "Order Item Product Price",
    "Sales",
    "Order Profit Per Order",
    "Product Price",
]

CATEGORICAL_FEATURES = [
    "Shipping Mode",
    "Type",
    "Market",
    "Customer Segment",
    "Category Name",
]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

# Columns explicitly excluded due to leakage, PII, or zero variance
LEAKAGE_COLUMNS = [
    "Delivery Status",
    "Days for shipping (real)",
    "Order Status",
]

PII_COLUMNS = [
    "Customer Email",
    "Customer Password",
    "Customer Fname",
    "Customer Lname",
    "Customer Street",
    "Customer Id",
    "Order Customer Id",
    "Order Item Id",
    "Order Id",
    "Customer Zipcode",
    "Order Zipcode",
]

REDUNDANT_COLUMNS = [
    "Product Description",
    "Product Image",
    "Product Status",
    "Product Category Id",
    "Product Card Id",
    "Latitude",
    "Longitude",
    "order date (DateOrders)",
    "shipping date (DateOrders)",
]

# Risk label thresholds — maps continuous risk score to SupplyMind labels
RISK_THRESHOLDS = {
    "low":      (0.0,  0.30),
    "medium":   (0.30, 0.55),
    "high":     (0.55, 0.80),
    "critical": (0.80, 1.01),
}


# =====================================================================
#  Dataset Loading
# =====================================================================

def load_dataset(path: str) -> pd.DataFrame:
    """Load the DataCo CSV and validate required columns.

    Parameters
    ----------
    path : str
        Path to DataCoSupplyChainDataset.csv.

    Returns
    -------
    pd.DataFrame
        Raw dataset with all columns.
    """
    df = pd.read_csv(path, encoding="latin-1")

    required = set(ALL_FEATURES) | {TARGET_COLUMN}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")

    logger.info("Loaded dataset: %d rows, %d columns", len(df), len(df.columns))
    return df


# =====================================================================
#  Preprocessor Construction
# =====================================================================

def build_preprocessor() -> ColumnTransformer:
    """Build a sklearn ColumnTransformer for the DataCo feature set.

    Numeric features:     StandardScaler
    Categorical features: OneHotEncoder (handle_unknown='ignore')
    """
    return ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
                drop=None,
            ), CATEGORICAL_FEATURES),
        ],
        remainder="drop",
        verbose_feature_names_out=True,
    )


def save_preprocessor(preprocessor: ColumnTransformer, path: Optional[str] = None) -> Path:
    """Persist the fitted preprocessor to disk."""
    dest = Path(path) if path else _PREPROCESSOR_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(preprocessor, dest)
    logger.info("Preprocessor saved to %s", dest)
    return dest


def load_preprocessor(path: Optional[str] = None) -> ColumnTransformer:
    """Load a previously fitted preprocessor."""
    src = Path(path) if path else _PREPROCESSOR_PATH
    if not src.exists():
        raise FileNotFoundError(
            f"Preprocessor not found: {src}. Run 'python ml/train_risk_model.py' first."
        )
    preprocessor = joblib.load(src)
    logger.info("Preprocessor loaded from %s", src)
    return preprocessor


# =====================================================================
#  Feature Preparation (Training)
# =====================================================================

def prepare_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, np.ndarray]:
    """Extract feature DataFrame and target array from the raw dataset.

    Parameters
    ----------
    df : pd.DataFrame
        Raw DataCo dataset.

    Returns
    -------
    X : pd.DataFrame
        Feature columns only (13 columns, mixed types).
    y : np.ndarray
        Binary target (0 = on-time, 1 = late).
    """
    # Select only safe features
    X = df[ALL_FEATURES].copy()

    # Fill missing values — numerics with median, categoricals with mode
    for col in NUMERIC_FEATURES:
        if X[col].isna().any():
            X[col] = X[col].fillna(X[col].median())

    for col in CATEGORICAL_FEATURES:
        if X[col].isna().any():
            X[col] = X[col].fillna(X[col].mode()[0])

    y = df[TARGET_COLUMN].to_numpy(dtype=np.int64)

    return X, y


# =====================================================================
#  Single-Input Preparation (Inference)
# =====================================================================

def prepare_single_input(features: Dict[str, Any]) -> pd.DataFrame:
    """Convert a feature dictionary into a 1-row DataFrame for prediction.

    Missing feature keys are filled with sensible defaults:
      - Numeric:     0.0
      - Categorical: most common value from training data

    Parameters
    ----------
    features : dict
        Mapping of feature name -> value.

    Returns
    -------
    pd.DataFrame
        Single-row DataFrame with columns matching ALL_FEATURES.
    """
    if not isinstance(features, dict):
        raise TypeError(f"Expected dict, got {type(features).__name__}")

    # Defaults for categorical features (most common values in DataCo)
    cat_defaults = {
        "Shipping Mode": "Standard Class",
        "Type": "DEBIT",
        "Market": "LATAM",
        "Customer Segment": "Consumer",
        "Category Name": "Cleats",
    }

    row = {}
    for col in NUMERIC_FEATURES:
        row[col] = float(features.get(col, 0.0))

    for col in CATEGORICAL_FEATURES:
        row[col] = str(features.get(col, cat_defaults.get(col, "Unknown")))

    return pd.DataFrame([row], columns=ALL_FEATURES)


# =====================================================================
#  Risk Score / Label Mapping
# =====================================================================

def risk_label_from_score(score: float) -> str:
    """Map a 0-1 risk probability to a SupplyMind risk label.

    Parameters
    ----------
    score : float
        Late delivery probability (0.0 to 1.0).

    Returns
    -------
    str
        One of: 'low', 'medium', 'high', 'critical'
    """
    for label, (lo, hi) in RISK_THRESHOLDS.items():
        if lo <= score < hi:
            return label
    return "critical"
