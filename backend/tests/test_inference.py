"""
backend/tests/test_inference.py

Comprehensive test suite for Stage 2 Inference Engine & Decision Layer.
Validates real C-MAPSS FD001 inference, schema validation, RUL & Anomaly calculations,
health index, risk levels, hysteresis, and persistence filtering.
"""

import pytest
import numpy as np
import pandas as pd
from pathlib import Path

from ml.dataset import CMAPSSDataset, ALL_RAW_COLS, INFORMATIVE_SENSORS
from ml.inference import InferenceEngine, get_inference_engine
from backend.app.services.decision_rules import (
    RiskLevel,
    AnomalyStatus,
    HysteresisRiskEngine,
    RiskThresholds,
    compute_health_index,
    compute_risk_score
)


@pytest.fixture
def engine():
    return InferenceEngine()


@pytest.fixture
def dataset():
    return CMAPSSDataset()


@pytest.fixture
def unit_1_trajectory(dataset):
    df = dataset.load_raw_train()
    return df[df["unit_number"] == 1].copy().sort_values("time_cycle").reset_index(drop=True)


def test_artifact_loading(engine):
    """Verify InferenceEngine properly loads all Stage 1 artifacts."""
    assert engine.rul_model is not None
    assert engine.anomaly_model is not None
    assert engine.feature_engineer is not None
    assert len(engine.feature_names) == 276
    assert "LightGBM" in engine.model_version or "LGBM" in engine.model_version


def test_valid_real_inference_early_cycle(engine, unit_1_trajectory):
    """Test inference on early healthy operational cycles (Cycle 20)."""
    window = unit_1_trajectory.iloc[:20].copy()
    engine.reset_tracker(1)
    result = engine.predict_window(window)

    assert result["machine_id"] == 1
    assert result["cycle"] == 20
    assert result["rul_estimate"] > 90.0, f"Expected high RUL for early cycle, got {result['rul_estimate']}"
    assert 0.0 <= result["anomaly_score"] <= 1.0
    assert result["anomaly_status"] in ["NORMAL", "ANOMALOUS"]
    assert 0.0 <= result["health_index"] <= 100.0
    assert result["health_index"] >= 70.0, f"Expected healthy engine HI > 70%, got {result['health_index']}"
    assert 0.0 <= result["risk_score"] <= 100.0
    assert result["risk_level"] == "NORMAL"
    assert len(result["contributing_signals"]) == 5
    assert len(result["trends"]) == len(INFORMATIVE_SENSORS)


def test_valid_real_inference_late_cycle(engine, unit_1_trajectory):
    """Test inference on degraded operational cycles near end-of-life (Cycle 180+)."""
    # Unit 1 lasts 192 cycles
    window = unit_1_trajectory.iloc[:190].copy()
    engine.reset_tracker(1)
    
    # Simulate sequential updates so hysteresis catches up
    for c in range(150, 191, 5):
        w = unit_1_trajectory.iloc[:c].copy()
        result = engine.predict_window(w)

    assert result["machine_id"] == 1
    assert result["cycle"] == 190
    assert result["rul_estimate"] < 25.0, f"Expected low RUL near EOL, got {result['rul_estimate']}"
    assert result["health_index"] < 40.0, f"Expected low HI near EOL, got {result['health_index']}"
    assert result["risk_level"] in ["WARNING", "CRITICAL"]


def test_deterministic_repeated_inference(engine, unit_1_trajectory):
    """Ensure identical inputs yield identical outputs (reproducibility)."""
    window = unit_1_trajectory.iloc[:50].copy()
    
    engine.reset_tracker(1)
    res1 = engine.predict_window(window, apply_hysteresis=False)
    
    engine.reset_tracker(1)
    res2 = engine.predict_window(window, apply_hysteresis=False)

    assert res1["rul_estimate"] == res2["rul_estimate"]
    assert res1["anomaly_score"] == res2["anomaly_score"]
    assert res1["health_index"] == res2["health_index"]
    assert res1["risk_score"] == res2["risk_score"]
    assert res1["contributing_signals"] == res2["contributing_signals"]


def test_missing_sensor_column_handling(engine, unit_1_trajectory):
    """Verify input validation rejects DataFrames with missing sensor columns."""
    corrupted_window = unit_1_trajectory.iloc[:20].drop(columns=["s_11"]).copy()
    with pytest.raises(ValueError, match="missing required C-MAPSS columns"):
        engine.predict_window(corrupted_window)


