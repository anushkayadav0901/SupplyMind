# scripts/model_diagnostics.py
"""
Comprehensive diagnostic analysis of the DataCo late-delivery risk model.
Outputs feature importance, error analysis, dominance check, and improvement signals.
"""

import sys, os
from pathlib import Path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from xgboost import XGBClassifier

from ml.feature_engineering import (
    ALL_FEATURES, NUMERIC_FEATURES, CATEGORICAL_FEATURES,
    TARGET_COLUMN, load_dataset, prepare_features, build_preprocessor
)

DATASET_PATH = str(_ROOT / "data" / "datasets" / "DataCoSupplyChainDataset.csv")
MODEL_PATH = str(_ROOT / "ml" / "models" / "vendor_risk_model.joblib")
PREPROCESSOR_PATH = str(_ROOT / "ml" / "models" / "preprocessor.joblib")

SEP = "=" * 72
SUBSEP = "-" * 72

# Load everything
print(f"{SEP}\n  LOADING DATA AND MODEL\n{SEP}")
df = load_dataset(DATASET_PATH)
X, y = prepare_features(df)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, stratify=y, random_state=42
)

preprocessor = joblib.load(PREPROCESSOR_PATH)
model = joblib.load(MODEL_PATH)

X_train_t = preprocessor.transform(X_train)
X_test_t = preprocessor.transform(X_test)
y_pred = model.predict(X_test_t)
y_proba = model.predict_proba(X_test_t)[:, 1]

feature_names_out = preprocessor.get_feature_names_out()
importances = model.feature_importances_

# ═══════════════════════════════════════════════════════════════
# 1. FEATURE IMPORTANCE ANALYSIS
# ═══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  1. FEATURE IMPORTANCE (ALL {len(feature_names_out)} TRANSFORMED FEATURES)\n{SEP}")
sorted_idx = np.argsort(importances)[::-1]
cumulative = 0
for rank, idx in enumerate(sorted_idx, 1):
    cumulative += importances[idx]
    marker = " <<<" if importances[idx] >= 0.01 else ""
    print(f"  {rank:3d}. {feature_names_out[idx]:50s}  {importances[idx]:.4f}  (cum={cumulative:.4f}){marker}")
    if rank >= 30:
        break

# Group importance by original feature
print(f"\n{SUBSEP}\n  IMPORTANCE GROUPED BY ORIGINAL FEATURE\n{SUBSEP}")
group_imp = {}
for fname, imp in zip(feature_names_out, importances):
    if fname.startswith("num__"):
        orig = fname.replace("num__", "")
    elif fname.startswith("cat__"):
        orig = fname.split("_", 2)[1].rsplit("_", 1)[0]
        # Fix: get actual original feature name
        for cf in CATEGORICAL_FEATURES:
            if fname.startswith(f"cat__{cf}_"):
                orig = cf
                break
    else:
        orig = fname
    group_imp[orig] = group_imp.get(orig, 0) + imp

for feat, imp in sorted(group_imp.items(), key=lambda x: -x[1]):
    pct = imp * 100
    bar = "#" * int(pct)
    print(f"  {feat:40s}  {imp:.4f}  ({pct:5.1f}%)  {bar}")

# ═══════════════════════════════════════════════════════════════
# 2. CLASS DISTRIBUTION
# ═══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  2. CLASS DISTRIBUTION\n{SEP}")
for label, name in [(0, "On-time"), (1, "Late")]:
    n_total = np.sum(y == label)
    n_train = np.sum(y_train == label)
    n_test = np.sum(y_test == label)
    print(f"  {name:10s}  total={n_total:7,d} ({n_total/len(y)*100:.1f}%)  "
          f"train={n_train:7,d}  test={n_test:7,d}")

# ═══════════════════════════════════════════════════════════════
# 3. CONFUSION MATRIX ANALYSIS
# ═══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  3. CONFUSION MATRIX ANALYSIS\n{SEP}")
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()
print(f"  True Negatives  (correctly predicted on-time) : {tn:,d}")
print(f"  False Positives (on-time predicted as late)   : {fp:,d}")
print(f"  False Negatives (late predicted as on-time)   : {fn:,d}")
print(f"  True Positives  (correctly predicted late)    : {tp:,d}")
print()
print(f"  Total test samples: {len(y_test):,d}")
print(f"  Correct: {tn+tp:,d} ({(tn+tp)/len(y_test)*100:.1f}%)")
print(f"  Wrong:   {fp+fn:,d} ({(fp+fn)/len(y_test)*100:.1f}%)")
print()
print(f"  Precision (late) : {tp/(tp+fp)*100:.1f}% — when we say 'late', we're right {tp/(tp+fp)*100:.1f}% of the time")
print(f"  Recall (late)    : {tp/(tp+fn)*100:.1f}% — we catch {tp/(tp+fn)*100:.1f}% of actual late deliveries")
print(f"  Specificity      : {tn/(tn+fp)*100:.1f}% — we correctly identify {tn/(tn+fp)*100:.1f}% of on-time deliveries")
print()
print(f"  KEY PROBLEM: {fn:,d} false negatives — late deliveries we MISS")
print(f"  This is {fn/np.sum(y_test==1)*100:.1f}% of all late deliveries going undetected")

