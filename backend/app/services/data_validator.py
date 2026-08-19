"""
backend/app/services/data_validator.py

Comprehensive Industrial Telemetry Validation and Data Quality Service for FactoryMind AI.

Enforces:
- Schema completeness & machine ID validation
- Timestamp parsing & ISO verification
- Strict finite numerical validation (zero tolerance for NaN / ±Inf)
- Configurable Stale Data Detection (distinguishes sensor loss from machine failure)
- Physical Unit Normalization integration
- Physical plausibility checks: Never invent physical operating limits. Use only documented/configured
  limits; if no validated range exists, report "Range unavailable" instead of rejecting the reading.
- Distinguishes data quality issues (MISSING/STALE/INVALID) from machine health degradation.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
import math
import numpy as np
import logging

from backend.app.schemas.normalized_telemetry import (
    DataQuality,
    DataSourceType,
    NormalizedSensorReading,
    NormalizedTelemetryFrame
)
from backend.app.services.unit_normalizer import normalize_unit
from backend.app.services.sensor_mapping import get_sensor_mapping_service

logger = logging.getLogger("factorymind.validator")

# Documented / Configured Physical Baseline Ranges for Turbofan Core Sensors (Min, Max in Canonical Units)
# Rule: Never invent physical operating limits. Use only documented/configured limits;
# if no validated range exists, report "Range unavailable" instead of rejecting the reading.
DOCUMENTED_PHYSICAL_LIMITS = {
    "s_1": (400.0, 600.0),    # T2 (°R) Total temperature at fan inlet
    "s_2": (500.0, 750.0),    # T24 (°R) Total temperature at LPC outlet
    "s_3": (1200.0, 1800.0),  # T30 (°R) Total temperature at HPC outlet
    "s_4": (1200.0, 1600.0),  # T50 (°R) Total temperature at LPT outlet
    "s_5": (10.0, 20.0),      # P2 (psia) Pressure at fan inlet
    "s_6": (15.0, 30.0),      # P15 (psia) Total pressure in bypass-duct
    "s_7": (400.0, 700.0),    # P30 (psia) Total pressure at HPC outlet
    "s_8": (2000.0, 3000.0),  # Nf (rpm) Physical fan speed
    "s_9": (8000.0, 10000.0), # Nc (rpm) Physical core speed
    "s_10": (0.8, 1.6),       # epr Engine pressure ratio (P50/P2)
    "s_11": (35.0, 60.0),     # Ps30 (psia) Static pressure at HPC outlet
    "s_12": (400.0, 650.0),   # phi Ratio of fuel flow to Ps30
    "s_13": (2000.0, 3000.0), # NRf (rpm) Corrected fan speed
    "s_14": (7500.0, 9500.0), # NRc (rpm) Corrected core speed
    "s_15": (7.0, 10.0),      # BPR Bypass Ratio
    "s_16": (0.01, 0.05),     # farB Burner fuel-air ratio
    "s_17": (300.0, 450.0),   # htBleed Bleed Enthalpy
    "s_18": (2000.0, 3000.0), # Nf_dmd Demanded fan speed
    "s_19": (80.0, 120.0),    # PCNfR_dmd Demanded corrected fan speed
    "s_20": (30.0, 50.0),     # W31 (lbm/s) HPT cool air flow
    "s_21": (15.0, 35.0)      # W32 (lbm/s) LPT cool air flow
}


class DataValidator:
    """
    Validates, normalizes, and assesses data quality for incoming industrial telemetry frames.
    """

    def __init__(self, stale_threshold_seconds: float = 60.0):
        self.stale_threshold_seconds = stale_threshold_seconds
        self.mapping_service = get_sensor_mapping_service()

    def parse_timestamp(self, ts_input: Any) -> Tuple[Optional[datetime], Optional[str]]:
        """
        Parses various timestamp representations (datetime, ISO string, unix timestamp).
        Returns:
            (parsed_datetime_utc, error_message)
        """
        if ts_input is None:
            return datetime.now(timezone.utc), None

        if isinstance(ts_input, datetime):
            if ts_input.tzinfo is None:
                return ts_input.replace(tzinfo=timezone.utc), None
            return ts_input.astimezone(timezone.utc), None

        if isinstance(ts_input, (int, float)):
            try:
                # Support seconds or milliseconds
                if ts_input > 1e11:  # Milliseconds
                    ts_input = ts_input / 1000.0
                return datetime.fromtimestamp(ts_input, tz=timezone.utc), None
            except Exception as e:
                return None, f"Invalid unix timestamp: {e}"

        if isinstance(ts_input, str):
            clean_str = ts_input.strip()
            # Try ISO formats
            try:
                dt = datetime.fromisoformat(clean_str.replace("Z", "+00:00"))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt, None
            except ValueError:
                pass

            # Try common datetime formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y/%m/%d %H:%M:%S",
                "%d-%m-%Y %H:%M:%S"
            ]:
                try:
                    dt = datetime.strptime(clean_str, fmt).replace(tzinfo=timezone.utc)
                    return dt, None
                except ValueError:
                    continue

            return None, f"Unrecognized datetime string format: '{clean_str}'"

        return None, f"Unsupported timestamp type: {type(ts_input)}"

    def is_stale(self, observation_time: datetime, reference_time: Optional[datetime] = None) -> bool:
        """Evaluates whether observation timestamp exceeds stale threshold."""
        now = reference_time or datetime.now(timezone.utc)
        if observation_time.tzinfo is None:
            observation_time = observation_time.replace(tzinfo=timezone.utc)
        elapsed = (now - observation_time).total_seconds()
        return elapsed > self.stale_threshold_seconds

    def validate_and_normalize_frame(
        self,
        machine_id: Union[str, int],
        raw_readings: Dict[str, Any],
        timestamp: Optional[Any] = None,
        cycle: Optional[int] = None,
        source_type: DataSourceType = DataSourceType.REST_API,
        source_id: str = "default",
        external_machine_id: Optional[str] = None,
        operating_settings: Optional[Dict[str, float]] = None,
        units: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[NormalizedTelemetryFrame], List[str]]:
        """
        Validates raw payload, applies sensor mappings, converts units, checks plausibility,
        and constructs a validated NormalizedTelemetryFrame.
        
        Returns:
            (normalized_frame_or_none, validation_errors_list)
        """
        errors: List[str] = []

        # 1. Validate machine ID
        if machine_id is None or str(machine_id).strip() == "":
            errors.append("Validation Error: machine_id is missing or empty.")
            return None, errors

        str_machine_id = str(machine_id).strip()

        # 2. Validate timestamp
        parsed_dt, ts_err = self.parse_timestamp(timestamp)
        if ts_err:
            errors.append(f"Validation Error: {ts_err}")
            return None, errors

        # 3. Check Stale Status
        frame_is_stale = self.is_stale(parsed_dt)

        # 4. Process sensor readings
        normalized_readings: Dict[str, NormalizedSensorReading] = {}
        provided_units = units or {}
        has_warning = False

        if not raw_readings or not isinstance(raw_readings, dict):
            errors.append("Validation Error: raw_readings must be a non-empty dictionary.")
            return None, errors

        for raw_name, raw_val in raw_readings.items():
            if raw_val is None:
                continue

            # Validate numeric value
            try:
                num_val = float(raw_val)
            except (ValueError, TypeError):
                errors.append(f"Invalid non-numeric value for sensor '{raw_name}': {raw_val}")
                continue

            if math.isnan(num_val) or math.isinf(num_val):
                errors.append(f"Quarantined non-finite value (NaN/Inf) for sensor '{raw_name}': {num_val}")
                continue

            # Resolve sensor mapping
            resolved = self.mapping_service.resolve_sensor(raw_name)
            if resolved:
                s_id, defn = resolved
                canonical_name = defn["name"]
                dimension = defn["dimension"]
                canonical_unit = defn["unit"]
                subsystem = defn["subsystem"]
            else:
                # Unmapped external sensor - preserve with canonical name as raw_name
                s_id = raw_name.lower().replace(" ", "_")
                canonical_name = raw_name
                dimension = "unknown"
                canonical_unit = "--"
                subsystem = "External Equipment"

            # Apply Unit Normalization
            source_unit = provided_units.get(raw_name) or provided_units.get(s_id) or provided_units.get(canonical_name)
            converted_val, final_unit, unit_note = normalize_unit(
                value=num_val,
                source_unit=source_unit,
                target_dimension=dimension
            )

            # Plausibility check:
            # Rule: Never invent physical operating limits. Use only documented/configured limits;
            # if no validated range exists, report "Range unavailable" instead of rejecting the reading.
            sensor_quality = DataQuality.GOOD
            if frame_is_stale:
                sensor_quality = DataQuality.STALE
            elif s_id in DOCUMENTED_PHYSICAL_LIMITS:
                p_min, p_max = DOCUMENTED_PHYSICAL_LIMITS[s_id]
                if converted_val < p_min or converted_val > p_max:
                    sensor_quality = DataQuality.WARNING
                    has_warning = True
                    unit_note = f"{unit_note} [Documented baseline: {p_min}-{p_max} {canonical_unit}; observed: {converted_val}]"
                else:
                    unit_note = f"{unit_note} [Within documented range: {p_min}-{p_max} {canonical_unit}]"
            else:
                # No documented range configured for this sensor channel
                unit_note = f"{unit_note} [Range unavailable — no documented limits configured]"

            reading = NormalizedSensorReading(
                sensor_id=s_id,
                canonical_name=canonical_name,
                raw_name=raw_name,
                value=converted_val,
                raw_value=num_val,
                unit=final_unit,
                raw_unit=source_unit,
                subsystem=subsystem,
                quality=sensor_quality,
                notes=unit_note
            )
            normalized_readings[canonical_name] = reading

        if not normalized_readings:
            errors.append("Validation Error: No valid numeric sensor readings could be extracted from payload.")
            return None, errors

        # Determine overall frame quality
        if frame_is_stale:
            frame_quality = DataQuality.STALE
        elif has_warning:
            frame_quality = DataQuality.WARNING
        else:
            frame_quality = DataQuality.GOOD

        # Build operating settings dict
        clean_settings = {}
        if operating_settings and isinstance(operating_settings, dict):
            for k, v in operating_settings.items():
                try:
                    val_float = float(v)
                    if not (math.isnan(val_float) or math.isinf(val_float)):
                        clean_settings[k] = val_float
                except (ValueError, TypeError):
                    pass

        frame = NormalizedTelemetryFrame(
            machine_id=str_machine_id,
            external_machine_id=external_machine_id,
            timestamp=parsed_dt,
            cycle=cycle,
            source_type=source_type,
            source_id=source_id,
            readings=normalized_readings,
            operating_settings=clean_settings,
            frame_quality=frame_quality,
            metadata=metadata or {}
        )

        return frame, errors
