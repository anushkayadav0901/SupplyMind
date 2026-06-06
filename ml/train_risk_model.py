# ml/train_risk_model.py
"""
Train an XGBoost binary classifier for late-delivery risk prediction
on the DataCo Supply Chain dataset.

Loads the real dataset, applies the feature engineering pipeline,
trains an XGBClassifier, evaluates on a held-out test set, and
persists model + preprocessor artifacts.

Usage:
    python ml/train_risk_model.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

# Ensure project root is on sys.path for ml.* imports
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from ml.feature_engineering import (
    ALL_FEATURES,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
    TARGET_COLUMN,
    build_preprocessor,
    load_dataset,
    prepare_features,
    save_preprocessor,
)


# ── Paths ───────────────────────────────────────────────────────
DATASET_PATH = os.path.join(_PROJECT_ROOT, "data", "datasets",
                            "DataCoSupplyChainDataset.csv")
MODEL_DIR = os.path.join(_PROJECT_ROOT, "ml", "models")
MODEL_PATH = os.path.join(MODEL_DIR, "vendor_risk_model.joblib")
FEATURE_NAMES_PATH = os.path.join(MODEL_DIR, "feature_names.json")
METADATA_PATH = os.path.join(MODEL_DIR, "training_metadata.json")


# ── Formatting helpers ──────────────────────────────────────────
def _sep(char: str = "-", width: int = 72) -> str:
    return char * width


def _header(title: str) -> None:
    print(f"\n{_sep('=')}")
    print(f"  {title}")
    print(_sep("="))


def _section(title: str) -> None:
    print(f"\n{_sep('-')}")
    print(f"  {title}")
    print(_sep("-"))


# ── Main training pipeline ──────────────────────────────────────
def main() -> None:
    _header("SupplyMind -- Late Delivery Risk Model Training (DataCo)")

    # ── 1. Load dataset ─────────────────────────────────────────
    _section("1. Loading DataCo Supply Chain dataset")
    print(f"   Path: {DATASET_PATH}")
    df = load_dataset(DATASET_PATH)
    print(f"   Rows: {len(df):,}  |  Columns: {len(df.columns)}")

    # ── 2. Prepare features ─────────────────────────────────────
    _section("2. Preparing features")
    X, y = prepare_features(df)
    print(f"   Feature DataFrame shape : {X.shape}")
    print(f"   Target distribution     : 0 (on-time)={int(np.sum(y == 0)):,}  "
          f"1 (late)={int(np.sum(y == 1)):,}")
    print(f"   Late delivery rate      : {np.mean(y):.1%}")
    print(f"   Numeric features  ({len(NUMERIC_FEATURES)})  : {NUMERIC_FEATURES}")
    print(f"   Categorical features ({len(CATEGORICAL_FEATURES)}): {CATEGORICAL_FEATURES}")

    # ── 3. Train/test split ─────────────────────────────────────
    _section("3. Train / test split (80/20, stratified)")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.20,
        stratify=y,
        random_state=42,
    )
    print(f"   Training samples : {len(X_train):,}")
    print(f"   Test samples     : {len(X_test):,}")

    # ── 4. Fit preprocessor ─────────────────────────────────────
    _section("4. Fitting preprocessor (StandardScaler + OneHotEncoder)")
    preprocessor = build_preprocessor()
    X_train_processed = preprocessor.fit_transform(X_train)
    X_test_processed = preprocessor.transform(X_test)
    print(f"   Transformed feature count: {X_train_processed.shape[1]}")

    # Save preprocessor
    os.makedirs(MODEL_DIR, exist_ok=True)
    save_preprocessor(preprocessor)

    # ── 5. Train XGBClassifier ──────────────────────────────────
    _section("5. Training XGBClassifier")

    # Compute scale_pos_weight for slight imbalance handling
    n_neg = int(np.sum(y_train == 0))
    n_pos = int(np.sum(y_train == 1))
    scale_pos_weight = n_neg / n_pos if n_pos > 0 else 1.0

    model_params = {
        "n_estimators": 200,
        "max_depth": 6,
        "learning_rate": 0.1,
        "objective": "binary:logistic",
        "eval_metric": "logloss",
        "scale_pos_weight": round(scale_pos_weight, 4),
        "random_state": 42,
        "n_jobs": -1,
    }
    print("   Parameters:")
    for k, v in model_params.items():
        print(f"     {k:25s} = {v}")

    model = XGBClassifier(**model_params)
    model.fit(X_train_processed, y_train)
    print("   Training complete.")

    # ── 6. Evaluate ─────────────────────────────────────────────
    _section("6. Evaluation on test set")

    y_pred = model.predict(X_test_processed)
    y_proba = model.predict_proba(X_test_processed)[:, 1]

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred)
    rec = recall_score(y_test, y_pred)
    auc = roc_auc_score(y_test, y_proba)

    print(f"\n   Accuracy  : {acc:.4f}")
    print(f"   Precision : {prec:.4f}")
    print(f"   Recall    : {rec:.4f}")
    print(f"   F1 Score  : {f1:.4f}")
    print(f"   ROC AUC   : {auc:.4f}")

    # Classification report
    print(f"\n{_sep('-')}")
    print("  Classification Report")
    print(_sep("-"))
    print(classification_report(
        y_test, y_pred,
        target_names=["On-time (0)", "Late (1)"],
        digits=4,
    ))

    # Confusion matrix
    print(_sep("-"))
    print("  Confusion Matrix")
    print(_sep("-"))
    cm = confusion_matrix(y_test, y_pred)
    labels = ["On-time", "Late"]
    header_str = "            " + "  ".join(f"{lbl:>10s}" for lbl in labels)
    print(header_str)
    for idx, row in enumerate(cm):
        row_str = "  ".join(f"{v:10d}" for v in row)
        print(f"  {labels[idx]:>8s}  {row_str}")

    # Feature importance (top 15)
    print(f"\n{_sep('-')}")
    print("  Top 15 Feature Importances (gain)")
    print(_sep("-"))
    feature_names_out = preprocessor.get_feature_names_out()
    importances = model.feature_importances_
    top_idx = np.argsort(importances)[::-1][:15]
    for rank, idx in enumerate(top_idx, 1):
        print(f"   {rank:2d}. {feature_names_out[idx]:45s}  {importances[idx]:.4f}")

    # ── 7. Save model artifacts ─────────────────────────────────
    _section("7. Saving model artifacts")

    # 7a. Model
    joblib.dump(model, MODEL_PATH)
    print(f"   Model saved          : {MODEL_PATH}")

    # 7b. Feature names (the raw input features, not transformed)
    with open(FEATURE_NAMES_PATH, "w", encoding="utf-8") as fh:
        json.dump({
            "all_features": ALL_FEATURES,
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
            "transformed_feature_names": list(feature_names_out),
        }, fh, indent=2)
    print(f"   Feature names saved  : {FEATURE_NAMES_PATH}")

    # 7c. Training metadata
    metadata = {
        "model_version": "xgboost-dataco-v1",
        "dataset": "DataCoSupplyChainDataset.csv",
        "target": TARGET_COLUMN,
        "accuracy": round(float(acc), 6),
        "precision": round(float(prec), 6),
        "recall": round(float(rec), 6),
        "f1": round(float(f1), 6),
        "roc_auc": round(float(auc), 6),
        "train_samples": int(len(X_train)),
        "test_samples": int(len(X_test)),
        "feature_count_raw": len(ALL_FEATURES),
        "feature_count_transformed": int(X_train_processed.shape[1]),
        "class_distribution": {
            "on_time": int(np.sum(y == 0)),
            "late": int(np.sum(y == 1)),
        },
        "model_params": {k: str(v) if not isinstance(v, (int, float, bool)) else v
                         for k, v in model_params.items()},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with open(METADATA_PATH, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)
    print(f"   Metadata saved       : {METADATA_PATH}")

    _header("Training pipeline complete")


if __name__ == "__main__":
    main()