def test_invalid_data_types_handling(engine, unit_1_trajectory):
    """Verify input validation rejects non-numeric or non-DataFrame inputs."""
    with pytest.raises(TypeError, match="Expected pandas DataFrame"):
        engine.predict_window([1, 2, 3])

    bad_df = unit_1_trajectory.iloc[:20].copy()
    bad_df["s_2"] = "invalid_string"
    with pytest.raises(TypeError, match="contains non-numeric data"):
        engine.predict_window(bad_df)


def test_no_nan_or_inf_in_inference_output(engine, unit_1_trajectory):
    """Verify that no NaN or Infinity exists anywhere in the returned dictionary."""
    window = unit_1_trajectory.iloc[:40].copy()
    result = engine.predict_window(window)

    for k, v in result.items():
        if isinstance(v, (int, float)):
            assert not np.isnan(v), f"Key {k} has NaN value"
            assert not np.isinf(v), f"Key {k} has Inf value"

    for signal in result["contributing_signals"]:
        for sk, sv in signal.items():
            if isinstance(sv, (int, float)):
                assert not np.isnan(sv), f"Signal key {sk} has NaN"
                assert not np.isinf(sv), f"Signal key {sk} has Inf"


def test_health_index_and_risk_score_formulas():
    """Verify health index and risk score mathematical bounds and consistency."""
    hi_100 = compute_health_index(predicted_rul=125.0, anomaly_score=0.0)
    assert hi_100 == 100.0
    assert compute_risk_score(hi_100) == 0.0

    hi_0 = compute_health_index(predicted_rul=0.0, anomaly_score=1.0)
    assert hi_0 == 0.0
    assert compute_risk_score(hi_0) == 100.0

    # Intermediate value
    hi_mid = compute_health_index(predicted_rul=62.5, anomaly_score=0.5)
    assert 45.0 <= hi_mid <= 55.0
    assert compute_risk_score(hi_mid) + hi_mid == 100.0


def test_hysteresis_and_persistence_behavior():
    """
    Test that isolated single-cycle spikes do not cause alert flapping,
    and sustained changes require the required persistence cycles.
    """
    tracker = HysteresisRiskEngine()
    assert tracker.current_state == RiskLevel.NORMAL

    # 1. Single noisy spike to WARNING (risk_score = 65, enter_warning = 60)
    state, changed = tracker.update(cycle=1, risk_score=65.0, predicted_rul=50.0, anomaly_score=0.2)
    # Escalation requires 2 cycles -> should remain NORMAL on cycle 1
    assert state == RiskLevel.NORMAL
    assert not changed

    # 2. Return to normal immediately (cycle 2: risk_score = 15)
    state, changed = tracker.update(cycle=2, risk_score=15.0, predicted_rul=100.0, anomaly_score=0.05)
    assert state == RiskLevel.NORMAL
    assert not changed

    # 3. Persistent escalation to MONITOR (enter_monitor = 30)
    state, changed = tracker.update(cycle=3, risk_score=35.0, predicted_rul=80.0, anomaly_score=0.1)
    assert state == RiskLevel.NORMAL  # Cycle 1 of MONITOR
    assert not changed

    state, changed = tracker.update(cycle=4, risk_score=36.0, predicted_rul=79.0, anomaly_score=0.1)
    assert state == RiskLevel.MONITOR  # Cycle 2 of MONITOR -> Transits!
    assert changed

    # 4. Flapping around exit threshold (exit_monitor = 24.0)
    # Cycle 5 drops to 23.0 (below exit threshold)
    state, changed = tracker.update(cycle=5, risk_score=23.0, predicted_rul=85.0, anomaly_score=0.08)
    # De-escalation requires 3 consecutive cycles -> stays MONITOR
    assert state == RiskLevel.MONITOR
    assert not changed

    # Cycle 6 bounces back to 28.0 (above exit threshold)
    state, changed = tracker.update(cycle=6, risk_score=28.0, predicted_rul=84.0, anomaly_score=0.09)
    assert state == RiskLevel.MONITOR
    assert not changed


def test_critical_safety_override():
    """Verify that very low RUL (<= 12 cycles) immediately triggers CRITICAL without delay."""
    tracker = HysteresisRiskEngine()
    state, changed = tracker.update(cycle=100, risk_score=85.0, predicted_rul=8.0, anomaly_score=0.7)
    assert state == RiskLevel.CRITICAL
    assert changed
