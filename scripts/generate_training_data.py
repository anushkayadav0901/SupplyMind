# scripts/generate_training_data.py
"""Generate a synthetic vendor risk training dataset with realistic correlations.

Creates 1000 vendor records with correlated features across four risk tiers
(low, medium, high, critical) and saves the result as a CSV file.

Usage:
    python scripts/generate_training_data.py
"""

import os
import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
NUM_VENDORS = 1000
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "data", "training")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "vendor_risk_dataset.csv")

# Class distribution: low=40%, medium=30%, high=20%, critical=10%
CLASS_COUNTS = {
    "low": int(NUM_VENDORS * 0.40),
    "medium": int(NUM_VENDORS * 0.30),
    "high": int(NUM_VENDORS * 0.20),
    "critical": NUM_VENDORS - int(NUM_VENDORS * 0.40)
                             - int(NUM_VENDORS * 0.30)
                             - int(NUM_VENDORS * 0.20),
}

# Per-class feature ranges: (low_bound, high_bound)
# These define the *centre* ranges before noise is added.
PROFILES = {
    "low": {
        "on_time_delivery_rate":       (0.85, 0.99),
        "average_delivery_delay_days": (0,    5),
        "defect_rate":                 (0.00, 0.05),
        "cancellation_rate":           (0.00, 0.05),
        "return_rate":                 (0.00, 0.06),
        "compliance_score":            (80,   100),
        "order_volume":                (200,  5000),
        "average_order_value":         (5000, 500000),
        "quote_rejection_rate":        (0.00, 0.08),
        "payment_delay_rate":          (0.00, 0.05),
        "historical_penalty_count":    (0,    3),
    },
    "medium": {
        "on_time_delivery_rate":       (0.70, 0.90),
        "average_delivery_delay_days": (3,    15),
        "defect_rate":                 (0.03, 0.12),
        "cancellation_rate":           (0.03, 0.12),
        "return_rate":                 (0.04, 0.15),
        "compliance_score":            (60,   85),
        "order_volume":                (100,  3500),
        "average_order_value":         (3000, 350000),
        "quote_rejection_rate":        (0.05, 0.20),
        "payment_delay_rate":          (0.03, 0.15),
        "historical_penalty_count":    (2,    12),
    },
    "high": {
        "on_time_delivery_rate":       (0.50, 0.75),
        "average_delivery_delay_days": (10,   35),
        "defect_rate":                 (0.08, 0.25),
        "cancellation_rate":           (0.10, 0.25),
        "return_rate":                 (0.10, 0.30),
        "compliance_score":            (35,   65),
        "order_volume":                (50,   2000),
        "average_order_value":         (1000, 200000),
        "quote_rejection_rate":        (0.15, 0.40),
        "payment_delay_rate":          (0.10, 0.30),
        "historical_penalty_count":    (5,    25),
    },
    "critical": {
        "on_time_delivery_rate":       (0.20, 0.55),
        "average_delivery_delay_days": (25,   60),
        "defect_rate":                 (0.15, 0.50),
        "cancellation_rate":           (0.20, 0.50),
        "return_rate":                 (0.20, 0.50),
        "compliance_score":            (5,    40),
        "order_volume":                (1,    800),
        "average_order_value":         (1000, 100000),
        "quote_rejection_rate":        (0.30, 0.70),
        "payment_delay_rate":          (0.25, 0.60),
        "historical_penalty_count":    (10,   50),
    },
}

# Gaussian noise standard-deviation as a fraction of each feature's range
NOISE_FRAC = 0.08

