"""
ml/features.py

Feature Engineering Module for NASA C-MAPSS FD001 Turbofan Telemetry.

Extracts time-series domain features preserving engine trajectories without future data leakage:
- Backward-looking rolling statistics (mean, std, min, max, range) over windows [5, 10, 20]
- Baseline delta: deviation from early engine baseline (mean of initial 5 cycles)
- Lag delta: rate of change over recent operational cycles
- Sensor ratios and degradation interactions
- Reusable for both full-trajectory batch training and streaming inference
"""

from typing import List, Optional, Tuple, Dict, Any
import numpy as np
import pandas as pd

from ml.dataset import (
    INFORMATIVE_SENSORS,
    SETTING_COLS,
    INDEX_COLS,
    CONSTANT_SENSORS
)

DEFAULT_ROLLING_WINDOWS = [5, 10, 20]
BASELINE_CYCLES = 5


class FeatureEngineer:
    """
    Time-series feature extraction engine for C-MAPSS sensor data.
    Ensures zero future leakage and backward-only window aggregation.
    """

    def __init__(
        self,
        sensors_to_use: Optional[List[str]] = None,
        rolling_windows: Optional[List[int]] = None,
        baseline_cycles: int = BASELINE_CYCLES,
        include_settings: bool = True
    ):
        self.sensors = sensors_to_use if sensors_to_use is not None else INFORMATIVE_SENSORS
        self.rolling_windows = rolling_windows if rolling_windows is not None else DEFAULT_ROLLING_WINDOWS
        self.baseline_cycles = baseline_cycles
        self.include_settings = include_settings
        self.feature_names_: List[str] = []

    def fit(self, df: pd.DataFrame) -> "FeatureEngineer":
        """
        Fits feature engineer by deriving and storing the feature column schema.
        """
        # Run transform on a small sample to lock feature column names
        sample = df.head(50).copy()
        transformed = self._extract_features(sample)
        self.feature_names_ = [
            c for c in transformed.columns 
            if c not in INDEX_COLS + ["rul", "rul_raw", "max_cycle", "final_rul"]
        ]
        return self

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extracts engineered features from a DataFrame containing one or more engine trajectories.
        """
        return self._extract_features(df)

    def fit_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fits and transforms in a single call.
        """
        self.fit(df)
        return self.transform(df)

    def get_feature_names(self) -> List[str]:
        """Returns the list of engineered feature names."""
        if not self.feature_names_:
            raise ValueError("FeatureEngineer is not fitted yet.")
        return self.feature_names_

    def _extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Core feature computation per engine trajectory (grouped by unit_number).
        """
        df_out = df.copy()

        # Ensure sorted by unit and cycle
        df_out = df_out.sort_values(by=["unit_number", "time_cycle"]).reset_index(drop=True)

        feature_dfs = []

        # Process each engine unit independently to guarantee zero cross-engine leakage
        for unit_id, unit_group in df_out.groupby("unit_number", sort=False):
            unit_features = self._extract_unit_features(unit_group)
            feature_dfs.append(unit_features)

        result = pd.concat(feature_dfs, axis=0).reset_index(drop=True)
        return result

    def _extract_unit_features(self, unit_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates rolling statistics and deltas strictly looking backward within a single engine unit.
        """
        df_unit = unit_df.copy()
        new_cols: Dict[str, np.ndarray] = {}

        # 1. Baseline calculation: Mean of initial baseline_cycles (nominal healthy state)
        baseline_mask = df_unit["time_cycle"] <= self.baseline_cycles
        baseline_df = df_unit[baseline_mask]
        
        # If fewer cycles than baseline_cycles exist, use available cycles
        if len(baseline_df) == 0:
            baseline_means = df_unit[self.sensors].iloc[0]
        else:
            baseline_means = baseline_df[self.sensors].mean()

        for s in self.sensors:
            s_series = df_unit[s]

            # Sensor baseline delta: deviation from healthy baseline
            new_cols[f"{s}_baseline_delta"] = (s_series - baseline_means[s]).to_numpy()

            # 2. Rolling window features (mean, std, min, max, range, lag delta)
            for w in self.rolling_windows:
                # Backward rolling window with min_periods=1 to handle trajectory starts
                r = s_series.rolling(window=w, min_periods=1)
                
                r_mean = r.mean().to_numpy()
                r_std = r.std(ddof=0).fillna(0.0).to_numpy()
                r_min = r.min().to_numpy()
                r_max = r.max().to_numpy()
                r_range = r_max - r_min

                new_cols[f"{s}_roll_mean_{w}"] = r_mean
                new_cols[f"{s}_roll_std_{w}"] = r_std
                new_cols[f"{s}_roll_min_{w}"] = r_min
                new_cols[f"{s}_roll_max_{w}"] = r_max
                new_cols[f"{s}_roll_range_{w}"] = r_range

            # 3. Lag diff (change over 5 cycles)
            lag_5 = s_series.shift(5)
            # Backward fill for initial 5 cycles
            lag_diff_5 = (s_series - lag_5).fillna(0.0).to_numpy()
            new_cols[f"{s}_lag_diff_5"] = lag_diff_5

            # 4. Short-term slope estimation (linear rate over last 10 cycles)
            lag_10 = s_series.shift(10)
            lag_diff_10 = (s_series - lag_10).fillna(0.0).to_numpy()
            new_cols[f"{s}_rate_10"] = lag_diff_10 / 10.0

        # Construct DataFrame from newly engineered columns
        engineered_df = pd.DataFrame(new_cols, index=df_unit.index)

        # Combine with original metadata and sensors
        combined = pd.concat([df_unit, engineered_df], axis=1)

        # Replace any remaining NaNs or Infs with 0.0
        combined = combined.replace([np.inf, -np.inf], np.nan).fillna(0.0)

        return combined


def extract_features_for_window(
    window_df: pd.DataFrame,
    feature_engineer: FeatureEngineer
) -> pd.DataFrame:
    """
    Convenience function for real-time inference on a sliding buffer window of an engine.
    Accepts arbitrary cycle window (e.g., past 20-50 cycles), computes features,
    and returns the features corresponding to the latest cycle.
    """
    features_df = feature_engineer.transform(window_df)
    # Return the latest cycle observation
    return features_df.iloc[[-1]].copy()
