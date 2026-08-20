"""
backend/app/services/ml_compatibility.py

ML Feature Schema Compatibility Evaluator for FactoryMind AI.

Two evaluation paths:
  1. C-MAPSS strict (21/21) — for simulation and NASA dataset sources.
     Returns COMPATIBLE / INCOMPATIBLE / INSUFFICIENT_DATA.
  2. Customer / external tiered — for industrial real-world data.
     Returns capability tier: FULL_RUL | PARTIAL_RUL | ANOMALY_ONLY | BASELINE_ONLY | INSUFFICIENT

The system MUST NOT:
  - invent missing sensors
  - copy old values into missing sensors
  - interpolate fake values
  - generate fake RUL or fake anomaly scores
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

# Feature importance tiers for tiered customer evaluation.
# Critical features are the most informative for RUL prediction;
# supplemental features improve accuracy but are not strictly required.
FEATURE_TIERS = {
    "critical": ["s_2", "s_3", "s_4", "s_7", "s_8", "s_11", "s_12", "s_15", "s_20", "s_21"],
    "supporting": ["s_9", "s_13", "s_14", "s_17"],
    "supplemental": ["s_1", "s_5", "s_6", "s_10", "s_16", "s_18", "s_19"],
}


class MLCompatibilityService:
    """
    Validates telemetry schema compatibility against trained prognostic ML models.
    """

    # -------------------------------------------------------------------------
    # PATH 1: C-MAPSS STRICT (21/21) — unchanged from original
    # -------------------------------------------------------------------------

    def evaluate_frame_compatibility(
        self,
        frame: NormalizedTelemetryFrame
    ) -> MLCompatibilityReport:
        """
        Evaluates whether a NormalizedTelemetryFrame has all 21 required sensor features
        to execute the C-MAPSS prognostic pipeline.
        Use for C-MAPSS simulation / NASA dataset sources only.
        """
        available_ids = set()

        for reading in frame.readings.values():
            if reading.sensor_id in CANONICAL_SENSOR_DEFINITIONS:
                available_ids.add(reading.sensor_id)
            else:
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
            capability = "FULL_RUL"
            message = "ML Compatibility: 21/21 required channels available. Full prognostic model ready."
        elif avail_count > 0:
            status = MLCompatibilityStatus.INCOMPATIBLE
            is_predictable = False
            is_anomaly = False
            capability = "ANOMALY_ONLY"
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
            capability = "INSUFFICIENT"
            message = "Insufficient Data: No compatible turbofan prognostic sensor channels identified in payload."

        return MLCompatibilityReport(
            machine_id=frame.machine_id,
            status=status,
            total_required_channels=21,
            available_compatible_channels=avail_count,
            missing_channels=missing,
            is_rul_predictable=is_predictable,
            is_anomaly_detectable=is_anomaly,
            capability_tier=capability,
            coverage_score=round(avail_count / 21, 3),
            message=message
        )

    # -------------------------------------------------------------------------
    # PATH 2: CUSTOMER / EXTERNAL TIERED EVALUATION
    # -------------------------------------------------------------------------

    def evaluate_customer_frame_compatibility(
        self,
        machine_id: str,
        available_sensor_ids: List[str],
        available_sensor_names: Optional[List[str]] = None
    ) -> MLCompatibilityReport:
        """
        Tiered capability assessment for industrial / external data sources.
        Does NOT require all 21 C-MAPSS channels.

        Scoring:
          - Coverage score = weighted fraction of feature tiers present
          - critical weight = 0.60, supporting = 0.30, supplemental = 0.10
          - FULL_RUL:     coverage >= 0.80 AND all critical present
          - PARTIAL_RUL:  coverage >= 0.50 AND ≥6 critical present
          - ANOMALY_ONLY: coverage >= 0.25 AND ≥3 critical present
          - BASELINE_ONLY: coverage >= 0.10
          - INSUFFICIENT: coverage < 0.10

        Args:
            machine_id: Machine identifier (string)
            available_sensor_ids: List of canonical sensor IDs present (e.g. ['s_2', 's_4'])
            available_sensor_names: Optional list of canonical names for matching
        """
        available_set = set(available_sensor_ids)

        # Also match by canonical name if sensor_ids mapping is imperfect
        if available_sensor_names:
            for name in available_sensor_names:
                for s_id, defn in CANONICAL_SENSOR_DEFINITIONS.items():
                    if defn["name"].lower() == name.lower():
                        available_set.add(s_id)

        critical_available = [s for s in FEATURE_TIERS["critical"] if s in available_set]
        supporting_available = [s for s in FEATURE_TIERS["supporting"] if s in available_set]
        supplemental_available = [s for s in FEATURE_TIERS["supplemental"] if s in available_set]

        n_critical_total = len(FEATURE_TIERS["critical"])
        n_supporting_total = len(FEATURE_TIERS["supporting"])
        n_supplemental_total = len(FEATURE_TIERS["supplemental"])

        # Weighted coverage score
        critical_fraction = len(critical_available) / n_critical_total if n_critical_total else 0
        supporting_fraction = len(supporting_available) / n_supporting_total if n_supporting_total else 0
        supplemental_fraction = len(supplemental_available) / n_supplemental_total if n_supplemental_total else 0

        coverage_score = (
            0.60 * critical_fraction +
            0.30 * supporting_fraction +
            0.10 * supplemental_fraction
        )
        coverage_score = round(coverage_score, 3)

        n_critical = len(critical_available)

        # Determine capability tier
        if coverage_score >= 0.80 and n_critical >= n_critical_total:
            capability = "FULL_RUL"
            status = MLCompatibilityStatus.FULL_RUL
            is_rul = True
            is_anomaly = True
            message = (
                f"Full RUL capability: {len(available_set)}/{21} C-MAPSS channels matched "
                f"(coverage={coverage_score:.2f}). Complete prognostic pipeline available."
            )
        elif coverage_score >= 0.50 and n_critical >= 6:
            capability = "PARTIAL_RUL"
            status = MLCompatibilityStatus.PARTIAL_RUL
            is_rul = True
            is_anomaly = True
            message = (
                f"Partial RUL capability: {n_critical}/{n_critical_total} critical features present "
                f"(coverage={coverage_score:.2f}). RUL prediction available with reduced accuracy. "
                "Confidence will be reported as MEDIUM or LOW."
            )
        elif coverage_score >= 0.15 or n_critical >= 3:
            capability = "ANOMALY_ONLY"
            status = MLCompatibilityStatus.ANOMALY_ONLY
            is_rul = False
            is_anomaly = True
            message = (
                f"Anomaly detection only: insufficient critical features for RUL "
                f"({n_critical}/{n_critical_total} critical, coverage={coverage_score:.2f}). "
                "RUL estimate will not be produced."
            )

        elif coverage_score >= 0.10:
            capability = "BASELINE_ONLY"
            status = MLCompatibilityStatus.BASELINE_ONLY
            is_rul = False
            is_anomaly = False
            message = (
                f"Baseline characterisation only: very few matched features "
                f"(coverage={coverage_score:.2f}). "
                "Only normal-behaviour baseline can be established — no anomaly scoring."
            )
        else:
            capability = "INSUFFICIENT"
            status = MLCompatibilityStatus.INSUFFICIENT_DATA
            is_rul = False
            is_anomaly = False
            message = (
                f"Insufficient sensor coverage (score={coverage_score:.2f}). "
                "No ML capability available for this sensor set. "
                "Review sensor mappings and data source configuration."
            )

        all_matched = sorted(list(available_set))
        missing = [s for s in REQUIRED_CANONICAL_SENSORS if s not in available_set]

        logger.info(
            f"Customer ML compatibility for machine {machine_id}: "
            f"tier={capability}, coverage={coverage_score:.3f}, "
            f"critical={n_critical}/{n_critical_total}"
        )

        return MLCompatibilityReport(
            machine_id=str(machine_id),
            status=status,
            total_required_channels=21,
            available_compatible_channels=len(all_matched),
            missing_channels=missing,
            is_rul_predictable=is_rul,
            is_anomaly_detectable=is_anomaly,
            capability_tier=capability,
            coverage_score=coverage_score,
            message=message
        )

    # -------------------------------------------------------------------------
    # CONVERSION HELPER (C-MAPSS only)
    # -------------------------------------------------------------------------

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

        sensor_map: Dict[str, float] = {}
        for r in frame.readings.values():
            if r.sensor_id in CANONICAL_SENSOR_DEFINITIONS:
                sensor_map[r.sensor_id] = float(r.value)
            else:
                for s_id, defn in CANONICAL_SENSOR_DEFINITIONS.items():
                    if defn["name"].lower() == r.canonical_name.lower():
                        sensor_map[s_id] = float(r.value)
                        break

        for i in range(1, 22):
            s_key = f"s_{i}"
            if s_key in sensor_map:
                row[s_key] = sensor_map[s_key]
            else:
                return None

        return row


# Singleton instance
_ml_compatibility_service: Optional[MLCompatibilityService] = None


def get_ml_compatibility_service() -> MLCompatibilityService:
    global _ml_compatibility_service
    if _ml_compatibility_service is None:
        _ml_compatibility_service = MLCompatibilityService()
    return _ml_compatibility_service
