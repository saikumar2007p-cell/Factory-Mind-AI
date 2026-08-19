"""
ml/train_anomaly.py

Trains an Isolation Forest anomaly detector on authentic NASA C-MAPSS FD001 turbofan telemetry.

Produces reproducible anomaly scores [0, 1] reflecting engine health deviation:
- 0.0: Nominal / Healthy baseline operation
- 1.0: Severe degradation / Extreme operational anomaly
- Saves trained model and threshold artifacts to ml/artifacts/
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

ARTIFACTS_DIR = ROOT_DIR / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

from ml.dataset import CMAPSSDataset
from ml.features import FeatureEngineer

RANDOM_SEED = 42


def train_anomaly_model() -> Dict[str, Any]:
    print("================================================================")
    print(" FactoryMind AI — Anomaly Detection Model (Isolation Forest)     ")
    print("================================================================")

    np.random.seed(RANDOM_SEED)

    # 1. Load dataset & features
    dataset = CMAPSSDataset()
    print("\n[1/4] Loading authentic C-MAPSS FD001 dataset...")
    df_raw = dataset.load_raw_train()
    
    # Load or instantiate feature engineer
    feat_eng_path = ARTIFACTS_DIR / "feature_engineer.joblib"
    if feat_eng_path.exists():
        print("      Loading existing fitted FeatureEngineer...")
        feature_engineer = joblib.load(feat_eng_path)
        df_features = feature_engineer.transform(df_raw)
    else:
        print("      Fitting new FeatureEngineer...")
        feature_engineer = FeatureEngineer()
        df_features = feature_engineer.fit_transform(df_raw)
        joblib.dump(feature_engineer, feat_eng_path)

    feature_names = feature_engineer.get_feature_names()
    X = df_features[feature_names]
    print(f"      Feature matrix shape: {X.shape}")

    # 2. Train Isolation Forest
    print("\n[2/4] Training Isolation Forest model...")
    model_params = {
        "n_estimators": 200,
        "max_samples": "auto",
        "contamination": 0.05,  # Nominal 5% expected anomalous cycles at high degradation
        "max_features": 1.0,
        "bootstrap": False,
        "random_state": RANDOM_SEED,
        "n_jobs": -1
    }

    model = IsolationForest(**model_params)
    model.fit(X)

    # 3. Compute decision function and calibrate anomaly score mapping
    print("\n[3/4] Calibrating anomaly score distributions...")
    raw_scores = model.decision_function(X)  # Lower values indicate anomalies
    preds = model.predict(X)                 # -1 for anomaly, +1 for normal

    min_val = float(np.min(raw_scores))
    max_val = float(np.max(raw_scores))
    p5 = float(np.percentile(raw_scores, 5))
    p50 = float(np.percentile(raw_scores, 50))
    p95 = float(np.percentile(raw_scores, 95))

    anomalous_count = int(np.sum(preds == -1))
    normal_count = int(np.sum(preds == 1))
    anomaly_percentage = float(anomalous_count / len(preds) * 100)

    print(f"  -> Total observations:        {len(preds):,}")
    print(f"  -> Normal cycles (+1):        {normal_count:,} ({100 - anomaly_percentage:.2f}%)")
    print(f"  -> Anomalous cycles (-1):     {anomalous_count:,} ({anomaly_percentage:.2f}%)")
    print(f"  -> Decision function range:   [{min_val:.4f}, {max_val:.4f}]")
    print(f"  -> 5th percentile threshold:  {p5:.4f}")
    print(f"  -> Median score:              {p50:.4f}")

    # 4. Save Artifacts
    print("\n[4/4] Serializing anomaly model and calibration parameters...")
    anomaly_model_path = ARTIFACTS_DIR / "anomaly_model.joblib"
    anomaly_meta_path = ARTIFACTS_DIR / "anomaly_metadata.json"

    joblib.dump(model, anomaly_model_path)

    calibration_metadata = {
        "model_type": "IsolationForest",
        "model_params": model_params,
        "random_seed": RANDOM_SEED,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_records": len(X),
        "total_features": len(feature_names),
        "anomaly_count": anomalous_count,
        "anomaly_percentage": round(anomaly_percentage, 2),
        "decision_function_stats": {
            "min": round(min_val, 4),
            "max": round(max_val, 4),
            "p05_threshold": round(p5, 4),
            "p50_median": round(p50, 4),
            "p95": round(p95, 4)
        }
    }

    with open(anomaly_meta_path, "w", encoding="utf-8") as f:
        json.dump(calibration_metadata, f, indent=2)

    print(f"[SUCCESS] Anomaly model saved to {anomaly_model_path}")
    print(f"[SUCCESS] Calibration metadata saved to {anomaly_meta_path}")

    return calibration_metadata


if __name__ == "__main__":
    train_anomaly_model()
