"""
ml/dataset.py

NASA C-MAPSS FD001 Dataset Loading, Validation, RUL Labeling, and Trajectory Preservation Module.

Provides:
- Strict schema parsing for raw 26-column NASA C-MAPSS text files.
- Piece-wise linear Remaining Useful Life (RUL) target calculation.
- Test set ground truth alignment with RUL_FD001.txt.
- Trajectory-preserving train/validation splits (by engine unit ID).
- Sensor categorization (informative vs constant sensors).
- Zero data leakage between units.
"""

from pathlib import Path
from typing import Tuple, List, Dict, Optional, Union
import numpy as np
import pandas as pd

# Paths
MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Column definitions
INDEX_COLS = ["unit_number", "time_cycle"]
SETTING_COLS = ["setting_1", "setting_2", "setting_3"]
SENSOR_COLS = [f"s_{i}" for i in range(1, 22)]
ALL_RAW_COLS = INDEX_COLS + SETTING_COLS + SENSOR_COLS

# Sensors with non-zero variance in FD001 (informative for HPC degradation)
INFORMATIVE_SENSORS = [
    "s_2", "s_3", "s_4", "s_7", "s_8", "s_9", 
    "s_11", "s_12", "s_13", "s_14", "s_15", "s_17", "s_20", "s_21"
]

# Sensors with zero/near-zero variance in FD001 (constant baseline)
CONSTANT_SENSORS = [
    "s_1", "s_5", "s_6", "s_10", "s_16", "s_18", "s_19"
]

DEFAULT_CLIP_RUL = 125  # Standard piece-wise linear RUL threshold for turbofan engines


