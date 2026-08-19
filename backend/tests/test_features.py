"""
backend/tests/test_features.py

Tests for Stage 1 Feature Engineering module:
- Backward-only rolling aggregations
- Strict verification of NO future data leakage
- NaN / Inf handling
- Sliding window inference compatibility
"""

import pytest
import numpy as np
import pandas as pd

from ml.dataset import CMAPSSDataset, INFORMATIVE_SENSORS
from ml.features import FeatureEngineer, extract_features_for_window


@pytest.fixture
def sample_trajectory():
    dataset = CMAPSSDataset()
    df_train = dataset.load_raw_train()
    # Return trajectory of engine 1
    return df_train[df_train["unit_number"] == 1].copy().reset_index(drop=True)


def test_feature_engineering_dimensions_and_nans(sample_trajectory):
    """Verify feature engineering produces non-empty output with zero NaNs."""
    feat_eng = FeatureEngineer()
    df_feat = feat_eng.fit_transform(sample_trajectory)
    feature_names = feat_eng.get_feature_names()

    assert len(feature_names) > 50, f"Expected >50 features, got {len(feature_names)}"
    assert len(df_feat) == len(sample_trajectory)
    assert df_feat[feature_names].isna().sum().sum() == 0, "Engineered features contain NaNs"
    assert not np.isinf(df_feat[feature_names].values).any(), "Engineered features contain Infs"


def test_no_future_leakage(sample_trajectory):
    """
    CRITICAL TEST: Ensure feature calculations at cycle T do NOT depend on any future cycles (T+1, T+2, ...).
    Transforming a trajectory up to cycle 50 must yield IDENTICAL features for cycles 1..50
    as transforming the entire 192-cycle trajectory.
    """
    feat_eng = FeatureEngineer()
    feat_eng.fit(sample_trajectory)

    # 1. Transform entire trajectory
    full_transformed = feat_eng.transform(sample_trajectory)
    features_at_50_from_full = full_transformed[full_transformed["time_cycle"] == 50][feat_eng.get_feature_names()].to_numpy()

    # 2. Transform truncated trajectory (only cycles 1..50)
    truncated_trajectory = sample_trajectory[sample_trajectory["time_cycle"] <= 50].copy()
    truncated_transformed = feat_eng.transform(truncated_trajectory)
    features_at_50_from_trunc = truncated_transformed[truncated_transformed["time_cycle"] == 50][feat_eng.get_feature_names()].to_numpy()

    # 3. Mutated future trajectory (corrupt all cycles after 50)
    corrupted_trajectory = sample_trajectory.copy()
    future_mask = corrupted_trajectory["time_cycle"] > 50
    for s in INFORMATIVE_SENSORS:
        corrupted_trajectory.loc[future_mask, s] = corrupted_trajectory.loc[future_mask, s] * 999.0 + 5000.0
    
    corrupted_transformed = feat_eng.transform(corrupted_trajectory)
    features_at_50_from_corrupted = corrupted_transformed[corrupted_transformed["time_cycle"] == 50][feat_eng.get_feature_names()].to_numpy()

    # All three must match exactly within numerical tolerance
    np.testing.assert_allclose(
        features_at_50_from_full,
        features_at_50_from_trunc,
        rtol=1e-5,
        atol=1e-5,
        err_msg="Future data leakage detected between full and truncated trajectories!"
    )

    np.testing.assert_allclose(
        features_at_50_from_full,
        features_at_50_from_corrupted,
        rtol=1e-5,
        atol=1e-5,
        err_msg="Future data leakage detected when future observations were corrupted!"
    )


def test_sliding_window_inference(sample_trajectory):
    """Ensure extract_features_for_window generates valid single-cycle feature vectors for live streaming."""
    feat_eng = FeatureEngineer()
    feat_eng.fit(sample_trajectory)

    window_30 = sample_trajectory.iloc[:30].copy()
    single_obs_features = extract_features_for_window(window_30, feat_eng)

    assert len(single_obs_features) == 1
    assert single_obs_features["time_cycle"].iloc[0] == 30
    assert single_obs_features[feat_eng.get_feature_names()].isna().sum().sum() == 0
