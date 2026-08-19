"""
backend/tests/test_models.py

Tests for Stage 1 Model Training & Artifacts:
- Model artifact files existence
- Deserialization and inference compatibility
- RUL prediction sanity (non-negative, realistic ranges)
- Anomaly detector decision function and scoring bounds
"""

import json
from pathlib import Path
import pytest
import joblib
import numpy as np
import pandas as pd

from ml.dataset import CMAPSSDataset, DEFAULT_CLIP_RUL

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ARTIFACTS_DIR = ROOT_DIR / "ml" / "artifacts"


def test_model_artifacts_exist():
    """Ensure all required Stage 1 artifacts were generated and saved."""
    required_files = [
        ARTIFACTS_DIR / "rul_model.joblib",
        ARTIFACTS_DIR / "anomaly_model.joblib",
        ARTIFACTS_DIR / "feature_engineer.joblib",
        ARTIFACTS_DIR / "features.json",
        ARTIFACTS_DIR / "training_metadata.json",
        ARTIFACTS_DIR / "metrics.json",
    ]
    for rf in required_files:
        assert rf.exists(), f"Missing required artifact: {rf}"


def test_rul_model_inference():
    """Verify RUL model produces valid prognostic outputs."""
    rul_model = joblib.load(ARTIFACTS_DIR / "rul_model.joblib")
    feature_engineer = joblib.load(ARTIFACTS_DIR / "feature_engineer.joblib")
    with open(ARTIFACTS_DIR / "features.json", "r", encoding="utf-8") as f:
        feature_names = json.load(f)

    dataset = CMAPSSDataset()
    df_test_raw, _ = dataset.get_labeled_test_data()
    df_features = feature_engineer.transform(df_test_raw.head(100))

    X = df_features[feature_names]
    preds = rul_model.predict(X)

    assert len(preds) == 100
    assert not np.isnan(preds).any(), "RUL predictions contain NaN"
    assert (preds >= 0).all(), "RUL predictions cannot be negative"
    assert (preds <= 160).all(), "RUL predictions unreasonably high"


def test_anomaly_model_inference():
    """Verify anomaly detector produces valid decision function outputs."""
    anomaly_model = joblib.load(ARTIFACTS_DIR / "anomaly_model.joblib")
    feature_engineer = joblib.load(ARTIFACTS_DIR / "feature_engineer.joblib")
    with open(ARTIFACTS_DIR / "features.json", "r", encoding="utf-8") as f:
        feature_names = json.load(f)

    dataset = CMAPSSDataset()
    df_test_raw, _ = dataset.get_labeled_test_data()
    df_features = feature_engineer.transform(df_test_raw.head(100))

    X = df_features[feature_names]
    decisions = anomaly_model.decision_function(X)
    preds = anomaly_model.predict(X)

    assert len(decisions) == 100
    assert len(preds) == 100
    assert not np.isnan(decisions).any()
    assert set(np.unique(preds)).issubset({-1, 1})