# ═══════════════════════════════════════════════════════════════
# 4. ERROR ANALYSIS — WHERE DOES THE MODEL FAIL?
# ═══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  4. ERROR ANALYSIS\n{SEP}")

# Rebuild test DataFrame with predictions
test_df = X_test.copy()
test_df["y_true"] = y_test
test_df["y_pred"] = y_pred
test_df["y_proba"] = y_proba

# Error rates by Shipping Mode
print(f"\n{SUBSEP}\n  ERROR RATE BY SHIPPING MODE\n{SUBSEP}")
for mode in test_df["Shipping Mode"].unique():
    mask = test_df["Shipping Mode"] == mode
    sub = test_df[mask]
    acc = accuracy_score(sub["y_true"], sub["y_pred"])
    n = len(sub)
    actual_late_rate = sub["y_true"].mean()
    pred_late_rate = sub["y_pred"].mean()
    err = 1 - acc
    print(f"  {mode:20s}  n={n:6,d}  actual_late={actual_late_rate:.1%}  "
          f"pred_late={pred_late_rate:.1%}  acc={acc:.1%}  err={err:.1%}")

# Error rates by Days for shipment (scheduled)
print(f"\n{SUBSEP}\n  ERROR RATE BY DAYS FOR SHIPMENT (SCHEDULED)\n{SUBSEP}")
for days in sorted(test_df["Days for shipment (scheduled)"].unique()):
    mask = test_df["Days for shipment (scheduled)"] == days
    sub = test_df[mask]
    acc = accuracy_score(sub["y_true"], sub["y_pred"])
    actual_late = sub["y_true"].mean()
    pred_late = sub["y_pred"].mean()
    print(f"  Days={days}  n={len(sub):6,d}  actual_late={actual_late:.1%}  "
          f"pred_late={pred_late:.1%}  acc={acc:.1%}")

# Hardest cases — high-confidence wrong predictions
print(f"\n{SUBSEP}\n  CONFIDENCE DISTRIBUTION OF ERRORS\n{SUBSEP}")
wrong = test_df[test_df["y_true"] != test_df["y_pred"]]
fn_mask = (test_df["y_true"] == 1) & (test_df["y_pred"] == 0)
fp_mask = (test_df["y_true"] == 0) & (test_df["y_pred"] == 1)

fn_probas = test_df[fn_mask]["y_proba"]
fp_probas = test_df[fp_mask]["y_proba"]

print(f"  False Negatives (missed late): n={len(fn_probas):,d}")
print(f"    P(late) mean={fn_probas.mean():.4f}  median={fn_probas.median():.4f}  "
      f"std={fn_probas.std():.4f}  min={fn_probas.min():.4f}  max={fn_probas.max():.4f}")
print(f"  False Positives (false alarm): n={len(fp_probas):,d}")
print(f"    P(late) mean={fp_probas.mean():.4f}  median={fp_probas.median():.4f}  "
      f"std={fp_probas.std():.4f}  min={fp_probas.min():.4f}  max={fp_probas.max():.4f}")

# ═══════════════════════════════════════════════════════════════
# 5. DOMINANCE CHECK — MODEL WITHOUT TOP FEATURES
# ═══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  5. DOMINANCE CHECK — ABLATION STUDY\n{SEP}")

# 5a. Full model (baseline)
full_acc = accuracy_score(y_test, y_pred)
full_auc = roc_auc_score(y_test, y_proba)
print(f"  FULL MODEL (all 13 features)   : acc={full_acc:.4f}  auc={full_auc:.4f}")

