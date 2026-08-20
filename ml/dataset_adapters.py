"""
ml/dataset_adapters.py

Dataset-specific adapters for FactoryMind AI multi-machine platform.
Each adapter knows how to load, validate, and normalize its specific dataset format.

Adapters:
  1. CMAPSSAdapter — NASA C-MAPSS FD001 (Turbofan, RUL)
  2. PHM2009GearboxAdapter — PHM 2009 (Gearbox, Fault Detection)
  3. PHMAP2023ValveAdapter — PHMAP 2023 (Valve/Pressure, Anomaly Detection)

Zero Fabrication: If data doesn't exist, return Unavailable. Never invent readings.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import numpy as np
import pandas as pd

logger = logging.getLogger("factorymind.dataset_adapters")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"


class BaseDatasetAdapter(ABC):
    """Base class for all dataset adapters."""

    dataset_id: str = ""
    equipment_type: str = ""
    machine_type: str = ""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if raw dataset files exist locally."""
        pass

    @abstractmethod
    def load_data(self) -> Optional[pd.DataFrame]:
        """Load and return the dataset as a DataFrame. Returns None if unavailable."""
        pass

    @abstractmethod
    def get_sensors(self) -> List[Dict[str, str]]:
        """Return list of actual sensors with name, unit, description."""
        pass

    @abstractmethod
    def get_supported_tasks(self) -> List[str]:
        """Return list of ML tasks this dataset supports."""
        pass

    @abstractmethod
    def get_machine_count(self) -> int:
        """Return number of distinct machines/units in dataset."""
        pass

    def get_status(self) -> Dict[str, Any]:
        """Return dataset availability status."""
        available = self.is_available()
        return {
            "datasetId": self.dataset_id,
            "equipmentType": self.equipment_type,
            "machineType": self.machine_type,
            "available": available,
            "status": "READY" if available else "NOT_DOWNLOADED",
            "sensors": self.get_sensors() if available else [],
            "supportedTasks": self.get_supported_tasks(),
            "machineCount": self.get_machine_count() if available else 0,
        }


