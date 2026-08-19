"""
backend/app/services/ml_compatibility.py

ML Feature Schema Compatibility Evaluator for FactoryMind AI.

Strict Rule: The production LightGBM RUL regressor and Isolation Forest anomaly detector
require 21 canonical sensor channels from NASA C-MAPSS FD001.
If an external industrial telemetry stream does not supply the complete 21/21 required feature set,
the system explicitly refuses to fabricate fake predictions and reports:
"RUL prediction unavailable — required sensor features are missing."

The system MUST NOT:
- invent missing sensors
- copy old values into missing sensors
- interpolate fake values
- generate fake RUL
- generate fake anomaly scores
"""

from typing import Dict, List, Optional, Tuple, Any
import logging

from backend.app.schemas.normalized_telemetry import (
    NormalizedTelemetryFrame,
    MLCompatibilityReport,
    MLCompatibilityStatus
)
from backend.app.services.sensor_mapping import CANONICAL_SENSOR_DEFINITIONS

logger = logging.getLogger("factorymind.compatibility")

REQUIRED_CANONICAL_SENSORS = [f"s_{i}" for i in range(1, 22)]


class MLCompatibilityService:
    """
    Validates telemetry schema compatibility against trained prognostic ML models.
    """

    def evaluate_frame_compatibility(
        self,
        frame: NormalizedTelemetryFrame
    ) -> MLCompatibilityReport:
        """
        Evaluates whether a NormalizedTelemetryFrame has all 21 required sensor features
        to execute the C-MAPSS prognostic pipeline.
        """
        available_ids = set()
        
        for reading in frame.readings.values():
            if reading.sensor_id in CANONICAL_SENSOR_DEFINITIONS:
                available_ids.add(reading.sensor_id)
            else:
                # Check by canonical name match
                for s_id, defn in CANONICAL_SENSOR_DEFINITIONS.items():
                    if defn["name"].lower() == reading.canonical_name.lower():
                        available_ids.add(s_id)
                        break

        missing = [s for s in REQUIRED_CANONICAL_SENSORS if s not in available_ids]
        avail_count = len(available_ids)

        if avail_count == 21:
            status = MLCompatibilityStatus.COMPATIBLE
            is_predictable = True
            is_anomaly = True
            message = "ML Compatibility: 21/21 required channels available. Full prognostic model ready."
        elif avail_count > 0:
            status = MLCompatibilityStatus.INCOMPATIBLE
            is_predictable = False
            is_anomaly = False
            missing_names = [f"{CANONICAL_SENSOR_DEFINITIONS[s]['name']} ({s})" for s in missing[:6]]
            more_str = f" and {len(missing) - 6} more" if len(missing) > 6 else ""
            message = (
                f"ML Compatibility: INCOMPATIBLE ({avail_count}/21 required channels available). "
                f"RUL prediction unavailable — required sensor features are missing ({', '.join(missing_names)}{more_str})."
            )
        else:
            status = MLCompatibilityStatus.INSUFFICIENT_DATA
            is_predictable = False
            is_anomaly = False
            message = "Insufficient Data: No compatible turbofan prognostic sensor channels identified in payload. RUL prediction unavailable."

        return MLCompatibilityReport(
            machine_id=frame.machine_id,
            status=status,
            total_required_channels=21,
            available_compatible_channels=avail_count,
            missing_channels=missing,
            is_rul_predictable=is_predictable,
            is_anomaly_detectable=is_anomaly,
            message=message
        )

    def convert_frame_to_model_row(
        self,
        frame: NormalizedTelemetryFrame
    ) -> Optional[Dict[str, float]]:
        """
        Converts a strictly 21/21 compatible NormalizedTelemetryFrame into a canonical dictionary
        matching the format expected by the ML inference engine.
        Returns None if frame is incomplete/incompatible — NEVER fabricates missing sensors.
        """
        report = self.evaluate_frame_compatibility(frame)
        if not report.is_rul_predictable:
            return None

        # Base unit & cycle
        try:
            unit_num = int(frame.machine_id)
        except ValueError:
            unit_num = 1

        cycle = frame.cycle if frame.cycle is not None else 1

        row: Dict[str, float] = {
            "unit_number": float(unit_num),
            "time_cycle": float(cycle),
            "setting_1": float(frame.operating_settings.get("setting_1", 0.0)),
            "setting_2": float(frame.operating_settings.get("setting_2", 0.0)),
            "setting_3": float(frame.operating_settings.get("setting_3", 100.0)),
        }

        # Populate sensor readings strictly from provided readings
        sensor_map: Dict[str, float] = {}
        for r in frame.readings.values():
            if r.sensor_id in CANONICAL_SENSOR_DEFINITIONS:
                sensor_map[r.sensor_id] = float(r.value)
            else:
                for s_id, defn in CANONICAL_SENSOR_DEFINITIONS.items():
                    if defn["name"].lower() == r.canonical_name.lower():
                        sensor_map[s_id] = float(r.value)
                        break

        # Strictly check that all 21 sensors are present
        for i in range(1, 22):
            s_key = f"s_{i}"
            if s_key in sensor_map:
                row[s_key] = sensor_map[s_key]
            else:
                # Do NOT invent or interpolate
                return None

        return row


# Singleton instance
_ml_compatibility_service: Optional[MLCompatibilityService] = None


def get_ml_compatibility_service() -> MLCompatibilityService:
    global _ml_compatibility_service
    if _ml_compatibility_service is None:
        _ml_compatibility_service = MLCompatibilityService()
    return _ml_compatibility_service
