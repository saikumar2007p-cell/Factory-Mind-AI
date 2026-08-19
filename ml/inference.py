"""
ml/inference.py

Production Prognostics & Anomaly Inference Service for FactoryMind AI.

Consumes real C-MAPSS observation windows, extracts features via the fitted Stage 1 pipeline,
runs LightGBM RUL regression & Isolation Forest anomaly detection,
computes deterministic Machine Health Index (0-100%), and evaluates risk levels with hysteresis.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
import joblib
import numpy as np
import pandas as pd

# Paths & Environment
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

ARTIFACTS_DIR = ROOT_DIR / "ml" / "artifacts"
SENSOR_META_PATH = ROOT_DIR / "data" / "reference" / "sensor_metadata.json"

from ml.dataset import ALL_RAW_COLS, INDEX_COLS, INFORMATIVE_SENSORS, CONSTANT_SENSORS
from ml.features import FeatureEngineer, extract_features_for_window
from backend.app.services.decision_rules import (
    RiskLevel,
    AnomalyStatus,
    compute_health_index,
    compute_risk_score,
    HysteresisRiskEngine,
    SensorSignalEvidence
)


class InferenceEngine:
    """
    Stateful and stateless production inference service for turbofan degradation prognostics.
    """

    def __init__(self, artifacts_dir: Optional[Union[str, Path]] = None):
        self.artifacts_dir = Path(artifacts_dir) if artifacts_dir else ARTIFACTS_DIR
        self._load_artifacts()
        self._load_sensor_metadata()
        self._engine_trackers: Dict[int, HysteresisRiskEngine] = {}

    def _load_artifacts(self):
        """Loads serialized Stage 1 model weights and feature pipeline."""
        required = [
            "rul_model.joblib",
            "anomaly_model.joblib",
            "feature_engineer.joblib",
            "features.json",
            "training_metadata.json",
            "anomaly_metadata.json"
        ]
        for fname in required:
            fpath = self.artifacts_dir / fname
            if not fpath.exists():
                raise FileNotFoundError(f"Required model artifact missing at {fpath}. Ensure Stage 1 has been executed.")

        self.rul_model = joblib.load(self.artifacts_dir / "rul_model.joblib")
        self.anomaly_model = joblib.load(self.artifacts_dir / "anomaly_model.joblib")
        self.feature_engineer: FeatureEngineer = joblib.load(self.artifacts_dir / "feature_engineer.joblib")
        
        with open(self.artifacts_dir / "features.json", "r", encoding="utf-8") as f:
            self.feature_names: List[str] = json.load(f)

        with open(self.artifacts_dir / "training_metadata.json", "r", encoding="utf-8") as f:
            self.training_metadata = json.load(f)

        with open(self.artifacts_dir / "anomaly_metadata.json", "r", encoding="utf-8") as f:
            self.anomaly_metadata = json.load(f)

        self.model_version = self.training_metadata.get("model_type", "LightGBM-v1.0")

    def _load_sensor_metadata(self):
        """Loads physical descriptions and subsystems for sensors."""
        if SENSOR_META_PATH.exists():
            with open(SENSOR_META_PATH, "r", encoding="utf-8") as f:
                self.sensor_metadata = json.load(f)
        else:
            self.sensor_metadata = {}

    def get_tracker(self, machine_id: int) -> HysteresisRiskEngine:
        """Retrieves or creates a stateful hysteresis filter for a specific engine."""
        if machine_id not in self._engine_trackers:
            self._engine_trackers[machine_id] = HysteresisRiskEngine()
        return self._engine_trackers[machine_id]

    def reset_tracker(self, machine_id: int):
        """Resets hysteresis tracker state for a specific engine."""
        if machine_id in self._engine_trackers:
            self._engine_trackers[machine_id].reset()

    def validate_input(self, window_df: pd.DataFrame) -> pd.DataFrame:
        """
        Validates input schema, sensor column presence, ordering, and finite values.
        """
        if not isinstance(window_df, pd.DataFrame):
            raise TypeError(f"Expected pandas DataFrame, got {type(window_df)}")

        if window_df.empty:
            raise ValueError("Input observation window cannot be empty.")

        # Check required columns
        missing_cols = [c for c in ALL_RAW_COLS if c not in window_df.columns]
        if missing_cols:
            raise ValueError(f"Input DataFrame is missing required C-MAPSS columns: {missing_cols}")

        # Check for invalid non-numeric types
        numeric_cols = [c for c in ALL_RAW_COLS if c != "unit_number"]
        for c in numeric_cols:
            if not pd.api.types.is_numeric_dtype(window_df[c]):
                raise TypeError(f"Column '{c}' contains non-numeric data.")

        # Sort and clean
        df_clean = window_df.sort_values(by=["unit_number", "time_cycle"]).copy()
        
        # Check single unit
        if df_clean["unit_number"].nunique() > 1:
            raise ValueError("Inference window must contain observations for a single unit_number.")

        # Replace any infs
        df_clean = df_clean.replace([np.inf, -np.inf], np.nan).ffill().bfill().fillna(0.0)
        return df_clean

    def calculate_anomaly_score(self, raw_decision: float) -> Tuple[float, AnomalyStatus]:
        """
        Calibrates raw Isolation Forest decision function into a normalized [0, 1] score.
        
        Decision function:
        - Median (Nominal baseline): ~0.1086 -> maps to ~0.0
        - 0.0 (Anomaly Threshold): maps to ~0.50
        - Minimum (~-0.1164): maps to 1.0
        """
        stats = self.anomaly_metadata.get("decision_function_stats", {})
        median_val = stats.get("p50_median", 0.1086)
        min_val = stats.get("min", -0.1164)
        
        spread = median_val - min_val
        if spread <= 0:
            spread = 0.20

        # Normalized distance from nominal median
        raw_norm = (median_val - raw_decision) / spread
        anomaly_score = float(np.round(np.clip(raw_norm, 0.0, 1.0), 4))
        
        # Status classification (raw_decision <= 0.0 is the formal IsolationForest threshold)
        status = AnomalyStatus.ANOMALOUS if (raw_decision <= 0.0 or anomaly_score >= 0.50) else AnomalyStatus.NORMAL
        return anomaly_score, status

    def extract_contributing_signals(
        self,
        window_df: pd.DataFrame,
        top_n: int = 5
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Computes trend direction, baseline deviations, and z-scores for informative sensors.
        Returns:
            (top_contributing_signals, all_sensor_trends)
        """
        sensor_desc = self.sensor_metadata.get("sensor_descriptions", {})
        baseline_mask = window_df["time_cycle"] <= 5
        baseline_slice = window_df[baseline_mask]
        
        signals = []
        trends = []

        for sensor_id in INFORMATIVE_SENSORS:
            series = window_df[sensor_id].to_numpy()
            current_val = float(series[-1])
            
            # Baseline mean & std
            if len(baseline_slice) > 0:
                base_mean = float(baseline_slice[sensor_id].mean())
                base_std = float(baseline_slice[sensor_id].std(ddof=0))
            else:
                base_mean = float(series[0])
                base_std = 1.0

            if base_std < 1e-4:
                base_std = 1.0

            delta = current_val - base_mean
            pct_change = (delta / base_mean * 100.0) if base_mean != 0 else 0.0
            z_score = float(delta / base_std)

            # Trend slope (last min(15, len(series)) cycles)
            recent_window = series[-min(15, len(series)):]
            if len(recent_window) >= 3:
                x = np.arange(len(recent_window))
                # Linear slope
                slope = float(np.polyfit(x, recent_window, 1)[0])
            else:
                slope = 0.0

            # Trend direction
            if slope > 0.02 * base_std:
                direction = "increasing"
            elif slope < -0.02 * base_std:
                direction = "decreasing"
            else:
                direction = "stable"

            meta = sensor_desc.get(sensor_id, {})
            name = meta.get("name", sensor_id)
            subsystem = meta.get("subsystem", "Turbofan Core")
            units = meta.get("units", "")

            signal_item = {
                "sensor_id": sensor_id,
                "name": name,
                "subsystem": subsystem,
                "units": units,
                "current_value": round(current_val, 3),
                "baseline_value": round(base_mean, 3),
                "delta": round(delta, 3),
                "percent_change": round(pct_change, 2),
                "z_score": round(z_score, 2),
                "trend_direction": direction,
                "trend_slope": round(slope, 4),
            }
            signals.append(signal_item)
            trends.append({
                "sensor_id": sensor_id,
                "name": name,
                "subsystem": subsystem,
                "trend_direction": direction,
                "slope": round(slope, 4),
                "current_value": round(current_val, 3)
            })

        # Rank contributing signals by absolute z-score (magnitude of deviation from healthy baseline)
        signals.sort(key=lambda x: abs(x["z_score"]), reverse=True)
        for rank, s in enumerate(signals, 1):
            s["importance_rank"] = rank

        return signals[:top_n], trends

    def predict_window(
        self,
        window_df: pd.DataFrame,
        apply_hysteresis: bool = True
    ) -> Dict[str, Any]:
        """
        Primary inference entrypoint.
        Processes an observation window, runs models, computes metrics, and assigns filtered risk level.
        """
        df_clean = self.validate_input(window_df)
        
        machine_id = int(df_clean["unit_number"].iloc[-1])
        cycle = int(df_clean["time_cycle"].iloc[-1])

        # 1. Feature Engineering (reusing fitted pipeline)
        df_features = self.feature_engineer.transform(df_clean)
        latest_features = df_features[self.feature_names].iloc[[-1]]

        # 2. RUL Model Prediction (LightGBM)
        raw_rul = float(self.rul_model.predict(latest_features)[0])
        # Technically justified safety bound: RUL cannot physically be negative
        predicted_rul = float(np.round(np.maximum(raw_rul, 0.0), 2))

        # 3. Anomaly Model Prediction (Isolation Forest)
        raw_decision = float(self.anomaly_model.decision_function(latest_features)[0])
        anomaly_score, anomaly_status = self.calculate_anomaly_score(raw_decision)

        # 4. Composite Machine Health Index & Risk Score
        health_index = compute_health_index(predicted_rul, anomaly_score)
        risk_score = compute_risk_score(health_index)

        # 5. Risk Level with Hysteresis & Multi-Cycle Persistence
        tracker = self.get_tracker(machine_id)
        if apply_hysteresis:
            risk_level, state_changed = tracker.update(
                cycle=cycle,
                risk_score=risk_score,
                predicted_rul=predicted_rul,
                anomaly_score=anomaly_score
            )
        else:
            risk_level = tracker.evaluate_instantaneous_level(risk_score, predicted_rul)
            state_changed = False

        # 6. Contributing Signals and Sensor Trends
        contributing_signals, trends = self.extract_contributing_signals(df_clean, top_n=5)

        # 7. Construct strongly typed structured output
        result = {
            "machine_id": machine_id,
            "cycle": cycle,
            "rul_estimate": predicted_rul,
            "anomaly_score": anomaly_score,
            "anomaly_status": anomaly_status.value,
            "health_index": health_index,
            "risk_score": risk_score,
            "risk_level": risk_level.value,
            "state_changed": state_changed,
            "raw_decision_function": round(raw_decision, 4),
            "contributing_signals": contributing_signals,
            "trends": trends,
            "model_version": self.model_version,
            "features_used_count": len(self.feature_names),
            "window_size": len(df_clean)
        }

        return result


# Module-level singleton instance for convenient imports
_inference_engine_instance: Optional[InferenceEngine] = None


def get_inference_engine() -> InferenceEngine:
    """Returns singleton InferenceEngine instance."""
    global _inference_engine_instance
    if _inference_engine_instance is None:
        _inference_engine_instance = InferenceEngine()
    return _inference_engine_instance