class CMAPSSAdapter(BaseDatasetAdapter):
    """Adapter for NASA C-MAPSS FD001 Turbofan Engine dataset."""

    dataset_id = "NASA_CMAPSS_FD001"
    equipment_type = "TURBOFAN_ENGINE"
    machine_type = "Engine"

    RAW_DIR = DATA_DIR / "raw"
    TRAIN_FILE = RAW_DIR / "train_FD001.txt"
    TEST_FILE = RAW_DIR / "test_FD001.txt"
    RUL_FILE = RAW_DIR / "RUL_FD001.txt"

    INDEX_COLS = ["unit_number", "time_cycle"]
    SETTING_COLS = ["setting_1", "setting_2", "setting_3"]
    SENSOR_COLS = [f"s_{i}" for i in range(1, 22)]
    ALL_COLS = INDEX_COLS + SETTING_COLS + SENSOR_COLS

    INFORMATIVE_SENSORS = [
        "s_2", "s_3", "s_4", "s_7", "s_8", "s_9",
        "s_11", "s_12", "s_13", "s_14", "s_15", "s_17", "s_20", "s_21"
    ]

    def is_available(self) -> bool:
        return self.TRAIN_FILE.exists() and self.TEST_FILE.exists()

    def load_data(self) -> Optional[pd.DataFrame]:
        if not self.is_available():
            logger.warning(f"[{self.dataset_id}] Raw files not found at {self.RAW_DIR}")
            return None
        try:
            df = pd.read_csv(self.TRAIN_FILE, sep=r"\s+", header=None, names=self.ALL_COLS)
            df["datasetId"] = self.dataset_id
            df["equipmentType"] = self.equipment_type
            df["dataSource"] = "NASA_CMAPSS_FD001"
            df["dataMode"] = "DEMO"
            return df
        except Exception as e:
            logger.error(f"[{self.dataset_id}] Load failed: {e}")
            return None

    def get_sensors(self) -> List[Dict[str, str]]:
        return [
            {"id": "s_2", "name": "T24 - LPC Outlet Temp", "unit": "°R", "type": "temperature"},
            {"id": "s_3", "name": "T30 - HPC Outlet Temp", "unit": "°R", "type": "temperature"},
            {"id": "s_4", "name": "T50 - LPT Outlet Temp", "unit": "°R", "type": "temperature"},
            {"id": "s_7", "name": "Ps30 - HPC Outlet Pressure", "unit": "psia", "type": "pressure"},
            {"id": "s_8", "name": "phi - Fuel Flow Ratio", "unit": "ratio", "type": "flow"},
            {"id": "s_9", "name": "NRf - Physical Fan Speed", "unit": "rpm", "type": "speed"},
            {"id": "s_11", "name": "NRc - Physical Core Speed", "unit": "rpm", "type": "speed"},
            {"id": "s_12", "name": "BPR - Bypass Ratio", "unit": "ratio", "type": "ratio"},
            {"id": "s_13", "name": "farB - Burner Fuel-Air Ratio", "unit": "ratio", "type": "ratio"},
            {"id": "s_14", "name": "htBleed - Bleed Enthalpy", "unit": "BTU/s", "type": "energy"},
            {"id": "s_15", "name": "Nf_dmd - Demanded Fan Speed", "unit": "rpm", "type": "speed"},
            {"id": "s_17", "name": "W32 - HPT Coolant Bleed", "unit": "lb/s", "type": "flow"},
            {"id": "s_20", "name": "BPR Corrected", "unit": "ratio", "type": "ratio"},
            {"id": "s_21", "name": "W31 - HPT Coolant Corrected", "unit": "lb/s", "type": "flow"},
        ]

    def get_supported_tasks(self) -> List[str]:
        return ["RUL_PREDICTION", "DEGRADATION_ANALYSIS", "ANOMALY_DETECTION", "CONDITION_MONITORING"]

    def get_machine_count(self) -> int:
        if not self.is_available():
            return 0
        try:
            df = pd.read_csv(self.TRAIN_FILE, sep=r"\s+", header=None, usecols=[0])
            return int(df[0].nunique())
        except Exception:
            return 100  # Known value for FD001


class PHM2009GearboxAdapter(BaseDatasetAdapter):
    """
    Adapter for PHM 2009 Data Challenge — Industrial Gearbox.
    Source: https://www.phmsociety.org/competition/phm/09
    Also available on Kaggle.

    Data format: CSV with columns [input_voltage, output_voltage, tachometer]
    Operating conditions: 30-50 Hz shaft speed, high/low load
    """

    dataset_id = "PHM_2009_GEARBOX"
    equipment_type = "INDUSTRIAL_GEARBOX"
    machine_type = "Gearbox"

    RAW_DIR = DATA_DIR / "raw" / "phm2009_gearbox"

    def is_available(self) -> bool:
        if not self.RAW_DIR.exists():
            return False
        csv_files = list(self.RAW_DIR.glob("*.csv"))
        return len(csv_files) > 0

    def load_data(self) -> Optional[pd.DataFrame]:
        if not self.is_available():
            logger.info(
                f"[{self.dataset_id}] Dataset not yet downloaded. "
                f"Download from: https://www.phmsociety.org/competition/phm/09 "
                f"or Kaggle, then place CSV files in: {self.RAW_DIR}"
            )
            return None
        try:
            frames = []
            for csv_file in sorted(self.RAW_DIR.glob("*.csv")):
                df = pd.read_csv(csv_file)
                df["source_file"] = csv_file.stem
                frames.append(df)
            if not frames:
                return None
            combined = pd.concat(frames, ignore_index=True)
            combined["datasetId"] = self.dataset_id
            combined["equipmentType"] = self.equipment_type
            combined["dataSource"] = "PHM_2009"
            combined["dataMode"] = "DEMO"
            return combined
        except Exception as e:
            logger.error(f"[{self.dataset_id}] Load failed: {e}")
            return None

    def get_sensors(self) -> List[Dict[str, str]]:
        return [
            {"id": "input_voltage", "name": "Input Shaft Accelerometer", "unit": "V", "type": "vibration"},
            {"id": "output_voltage", "name": "Output Shaft Accelerometer", "unit": "V", "type": "vibration"},
            {"id": "tachometer", "name": "Tachometer Pulses", "unit": "pulses", "type": "speed"},
        ]

    def get_supported_tasks(self) -> List[str]:
        return ["FAULT_DETECTION", "FAULT_CLASSIFICATION", "VIBRATION_ANALYSIS", "CONDITION_MONITORING"]

    def get_machine_count(self) -> int:
        if not self.is_available():
            return 0
        try:
            csv_files = list(self.RAW_DIR.glob("*.csv"))
            return len(csv_files)
        except Exception:
            return 0


