"""
ml/train_rul.py

Trains the Remaining Useful Life (RUL) regression model using LightGBM on the authentic NASA C-MAPSS FD001 dataset.

Evaluates performance with:
- Trajectory-preserved 80/20 train/validation split
- Ground-truth evaluation on all 100 C-MAPSS test units
- Metrics: RMSE, MAE, R², and the NASA C-MAPSS asymmetric scoring function
- Serializes trained model and preprocessing pipeline to ml/artifacts/
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple
import joblib
import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

ARTIFACTS_DIR = ROOT_DIR / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

RANDOM_SEED = 42

from ml.dataset import CMAPSSDataset, DEFAULT_CLIP_RUL
from ml.features import FeatureEngineer


def calculate_cmapss_score(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Computes the NASA C-MAPSS asymmetric scoring metric.
    Penalizes late predictions (overestimating RUL) more heavily than early predictions (underestimating RUL).
    
    d_i = y_pred_i - y_true_i
    s_i = exp(-d_i / 13) - 1 if d_i < 0 (early prediction)
    s_i = exp(d_i / 10) - 1 if d_i >= 0 (late prediction)
    """
    diff = y_pred - y_true
    score = 0.0
    for d in diff:
        if d < 0:
            score += np.exp(-d / 13.0) - 1.0
        else:
            score += np.exp(d / 10.0) - 1.0
    return float(score)