# Hard limits to clip features into valid domains
CLIP_RULES = {
    "on_time_delivery_rate":       (0.0, 1.0),
    "average_delivery_delay_days": (0,   60),
    "defect_rate":                 (0.0, 1.0),
    "cancellation_rate":           (0.0, 1.0),
    "return_rate":                 (0.0, 1.0),
    "compliance_score":            (0.0, 100.0),
    "order_volume":                (1,   5000),
    "average_order_value":         (1000, 500000),
    "quote_rejection_rate":        (0.0, 1.0),
    "payment_delay_rate":          (0.0, 1.0),
    "historical_penalty_count":    (0,   50),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _generate_vendor_names(n: int, rng: np.random.Generator) -> list[str]:
    """Create unique, plausible vendor names."""
    prefixes = [
        "Alpha", "Beta", "Delta", "Sigma", "Omega", "Nova", "Prime", "Core",
        "Apex", "Vertex", "Zenith", "Nexus", "Titan", "Vanguard", "Stellar",
        "Pinnacle", "Summit", "Pacific", "Atlantic", "Global", "Metro",
        "Eagle", "Falcon", "Phoenix", "Orion", "Crest", "Peak", "Atlas",
        "Mercury", "Neptune", "Saturn", "Pulsar", "Quantum", "Cobalt",
        "Granite", "Sapphire", "Emerald", "Onyx", "Jade", "Amber",
    ]
    suffixes = [
        "Industries", "Corp", "Solutions", "Supplies", "Logistics",
        "Materials", "Enterprises", "Group", "Trading", "Partners",
        "Systems", "Services", "Manufacturing", "Distribution", "Global",
        "Technologies", "Components", "Resources", "Networks", "Ventures",
    ]
    names: list[str] = []
    seen: set[str] = set()
    while len(names) < n:
        name = (rng.choice(prefixes) + " "
                + rng.choice(suffixes) + " "
                + str(rng.integers(100, 9999)))
        if name not in seen:
            seen.add(name)
            names.append(name)
    return names


def _sample_feature(rng: np.random.Generator, low: float, high: float,
                    n: int, noise_std: float) -> np.ndarray:
    """Sample *n* values uniformly in [low, high] and add Gaussian noise."""
    values = rng.uniform(low, high, size=n)
    noise = rng.normal(0, noise_std, size=n)
    return values + noise


# ---------------------------------------------------------------------------
# Main generation routine
# ---------------------------------------------------------------------------

def generate_dataset() -> pd.DataFrame:
    """Build the full synthetic dataset and return it as a DataFrame."""
    rng = np.random.default_rng(RANDOM_SEED)
    frames: list[pd.DataFrame] = []

    for label, count in CLASS_COUNTS.items():
        profile = PROFILES[label]
        record: dict[str, np.ndarray] = {}

        for feat, (lo, hi) in profile.items():
            feat_range = hi - lo if hi != lo else 1.0
            noise_std = feat_range * NOISE_FRAC
            raw = _sample_feature(rng, lo, hi, count, noise_std)

            # Clip to hard domain limits
            clip_lo, clip_hi = CLIP_RULES[feat]
            raw = np.clip(raw, clip_lo, clip_hi)

            # Integer features stay as integers
            if feat in ("average_delivery_delay_days", "order_volume",
                        "average_order_value", "historical_penalty_count"):
                raw = np.round(raw).astype(int)

            record[feat] = raw

        df_chunk = pd.DataFrame(record)
        df_chunk["risk_label"] = label
        frames.append(df_chunk)

    df = pd.concat(frames, ignore_index=True)

    # Add vendor names
    df.insert(0, "vendor_name", _generate_vendor_names(len(df), rng))

    # Shuffle rows so classes are not grouped
    df = df.sample(frac=1, random_state=RANDOM_SEED).reset_index(drop=True)

    return df


def print_summary(df: pd.DataFrame) -> None:
    """Print descriptive statistics and class distribution."""
    print("=" * 72)
    print("  SYNTHETIC VENDOR RISK DATASET  --  Summary")
    print("=" * 72)
    print(f"\nTotal vendors : {len(df)}")
    print(f"Columns       : {list(df.columns)}\n")

    print("-" * 72)
    print("Class distribution:")
    print("-" * 72)
    dist = df["risk_label"].value_counts()
    for label in ["low", "medium", "high", "critical"]:
        cnt = dist.get(label, 0)
        pct = cnt / len(df) * 100
        print(f"  {label:10s}  {cnt:5d}  ({pct:5.1f}%)")

    print("\n" + "-" * 72)
    print("Feature statistics:")
    print("-" * 72)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    stats = df[numeric_cols].describe().T
    stats_display = stats[["mean", "std", "min", "max"]]
    print(stats_display.to_string())
    print("=" * 72)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Generating {NUM_VENDORS} synthetic vendor records (seed={RANDOM_SEED}) ...")
    dataset = generate_dataset()
    dataset.to_csv(OUTPUT_PATH, index=False)
    print(f"Dataset saved to: {OUTPUT_PATH}\n")

    print_summary(dataset)
