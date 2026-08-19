"""
backend/tests/test_dataset.py

Comprehensive test suite for Stage 0 — NASA C-MAPSS FD001 dataset pipeline.
Validates file integrity, column schemas, RUL calculation, trajectory preservation, and absence of data leakage.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from ml.dataset import (
    CMAPSSDataset,
    ALL_RAW_COLS,
    INDEX_COLS,
    SETTING_COLS,
    SENSOR_COLS,
    INFORMATIVE_SENSORS,
    CONSTANT_SENSORS,
    DEFAULT_CLIP_RUL
)


@pytest.fixture
def dataset():
    return CMAPSSDataset()


def test_raw_files_exist(dataset):
    """Ensure all required raw C-MAPSS FD001 files exist on disk."""
    assert dataset.verify_files_exist(), "Raw NASA C-MAPSS FD001 files missing from data/raw/."


def test_raw_train_schema_and_shape(dataset):
    """Validate training dataset row count, column structure, and unit counts."""
    df_train = dataset.load_raw_train()
    
    assert isinstance(df_train, pd.DataFrame)
    assert df_train.shape == (20631, 26), f"Expected shape (20631, 26), got {df_train.shape}"
    assert list(df_train.columns) == ALL_RAW_COLS
    assert df_train["unit_number"].nunique() == 100
    assert set(df_train["unit_number"].unique()) == set(range(1, 101))
    assert df_train.isna().sum().sum() == 0, "Training set contains null values"


def test_raw_test_schema_and_shape(dataset):
    """Validate test dataset row count, column structure, and unit counts."""
    df_test = dataset.load_raw_test()
    
    assert isinstance(df_test, pd.DataFrame)
    assert df_test.shape == (13096, 26), f"Expected shape (13096, 26), got {df_test.shape}"
    assert list(df_test.columns) == ALL_RAW_COLS
    assert df_test["unit_number"].nunique() == 100
    assert set(df_test["unit_number"].unique()) == set(range(1, 101))
    assert df_test.isna().sum().sum() == 0, "Test set contains null values"


def test_ground_truth_rul(dataset):
    """Validate ground truth RUL vector for test engines."""
    rul_truth = dataset.load_ground_truth_rul()
    
    assert len(rul_truth) == 100, f"Expected 100 RUL ground truth values, got {len(rul_truth)}"
    assert (rul_truth >= 0).all(), "Ground truth RUL must be non-negative"
    assert (rul_truth < 200).all(), "Unreasonably high RUL in ground truth"


def test_rul_labeling_logic(dataset):
    """Verify that RUL decreases by 1 per cycle and hits 0 at the last cycle of each unit."""
    df_labeled = dataset.get_labeled_train_data(clip_rul=None)
    
    # Check for unit 1
    unit_1 = df_labeled[df_labeled["unit_number"] == 1].sort_values("time_cycle")
    max_cycle_1 = unit_1["time_cycle"].max()
    
    assert unit_1.iloc[0]["rul_raw"] == max_cycle_1 - 1
    assert unit_1.iloc[-1]["rul_raw"] == 0
    
    # Ensure raw RUL decreases monotonically by exactly 1 per step
    diffs = unit_1["rul_raw"].diff().dropna()
    assert (diffs == -1).all(), "RUL must decrease by exactly 1 per cycle"


def test_piecewise_rul_clipping(dataset):
    """Verify piece-wise linear RUL clipping for health degradation modeling."""
    clip_val = 125
    df_clipped = dataset.get_labeled_train_data(clip_rul=clip_val)
    
    assert (df_clipped["rul"] <= clip_val).all(), f"Clipped RUL exceeded {clip_val}"
    assert df_clipped["rul"].min() == 0, "Minimum RUL must be 0 at end of life"


def test_trajectory_preservation_in_train_val_split(dataset):
    """Verify train/validation split is performed by engine unit ID, preserving entire trajectories with zero overlap."""
    df_train = dataset.get_labeled_train_data()
    train_split, val_split = dataset.split_train_val_trajectories(df_train, val_fraction=0.2, random_state=42)
    
    train_units = set(train_split["unit_number"].unique())
    val_units = set(val_split["unit_number"].unique())
    
    assert len(train_units.intersection(val_units)) == 0, "Data leakage detected: unit overlap between train and val splits!"
    assert len(train_units) == 80
    assert len(val_units) == 20
    assert len(train_split) + len(val_split) == len(df_train)


def test_sensor_variance_and_categories(dataset):
    """Verify that informative sensors exhibit variance while constant sensors have zero variance in FD001."""
    df_train = dataset.load_raw_train()
    
    for s in INFORMATIVE_SENSORS:
        var = df_train[s].var()
        assert var > 1e-4, f"Informative sensor {s} unexpectedly has near-zero variance: {var}"
        
    for s in CONSTANT_SENSORS:
        var = df_train[s].var()
        assert var < 1e-3, f"Constant sensor {s} unexpectedly has significant variance: {var}"