class PHMAP2023ValveAdapter(BaseDatasetAdapter):
    """
    Adapter for PHMAP 2023 Data Challenge — Valve/Pressure System.
    Source: https://phmap.jp/2023/data-challenge/
    Spacecraft propulsion system pressure data at 1 kHz.
    """

    dataset_id = "PHMAP_2023_VALVE"
    equipment_type = "VALVE_PRESSURE_SYSTEM"
    machine_type = "Valve"

    RAW_DIR = DATA_DIR / "raw" / "phmap2023_valve"

    def is_available(self) -> bool:
        if not self.RAW_DIR.exists():
            return False
        data_files = list(self.RAW_DIR.glob("*.csv")) + list(self.RAW_DIR.glob("*.npy"))
        return len(data_files) > 0

    def load_data(self) -> Optional[pd.DataFrame]:
        if not self.is_available():
            logger.info(
                f"[{self.dataset_id}] Dataset not yet downloaded. "
                f"Download from: https://phmap.jp/2023/data-challenge/ "
                f"then place data files in: {self.RAW_DIR}"
            )
            return None
        try:
            frames = []
            for csv_file in sorted(self.RAW_DIR.glob("*.csv")):
                df = pd.read_csv(csv_file)
                df["source_file"] = csv_file.stem
                frames.append(df)
            if not frames:
                return None
            combined = pd.concat(frames, ignore_index=True)
            combined["datasetId"] = self.dataset_id
            combined["equipmentType"] = self.equipment_type
            combined["dataSource"] = "PHMAP_2023"
            combined["dataMode"] = "DEMO"
            return combined
        except Exception as e:
            logger.error(f"[{self.dataset_id}] Load failed: {e}")
            return None

    def get_sensors(self) -> List[Dict[str, str]]:
        return [
            {"id": "pressure_upstream", "name": "Upstream Pressure", "unit": "kPa", "type": "pressure"},
            {"id": "pressure_downstream", "name": "Downstream Pressure", "unit": "kPa", "type": "pressure"},
            {"id": "valve_command", "name": "Valve Command Signal", "unit": "binary", "type": "control"},
        ]

    def get_supported_tasks(self) -> List[str]:
        return ["ANOMALY_DETECTION", "FAULT_DETECTION", "FAULT_LOCALIZATION", "PRESSURE_ANALYSIS"]

    def get_machine_count(self) -> int:
        if not self.is_available():
            return 0
        try:
            data_files = list(self.RAW_DIR.glob("*.csv"))
            return max(len(data_files), 1)
        except Exception:
            return 0


# ============================================================================
# ADAPTER REGISTRY — Central access to all dataset adapters
# ============================================================================

ADAPTER_REGISTRY: Dict[str, BaseDatasetAdapter] = {
    "NASA_CMAPSS_FD001": CMAPSSAdapter(),
    "PHM_2009_GEARBOX": PHM2009GearboxAdapter(),
    "PHMAP_2023_VALVE": PHMAP2023ValveAdapter(),
}


def get_adapter(dataset_id: str) -> Optional[BaseDatasetAdapter]:
    """Get the adapter for a specific dataset."""
    return ADAPTER_REGISTRY.get(dataset_id)


def get_all_adapter_statuses() -> List[Dict[str, Any]]:
    """Return status of all registered dataset adapters."""
    return [adapter.get_status() for adapter in ADAPTER_REGISTRY.values()]