# 5b. Without Shipping Mode
features_no_ship = [f for f in ALL_FEATURES if f != "Shipping Mode"]
X_no_ship = X[features_no_ship]
pre_no_ship = build_preprocessor()
# Rebuild preprocessor for this subset
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
num_no_ship = [f for f in NUMERIC_FEATURES]
cat_no_ship = [f for f in CATEGORICAL_FEATURES if f != "Shipping Mode"]
pre_no_ship = ColumnTransformer([
    ("num", StandardScaler(), num_no_ship),
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_no_ship),
], remainder="drop")
Xtr_ns, Xte_ns = X_no_ship.iloc[X_train.index], X_no_ship.iloc[X_test.index]
# Use same split indices
Xtr_ns = X_no_ship.loc[X_train.index]
Xte_ns = X_no_ship.loc[X_test.index]
Xtr_ns_t = pre_no_ship.fit_transform(Xtr_ns)
Xte_ns_t = pre_no_ship.transform(Xte_ns)
m_ns = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                      objective="binary:logistic", eval_metric="logloss",
                      random_state=42, n_jobs=-1)
m_ns.fit(Xtr_ns_t, y_train)
p_ns = m_ns.predict(Xte_ns_t)
pp_ns = m_ns.predict_proba(Xte_ns_t)[:, 1]
print(f"  WITHOUT Shipping Mode          : acc={accuracy_score(y_test, p_ns):.4f}  "
      f"auc={roc_auc_score(y_test, pp_ns):.4f}")

# 5c. Without Days for shipment (scheduled)
num_no_days = [f for f in NUMERIC_FEATURES if f != "Days for shipment (scheduled)"]
cat_no_days = CATEGORICAL_FEATURES
pre_no_days = ColumnTransformer([
    ("num", StandardScaler(), num_no_days),
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_no_days),
], remainder="drop")
features_no_days = num_no_days + cat_no_days
X_no_days = X[features_no_days]
Xtr_nd = X_no_days.loc[X_train.index]
Xte_nd = X_no_days.loc[X_test.index]
Xtr_nd_t = pre_no_days.fit_transform(Xtr_nd)
Xte_nd_t = pre_no_days.transform(Xte_nd)
m_nd = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                      objective="binary:logistic", eval_metric="logloss",
                      random_state=42, n_jobs=-1)
m_nd.fit(Xtr_nd_t, y_train)
p_nd = m_nd.predict(Xte_nd_t)
pp_nd = m_nd.predict_proba(Xte_nd_t)[:, 1]
print(f"  WITHOUT Days for shipment      : acc={accuracy_score(y_test, p_nd):.4f}  "
      f"auc={roc_auc_score(y_test, pp_nd):.4f}")

# 5d. WITHOUT both Shipping Mode AND Days for shipment
num_no_both = [f for f in NUMERIC_FEATURES if f != "Days for shipment (scheduled)"]
cat_no_both = [f for f in CATEGORICAL_FEATURES if f != "Shipping Mode"]
pre_no_both = ColumnTransformer([
    ("num", StandardScaler(), num_no_both),
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_no_both),
], remainder="drop")
features_no_both = num_no_both + cat_no_both
X_no_both = X[features_no_both]
Xtr_nb = X_no_both.loc[X_train.index]
Xte_nb = X_no_both.loc[X_test.index]
Xtr_nb_t = pre_no_both.fit_transform(Xtr_nb)
Xte_nb_t = pre_no_both.transform(Xte_nb)
m_nb = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                      objective="binary:logistic", eval_metric="logloss",
                      random_state=42, n_jobs=-1)
m_nb.fit(Xtr_nb_t, y_train)
p_nb = m_nb.predict(Xte_nb_t)
pp_nb = m_nb.predict_proba(Xte_nb_t)[:, 1]
print(f"  WITHOUT BOTH (remaining 11)    : acc={accuracy_score(y_test, p_nb):.4f}  "
      f"auc={roc_auc_score(y_test, pp_nb):.4f}")

# 5e. ONLY Shipping Mode + Days
num_only = ["Days for shipment (scheduled)"]
cat_only = ["Shipping Mode"]
pre_only = ColumnTransformer([
    ("num", StandardScaler(), num_only),
    ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat_only),
], remainder="drop")
X_only = X[num_only + cat_only]
Xtr_o = X_only.loc[X_train.index]
Xte_o = X_only.loc[X_test.index]
Xtr_o_t = pre_only.fit_transform(Xtr_o)
Xte_o_t = pre_only.transform(Xte_o)
m_o = XGBClassifier(n_estimators=200, max_depth=6, learning_rate=0.1,
                     objective="binary:logistic", eval_metric="logloss",
                     random_state=42, n_jobs=-1)
m_o.fit(Xtr_o_t, y_train)
p_o = m_o.predict(Xte_o_t)
pp_o = m_o.predict_proba(Xte_o_t)[:, 1]
print(f"  ONLY Shipping Mode + Days      : acc={accuracy_score(y_test, p_o):.4f}  "
      f"auc={roc_auc_score(y_test, pp_o):.4f}")

