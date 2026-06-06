# scripts/test_prediction.py
"""Quick test for the ML risk predictor — runs predictions with DataCo features."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from ml.predict import RiskPredictor

predictor = RiskPredictor()

# Simulate a high-risk order (First Class shipping — 95% late rate)
high_risk = predictor.predict({
    "Shipping Mode": "First Class",
    "Days for shipment (scheduled)": 1,
    "Type": "DEBIT",
    "Market": "LATAM",
    "Customer Segment": "Consumer",
    "Category Name": "Cleats",
    "Order Item Quantity": 3,
    "Order Item Discount": 5.0,
    "Order Item Discount Rate": 0.05,
    "Order Item Product Price": 120.0,
    "Sales": 360.0,
    "Order Profit Per Order": 45.0,
    "Product Price": 120.0,
})

# Simulate a low-risk order (Standard Class shipping — 38% late rate)
low_risk = predictor.predict({
    "Shipping Mode": "Standard Class",
    "Days for shipment (scheduled)": 4,
    "Type": "TRANSFER",
    "Market": "Europe",
    "Customer Segment": "Corporate",
    "Category Name": "Men's Footwear",
    "Order Item Quantity": 1,
    "Order Item Discount": 0.0,
    "Order Item Discount Rate": 0.0,
    "Order Item Product Price": 50.0,
    "Sales": 50.0,
    "Order Profit Per Order": 15.0,
    "Product Price": 50.0,
})

# Simulate a medium-risk order (Second Class shipping — 77% late rate)
med_risk = predictor.predict({
    "Shipping Mode": "Second Class",
    "Days for shipment (scheduled)": 2,
    "Type": "PAYMENT",
    "Market": "Pacific Asia",
    "Customer Segment": "Home Office",
    "Category Name": "Indoor/Outdoor Games",
    "Order Item Quantity": 2,
    "Order Item Discount": 10.0,
    "Order Item Discount Rate": 0.10,
    "Order Item Product Price": 200.0,
    "Sales": 400.0,
    "Order Profit Per Order": 80.0,
    "Product Price": 200.0,
})

for name, result in [("HIGH-RISK (First Class)", high_risk),
                      ("LOW-RISK (Standard Class)", low_risk),
                      ("MEDIUM-RISK (Second Class)", med_risk)]:
    print("=" * 60)
    print(f"  {name} ORDER PREDICTION")
    print("=" * 60)
    print(f"  Risk Label      : {result['risk_label']}")
    print(f"  Risk Score      : {result['risk_score']}")
    print(f"  P(late)         : {result['probabilities']['late']}")
    print(f"  P(on_time)      : {result['probabilities']['on_time']}")
    print(f"  Model           : {result['model_version']}")
    print()

print("=" * 60)
print("  HEALTH CHECK")
print("=" * 60)
health = predictor.health_check()
for k, v in health.items():
    print(f"  {k}: {v}")
