"""
ml/evaluate.py

Evaluation Suite for FactoryMind AI Prognostic and Anomaly Detection Models.
Evaluates model artifacts on authentic NASA C-MAPSS FD001 test engines.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

ARTIFACTS_DIR = ROOT_DIR / "ml" / "artifacts"

from ml.dataset import CMAPSSDataset, DEFAULT_CLIP_RUL
from ml.train_rul import calculate_cmapss_score


def evaluate_models() -> Dict[str, Any]:
    print("================================================================")
    print(" FactoryMind AI — Comprehensive Model Evaluation & Verification ")
    print("================================================================")

    # 1. Load artifacts
    rul_model_path = ARTIFACTS_DIR / "rul_model.joblib"
    anomaly_model_path = ARTIFACTS_DIR / "anomaly_model.joblib"
    feature_eng_path = ARTIFACTS_DIR / "feature_engineer.joblib"
    features_json_path = ARTIFACTS_DIR / "features.json"

    for p in [rul_model_path, anomaly_model_path, feature_eng_path, features_json_path]:
        if not p.exists():
            raise FileNotFoundError(f"Missing required artifact at {p}. Please train models first.")

    rul_model = joblib.load(rul_model_path)
    anomaly_model = joblib.load(anomaly_model_path)
    feature_engineer = joblib.load(feature_eng_path)
    with open(features_json_path, "r", encoding="utf-8") as f:
        feature_names = json.load(f)

    # 2. Load test dataset
    dataset = CMAPSSDataset()
    df_test_raw, df_test_last_raw = dataset.get_labeled_test_data(clip_rul=DEFAULT_CLIP_RUL)
    df_test_features = feature_engineer.transform(df_test_raw)
    
    # 3. RUL Evaluation on Benchmark Slice (last cycle of each test engine)
    df_test_last = df_test_features.groupby("unit_number").last().reset_index()
    X_test_last = df_test_last[feature_names]
    y_test_last = df_test_last["rul"]

    y_pred_rul = rul_model.predict(X_test_last)
    test_rmse = float(np.sqrt(mean_squared_error(y_test_last, y_pred_rul)))
    test_mae = float(mean_absolute_error(y_test_last, y_pred_rul))
    test_r2 = float(r2_score(y_test_last, y_pred_rul))
    cmapss_score = calculate_cmapss_score(y_test_last.to_numpy(), y_pred_rul)

    # 4. Anomaly Evaluation across all test cycles
    X_test_all = df_test_features[feature_names]
    anomaly_decisions = anomaly_model.decision_function(X_test_all)
    anomaly_preds = anomaly_model.predict(X_test_all)  # -1 = anomaly, 1 = normal

    anomaly_count = int(np.sum(anomaly_preds == -1))
    total_test_cycles = len(anomaly_preds)
    anomaly_pct = float(anomaly_count / total_test_cycles * 100)

    # Evaluation summary
    report = {
        "rul_evaluation": {
            "test_engines": int(len(y_test_last)),
            "rmse": round(test_rmse, 3),
            "mae": round(test_mae, 3),
            "r2": round(test_r2, 4),
            "cmapss_score": round(cmapss_score, 2),
            "target_rmse_met": bool(test_rmse < 20.0),
        },
        "anomaly_evaluation": {
            "total_test_cycles": total_test_cycles,
            "anomalous_cycles": anomaly_count,
            "anomaly_percentage": round(anomaly_pct, 2),
            "decision_min": round(float(np.min(anomaly_decisions)), 4),
            "decision_max": round(float(np.max(anomaly_decisions)), 4),
            "decision_median": round(float(np.median(anomaly_decisions)), 4)
        }
    }

    print("\n--- RUL MODEL PERFORMANCE (100 C-MAPSS TEST ENGINES) ---")
    print(f"  • RMSE:          {report['rul_evaluation']['rmse']} cycles")
    print(f"  • MAE:           {report['rul_evaluation']['mae']} cycles")
    print(f"  • R² Score:      {report['rul_evaluation']['r2']}")
    print(f"  • C-MAPSS Score: {report['rul_evaluation']['cmapss_score']}")
    print(f"  • Target (<20):  {'MET (PASS)' if report['rul_evaluation']['target_rmse_met'] else 'FAIL'}")

    print("\n--- ANOMALY DETECTOR PERFORMANCE (13,096 TEST CYCLES) ---")
    print(f"  • Total Cycles Evaluated: {report['anomaly_evaluation']['total_test_cycles']:,}")
    print(f"  • Anomalies Detected:     {report['anomaly_evaluation']['anomalous_cycles']:,} ({report['anomaly_evaluation']['anomaly_percentage']}%)")
    print(f"  • Decision Range:         [{report['anomaly_evaluation']['decision_min']}, {report['anomaly_evaluation']['decision_max']}]")
    print("================================================================\n")

    return report


if __name__ == "__main__":
    evaluate_models()