# ═══════════════════════════════════════════════════════════════
# 6. CROSS-VALIDATION
# ═══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  6. CROSS-VALIDATION (5-fold, full model)\n{SEP}")
X_all_t = preprocessor.transform(X)
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(model, X_all_t, y, cv=cv, scoring="accuracy", n_jobs=-1)
cv_auc = cross_val_score(model, X_all_t, y, cv=cv, scoring="roc_auc", n_jobs=-1)
print(f"  Accuracy: {cv_scores.mean():.4f} +/- {cv_scores.std():.4f}  folds={cv_scores}")
print(f"  ROC AUC:  {cv_auc.mean():.4f} +/- {cv_auc.std():.4f}  folds={cv_auc}")

# ═══════════════════════════════════════════════════════════════
# 7. CHECK POTENTIAL NEW FEATURES
# ═══════════════════════════════════════════════════════════════
print(f"\n{SEP}\n  7. POTENTIAL NEW FEATURES — SIGNAL CHECK\n{SEP}")

# 7a. Order Region
print(f"\n{SUBSEP}\n  ORDER REGION vs LATE DELIVERY\n{SUBSEP}")
region_rates = df.groupby("Order Region")["Late_delivery_risk"].agg(["mean", "count"])
region_rates = region_rates.sort_values("mean", ascending=False)
for reg, row in region_rates.iterrows():
    print(f"  {reg:30s}  late_rate={row['mean']:.3f}  n={int(row['count']):,d}")

# 7b. Department Name
print(f"\n{SUBSEP}\n  DEPARTMENT NAME vs LATE DELIVERY\n{SUBSEP}")
dept_rates = df.groupby("Department Name")["Late_delivery_risk"].agg(["mean", "count"])
dept_rates = dept_rates.sort_values("mean", ascending=False)
for dept, row in dept_rates.iterrows():
    print(f"  {dept:30s}  late_rate={row['mean']:.3f}  n={int(row['count']):,d}")

# 7c. Order Country diversity
print(f"\n{SUBSEP}\n  ORDER COUNTRY — TOP 15 vs LATE DELIVERY\n{SUBSEP}")
country_rates = df.groupby("Order Country")["Late_delivery_risk"].agg(["mean", "count"])
country_rates = country_rates.sort_values("count", ascending=False).head(15)
for c, row in country_rates.iterrows():
    print(f"  {c:30s}  late_rate={row['mean']:.3f}  n={int(row['count']):,d}")

# 7d. Date features — check if hour/day_of_week matter
print(f"\n{SUBSEP}\n  DATE-DERIVED FEATURES — SIGNAL CHECK\n{SUBSEP}")
df_dates = df.copy()
df_dates["order_dt"] = pd.to_datetime(df_dates["order date (DateOrders)"], format="mixed")
df_dates["order_hour"] = df_dates["order_dt"].dt.hour
df_dates["order_dow"] = df_dates["order_dt"].dt.dayofweek
df_dates["order_month"] = df_dates["order_dt"].dt.month

for col in ["order_hour", "order_dow", "order_month"]:
    corr = df_dates[col].corr(df_dates["Late_delivery_risk"])
    grp = df_dates.groupby(col)["Late_delivery_risk"].mean()
    var = grp.std()
    print(f"  {col:20s}  corr={corr:+.4f}  late_rate_std_across_groups={var:.4f}  "
          f"min={grp.min():.3f}  max={grp.max():.3f}")

# 7e. Customer order frequency as a feature
print(f"\n{SUBSEP}\n  CUSTOMER ORDER FREQUENCY — SIGNAL CHECK\n{SUBSEP}")
cust_freq = df.groupby("Customer Id").size().rename("order_count")
df_freq = df.merge(cust_freq, left_on="Customer Id", right_index=True)
corr_freq = df_freq["order_count"].corr(df_freq["Late_delivery_risk"])
print(f"  Customer order count corr with late_risk: {corr_freq:+.4f}")
freq_bins = pd.cut(df_freq["order_count"], bins=[0, 5, 10, 20, 50, 200])
freq_rate = df_freq.groupby(freq_bins, observed=True)["Late_delivery_risk"].mean()
for b, rate in freq_rate.items():
    print(f"    orders {b}: late_rate={rate:.3f}")

# 7f. Benefit per order / profit ratio interactions
print(f"\n{SUBSEP}\n  PROFIT FEATURES — SIGNAL CHECK\n{SUBSEP}")
for col in ["Benefit per order", "Order Item Profit Ratio"]:
    corr = df[col].corr(df["Late_delivery_risk"])
    print(f"  {col:35s}  corr={corr:+.4f}")

print(f"\n{SEP}\n  DIAGNOSTICS COMPLETE\n{SEP}")