class CMAPSSDataset:
    """
    Handler for NASA C-MAPSS FD001 Turbofan dataset.
    """

    def __init__(self, raw_data_dir: Optional[Union[str, Path]] = None):
        self.raw_data_dir = Path(raw_data_dir) if raw_data_dir else DEFAULT_RAW_DIR
        self.train_file = self.raw_data_dir / "train_FD001.txt"
        self.test_file = self.raw_data_dir / "test_FD001.txt"
        self.rul_file = self.raw_data_dir / "RUL_FD001.txt"

    def verify_files_exist(self) -> bool:
        """Checks if all required raw dataset files exist."""
        for f in [self.train_file, self.test_file, self.rul_file]:
            if not f.exists():
                return False
        return True

    def load_raw_train(self) -> pd.DataFrame:
        """
        Loads raw train_FD001.txt without transformations.
        Expected shape: 20,631 rows x 26 columns.
        """
        if not self.train_file.exists():
            raise FileNotFoundError(f"Training dataset not found at {self.train_file}. Please run scripts/download_dataset.py first.")
        
        df = pd.read_csv(self.train_file, sep=r"\s+", header=None, names=ALL_RAW_COLS)
        self._validate_schema(df, expected_min_rows=20000, expected_units=100)
        return df

    def load_raw_test(self) -> pd.DataFrame:
        """
        Loads raw test_FD001.txt without transformations.
        Expected shape: 13,096 rows x 26 columns.
        """
        if not self.test_file.exists():
            raise FileNotFoundError(f"Test dataset not found at {self.test_file}. Please run scripts/download_dataset.py first.")
        
        df = pd.read_csv(self.test_file, sep=r"\s+", header=None, names=ALL_RAW_COLS)
        self._validate_schema(df, expected_min_rows=13000, expected_units=100)
        return df

    def load_ground_truth_rul(self) -> pd.Series:
        """
        Loads ground truth RUL for test engines from RUL_FD001.txt.
        Expected length: 100 scalars (1 per engine unit).
        """
        if not self.rul_file.exists():
            raise FileNotFoundError(f"RUL ground truth file not found at {self.rul_file}.")
        
        df_rul = pd.read_csv(self.rul_file, sep=r"\s+", header=None, names=["rul"])
        if len(df_rul) != 100:
            raise ValueError(f"Expected 100 RUL ground truth values, got {len(df_rul)}")
        return df_rul["rul"]

    @staticmethod
    def _validate_schema(df: pd.DataFrame, expected_min_rows: int, expected_units: int):
        """Strict validation of dataset dimensions, missing values, and column integrity."""
        if len(df.columns) != len(ALL_RAW_COLS):
            raise ValueError(f"Schema mismatch: expected {len(ALL_RAW_COLS)} columns, got {len(df.columns)}")
        
        if len(df) < expected_min_rows:
            raise ValueError(f"Row count below expected: got {len(df)}, expected at least {expected_min_rows}")
        
        unique_units = df["unit_number"].nunique()
        if unique_units != expected_units:
            raise ValueError(f"Engine unit count mismatch: got {unique_units}, expected {expected_units}")
        
        if df.isna().sum().sum() > 0:
            raise ValueError("Dataset contains unexpected NaN/null values.")

    def get_labeled_train_data(self, clip_rul: Optional[int] = DEFAULT_CLIP_RUL) -> pd.DataFrame:
        """
        Loads training data and computes exact Remaining Useful Life (RUL) target per cycle.
        
        RUL calculation:
        1. Max cycle $T_i$ for each unit $i$.
        2. Raw RUL = $T_i$ - current cycle.
        3. If clip_rul is set, piece-wise linear RUL = min(Raw RUL, clip_rul).
        """
        df = self.load_raw_train()
        
        # Calculate max cycle per unit
        max_cycle_per_unit = df.groupby("unit_number")["time_cycle"].max().reset_index()
        max_cycle_per_unit.columns = ["unit_number", "max_cycle"]
        
        df = df.merge(max_cycle_per_unit, on="unit_number", how="left")
        df["rul_raw"] = df["max_cycle"] - df["time_cycle"]
        
        if clip_rul is not None and clip_rul > 0:
            df["rul"] = df["rul_raw"].clip(upper=clip_rul)
        else:
            df["rul"] = df["rul_raw"]
            
        return df

    def get_labeled_test_data(self, clip_rul: Optional[int] = DEFAULT_CLIP_RUL) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Loads test data and computes ground truth RUL for every cycle in test set.
        
        Returns:
            df_test_all: Full test telemetry with ground truth RUL for every observed cycle.
            df_test_last: The latest cycle for each test unit (commonly used for RUL benchmark evaluation).
        """
        df_test = self.load_raw_test()
        rul_truth = self.load_ground_truth_rul()
        
        # rul_truth index is 0..99, corresponding to unit_numbers 1..100
        rul_df = pd.DataFrame({
            "unit_number": np.arange(1, 101),
            "final_rul": rul_truth.values
        })
        
        # Max cycle in test per unit
        max_cycle_test = df_test.groupby("unit_number")["time_cycle"].max().reset_index()
        max_cycle_test.columns = ["unit_number", "max_cycle"]
        
        df_test = df_test.merge(max_cycle_test, on="unit_number", how="left")
        df_test = df_test.merge(rul_df, on="unit_number", how="left")
        
        # In test set, RUL at cycle t = final_rul + (max_cycle - t)
        df_test["rul_raw"] = df_test["final_rul"] + (df_test["max_cycle"] - df_test["time_cycle"])
        
        if clip_rul is not None and clip_rul > 0:
            df_test["rul"] = df_test["rul_raw"].clip(upper=clip_rul)
        else:
            df_test["rul"] = df_test["rul_raw"]
            
        # Extract latest cycle slice for benchmark evaluation
        df_test_last = df_test.groupby("unit_number").last().reset_index()
        
        return df_test, df_test_last

    def split_train_val_trajectories(
        self,
        df: pd.DataFrame,
        val_fraction: float = 0.2,
        random_state: int = 42
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Splits data into train and validation sets by UNIT IDs (trajectories).
        Ensures NO engine trajectories are split across train and validation sets,
        preventing data leakage and optimistic bias.
        """
        units = df["unit_number"].unique()
        rng = np.random.RandomState(random_state)
        shuffled_units = rng.permutation(units)
        
        val_count = int(len(units) * val_fraction)
        val_units = set(shuffled_units[:val_count])
        train_units = set(shuffled_units[val_count:])
        
        df_train = df[df["unit_number"].isin(train_units)].copy().reset_index(drop=True)
        df_val = df[df["unit_number"].isin(val_units)].copy().reset_index(drop=True)
        
        return df_train, df_val

    def get_unit_trajectory(self, unit_id: int, is_test: bool = False) -> pd.DataFrame:
        """
        Retrieves the complete time-series trajectory of a specific engine unit.
        """
        if is_test:
            df, _ = self.get_labeled_test_data()
        else:
            df = self.get_labeled_train_data()
            
        unit_df = df[df["unit_number"] == unit_id].copy().sort_values("time_cycle").reset_index(drop=True)
        if unit_df.empty:
            raise ValueError(f"Unit ID {unit_id} not found in dataset.")
        return unit_df
