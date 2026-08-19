"""
backend/app/services/unit_normalizer.py

Physical Unit Normalization Service for FactoryMind AI.

Converts diverse industrial sensor engineering units into canonical turbofan prognostic units.
Strict Rule: Only converts when the source unit is explicitly known. Never guesses or silently assumes units.
"""

from typing import Tuple, Optional
import math
import logging

logger = logging.getLogger("factorymind.units")

# Canonical unit targets for turbofan subsystems
CANONICAL_TARGET_UNITS = {
    "temperature": "°R",    # Degrees Rankine
    "pressure": "psia",     # Pounds per square inch absolute
    "speed": "rpm",         # Revolutions per minute
    "flow": "lbm/s",        # Pounds mass per second
    "ratio": "--",          # Dimensionless ratio
    "enthalpy": "--"
}


def normalize_unit(
    value: float,
    source_unit: Optional[str],
    target_dimension: str
) -> Tuple[float, str, str]:
    """
    Normalizes a numerical sensor value from source_unit to the canonical target unit.
    
    Returns:
        (converted_value, canonical_unit, quality_note)
    """
    if source_unit is None or not source_unit.strip():
        return value, "Unit unavailable", "Source unit was not provided; value preserved without conversion."

    clean_unit = source_unit.strip().lower()
    canonical_target = CANONICAL_TARGET_UNITS.get(target_dimension.lower(), "--")

    # 1. Temperature Normalization (Target: °R)
    if target_dimension.lower() in ["temperature", "temp"]:
        if clean_unit in ["°r", "deg r", "r", "rankine"]:
            return value, "°R", "Exact canonical match"
        elif clean_unit in ["°c", "deg c", "c", "celsius"]:
            # °C -> °R: (C + 273.15) * 1.8
            converted = (value + 273.15) * 1.8
            return round(converted, 3), "°R", "Converted from Celsius (°C)"
        elif clean_unit in ["°f", "deg f", "f", "fahrenheit"]:
            # °F -> °R: F + 459.67
            converted = value + 459.67
            return round(converted, 3), "°R", "Converted from Fahrenheit (°F)"
        elif clean_unit in ["k", "kelvin"]:
            # K -> °R: K * 1.8
            converted = value * 1.8
            return round(converted, 3), "°R", "Converted from Kelvin (K)"

    # 2. Pressure Normalization (Target: psia)
    elif target_dimension.lower() in ["pressure", "press"]:
        if clean_unit in ["psia", "psi", "lbs/in2"]:
            return value, "psia", "Exact canonical match"
        elif clean_unit in ["kpa", "kilopascal"]:
            # kPa -> psia: kPa * 0.1450377
            converted = value * 0.1450377
            return round(converted, 3), "psia", "Converted from Kilopascals (kPa)"
        elif clean_unit in ["bar"]:
            # bar -> psia: bar * 14.50377
            converted = value * 14.50377
            return round(converted, 3), "psia", "Converted from Bar"
        elif clean_unit in ["mpa"]:
            # MPa -> psia: MPa * 145.0377
            converted = value * 145.0377
            return round(converted, 3), "psia", "Converted from Megapascals (MPa)"
        elif clean_unit in ["pa", "pascal"]:
            converted = value * 0.0001450377
            return round(converted, 3), "psia", "Converted from Pascals (Pa)"

    # 3. Rotational Speed (Target: rpm)
    elif target_dimension.lower() in ["speed", "rotational_speed"]:
        if clean_unit in ["rpm", "rev/min", "r/min"]:
            return value, "rpm", "Exact canonical match"
        elif clean_unit in ["rad/s", "rads/s", "radians/sec"]:
            # rad/s -> rpm: rad/s * 60 / (2 * pi)
            converted = value * (60.0 / (2.0 * math.pi))
            return round(converted, 2), "rpm", "Converted from Radians per second"
        elif clean_unit in ["hz", "1/s"]:
            converted = value * 60.0
            return round(converted, 2), "rpm", "Converted from Hertz (Hz)"

    # 4. Mass Flow Rate (Target: lbm/s)
    elif target_dimension.lower() in ["flow", "mass_flow"]:
        if clean_unit in ["lbm/s", "lbs/s", "lb/s"]:
            return value, "lbm/s", "Exact canonical match"
        elif clean_unit in ["kg/s", "kgs/s"]:
            converted = value * 2.20462
            return round(converted, 3), "lbm/s", "Converted from kg/s"

    # Fallback for unrecognized unit
    return value, source_unit, f"Unknown conversion from '{source_unit}' to '{canonical_target}'; raw value preserved."