def train_rul_model() -> Dict[str, Any]:
    print("================================================================")
    print(" FactoryMind AI — RUL Model Training (LightGBM & C-MAPSS FD001) ")
    print("================================================================")

    np.random.seed(RANDOM_SEED)

    # 1. Load authentic dataset
    dataset = CMAPSSDataset()
    print("\n[1/5] Loading real C-MAPSS FD001 dataset...")
    df_raw_train = dataset.get_labeled_train_data(clip_rul=DEFAULT_CLIP_RUL)
    print(f"      Loaded {len(df_raw_train):,} training records across {df_raw_train['unit_number'].nunique()} engines.")

    # 2. Extract features
    print("\n[2/5] Engineering time-series features (zero-leakage backward rolling windows)...")
    feature_engineer = FeatureEngineer()
    df_train_features = feature_engineer.fit_transform(df_raw_train)
    feature_names = feature_engineer.get_feature_names()
    print(f"      Engineered {len(feature_names)} features per cycle.")

    # 3. Trajectory-preserving train/validation split (80 engines train, 20 engines val)
    print("\n[3/5] Performing trajectory-preserving train/val split (80/20 engines)...")
    train_df, val_df = dataset.split_train_val_trajectories(df_train_features, val_fraction=0.2, random_state=RANDOM_SEED)
    
    X_train = train_df[feature_names]
    y_train = train_df["rul"]
    X_val = val_df[feature_names]
    y_val = val_df["rul"]

    print(f"      Training set: {len(X_train):,} cycles ({train_df['unit_number'].nunique()} engines)")
    print(f"      Validation set: {len(X_val):,} cycles ({val_df['unit_number'].nunique()} engines)")

    # 4. Train LightGBM Regressor
    print("\n[4/5] Training LightGBM RUL Regressor...")
    model_params = {
        "n_estimators": 350,
        "learning_rate": 0.03,
        "max_depth": 6,
        "num_leaves": 31,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_samples": 20,
        "random_state": RANDOM_SEED,
        "n_jobs": -1,
        "verbose": -1,
        "objective": "regression"
    }

    start_time = time.time()
    model = LGBMRegressor(**model_params)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
    )
    training_duration_s = time.time() - start_time
    print(f"      Model training completed in {training_duration_s:.2f} seconds.")

    # 5. Evaluate on Validation Set
    val_preds = model.predict(X_val)
    val_rmse = float(np.sqrt(mean_squared_error(y_val, val_preds)))
    val_mae = float(mean_absolute_error(y_val, val_preds))
    val_r2 = float(r2_score(y_val, val_preds))

    print(f"\n[EVALUATION - VALIDATION ENGINES]")
    print(f"  -> Validation RMSE: {val_rmse:.2f} cycles")
    print(f"  -> Validation MAE:  {val_mae:.2f} cycles")
    print(f"  -> Validation R²:   {val_r2:.4f}")

    # 6. Evaluate on Authentic NASA Test Set (all 100 test engines)
    print("\n[5/5] Evaluating on authentic NASA C-MAPSS test set (100 test engines)...")
    df_test_raw, _ = dataset.get_labeled_test_data(clip_rul=DEFAULT_CLIP_RUL)
    df_test_features = feature_engineer.transform(df_test_raw)

    # Extract final cycle for each of the 100 test engines
    df_test_last = df_test_features.groupby("unit_number").last().reset_index()
    X_test_last = df_test_last[feature_names]
    y_test_last = df_test_last["rul"]

    test_preds = model.predict(X_test_last)
    test_rmse = float(np.sqrt(mean_squared_error(y_test_last, test_preds)))
    test_mae = float(mean_absolute_error(y_test_last, test_preds))
    test_r2 = float(r2_score(y_test_last, test_preds))
    cmapss_score = calculate_cmapss_score(y_test_last.to_numpy(), test_preds)

    print(f"\n================================================================")
    print(f" FINAL BENCHMARK RESULTS — NASA C-MAPSS FD001 TEST ENGINES (N=100) ")
    print(f"================================================================")
    print(f"  -> Test RMSE:         {test_rmse:.2f} cycles (Target: < 20.00)")
    print(f"  -> Test MAE:          {test_mae:.2f} cycles")
    print(f"  -> Test R² Score:     {test_r2:.4f}")
    print(f"  -> NASA C-MAPSS Score:{cmapss_score:.2f}")
    print(f"================================================================")

    # 7. Extract Feature Importances
    importances = pd.DataFrame({
        "feature": feature_names,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)
    
    top_15_features = importances.head(15).to_dict(orient="records")

    # 8. Serialize Artifacts
    print("\n[INFO] Serializing trained model and pipeline artifacts to ml/artifacts/...")
    
    model_path = ARTIFACTS_DIR / "rul_model.joblib"
    feature_engineer_path = ARTIFACTS_DIR / "feature_engineer.joblib"
    features_json_path = ARTIFACTS_DIR / "features.json"
    metadata_path = ARTIFACTS_DIR / "training_metadata.json"
    metrics_path = ARTIFACTS_DIR / "metrics.json"

    joblib.dump(model, model_path)
    joblib.dump(feature_engineer, feature_engineer_path)

    with open(features_json_path, "w", encoding="utf-8") as f:
        json.dump(feature_names, f, indent=2)

    metadata = {
        "dataset": "NASA C-MAPSS FD001",
        "model_type": "LightGBM Regressor (LGBMRegressor)",
        "model_params": model_params,
        "random_seed": RANDOM_SEED,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "training_duration_seconds": round(training_duration_s, 2),
        "total_train_records": len(df_raw_train),
        "total_train_units": int(df_raw_train["unit_number"].nunique()),
        "feature_count": len(feature_names),
        "top_15_features": top_15_features
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    metrics = {
        "validation": {
            "rmse": round(val_rmse, 3),
            "mae": round(val_mae, 3),
            "r2": round(val_r2, 4),
            "units": int(val_df["unit_number"].nunique()),
            "records": len(X_val)
        },
        "test_benchmark": {
            "rmse": round(test_rmse, 3),
            "mae": round(test_mae, 3),
            "r2": round(test_r2, 4),
            "cmapss_score": round(cmapss_score, 2),
            "units": int(len(y_test_last)),
            "target_rmse_met": bool(test_rmse < 20.0)
        }
    }
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print(f"[SUCCESS] Model saved to {model_path}")
    print(f"[SUCCESS] Feature pipeline saved to {feature_engineer_path}")
    print(f"[SUCCESS] Metadata and metrics saved to {metrics_path}")

    return metrics


if __name__ == "__main__":
    train_rul_model()
