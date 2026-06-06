# scripts/diagnostics_part2.py
"""Remaining diagnostics: CV + new feature signal checks."""

import sys
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier
from ml.feature_engineering import load_dataset, prepare_features

df = load_dataset(str(_ROOT / "data" / "datasets" / "DataCoSupplyChainDataset.csv"))
X, y = prepare_features(df)
preprocessor = joblib.load(str(_ROOT / "ml" / "models" / "preprocessor.joblib"))
X_t = preprocessor.transform(X)

# Manual 5-fold CV
print("=" * 60)
print("  5-FOLD CROSS-VALIDATION")
print("=" * 60)
kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
accs, aucs = [], []
for fold, (tr, te) in enumerate(kf.split(X_t, y), 1):
    m = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                      objective="binary:logistic", eval_metric="logloss",
                      random_state=42, n_jobs=-1)
    m.fit(X_t[tr], y[tr])
    p = m.predict(X_t[te])
    pp = m.predict_proba(X_t[te])[:, 1]
    a = accuracy_score(y[te], p)
    au = roc_auc_score(y[te], pp)
    accs.append(a)
    aucs.append(au)
    print(f"  Fold {fold}: acc={a:.4f}  auc={au:.4f}")
print(f"  Mean: acc={np.mean(accs):.4f} +/- {np.std(accs):.4f}  auc={np.mean(aucs):.4f} +/- {np.std(aucs):.4f}")

# New feature signals
print("\n" + "=" * 60)
print("  NEW FEATURE SIGNAL CHECKS")
print("=" * 60)

print("\n--- ORDER REGION vs LATE DELIVERY ---")
rr = df.groupby("Order Region")["Late_delivery_risk"].agg(["mean", "count"])
rr = rr.sort_values("mean", ascending=False)
for r, row in rr.iterrows():
    print(f"  {r:35s}  late={row['mean']:.3f}  n={int(row['count']):,d}")

print("\n--- DEPARTMENT NAME vs LATE DELIVERY ---")
dr = df.groupby("Department Name")["Late_delivery_risk"].agg(["mean", "count"])
dr = dr.sort_values("mean", ascending=False)
for d, row in dr.iterrows():
    print(f"  {d:35s}  late={row['mean']:.3f}  n={int(row['count']):,d}")

print("\n--- DATE-DERIVED FEATURES ---")
df["order_dt"] = pd.to_datetime(df["order date (DateOrders)"], format="mixed")
df["order_hour"] = df["order_dt"].dt.hour
df["order_dow"] = df["order_dt"].dt.dayofweek
df["order_month"] = df["order_dt"].dt.month
df["order_year"] = df["order_dt"].dt.year
for col in ["order_hour", "order_dow", "order_month", "order_year"]:
    corr = df[col].corr(df["Late_delivery_risk"])
    grp = df.groupby(col)["Late_delivery_risk"].mean()
    print(f"  {col:20s}  corr={corr:+.4f}  late_std={grp.std():.4f}  min={grp.min():.3f}  max={grp.max():.3f}")

print("\n--- CUSTOMER ORDER FREQUENCY ---")
cfreq = df.groupby("Customer Id").size().rename("order_count")
dff = df.merge(cfreq, left_on="Customer Id", right_index=True)
corr_freq = dff["order_count"].corr(dff["Late_delivery_risk"])
print(f"  corr with late_risk: {corr_freq:+.4f}")

print("\n--- BENEFIT / PROFIT FEATURES ---")
for c in ["Benefit per order", "Order Item Profit Ratio", "Sales per customer"]:
    corr = df[c].corr(df["Late_delivery_risk"])
    print(f"  {c:35s}  corr={corr:+.4f}")

print("\n--- ROUTE: ORDER COUNTRY VOLUME ---")
country_freq = df.groupby("Order Country").size().rename("country_order_count")
dfc = df.merge(country_freq, left_on="Order Country", right_index=True)
corr_country = dfc["country_order_count"].corr(dfc["Late_delivery_risk"])
print(f"  corr with late_risk: {corr_country:+.4f}")

# Check the actual late rate within Standard Class (the problem area)
print("\n--- STANDARD CLASS DEEP DIVE ---")
std = df[df["Shipping Mode"] == "Standard Class"]
print(f"  n={len(std):,d}  late_rate={std['Late_delivery_risk'].mean():.3f}")
for col in ["Type", "Market", "Customer Segment"]:
    print(f"\n  {col}:")
    sub = std.groupby(col)["Late_delivery_risk"].agg(["mean", "count"])
    for val, row in sub.sort_values("mean", ascending=False).iterrows():
        print(f"    {val:25s}  late={row['mean']:.3f}  n={int(row['count']):,d}")

print("\n" + "=" * 60)
print("  COMPLETE")
print("=" * 60)
