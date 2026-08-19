"""
backend/app/services/sensor_mapping.py

Configurable Industrial Sensor Taxonomy and Canonical Mapping Service for FactoryMind AI.

Maps arbitrary plant/IoT/REST/CSV sensor channel names into FactoryMind's canonical
C-MAPSS turbofan prognostic sensor schema.
"""

from typing import Dict, Optional, Tuple, List, Any
import logging

logger = logging.getLogger("factorymind.mapping")

# Canonical 21 Sensor Definitions for Turbofan Prognostics
CANONICAL_SENSOR_DEFINITIONS = {
    "s_1": {"name": "T2", "dimension": "temperature", "unit": "°R", "subsystem": "Fan Inlet", "description": "Total temperature at fan inlet"},
    "s_2": {"name": "T24", "dimension": "temperature", "unit": "°R", "subsystem": "Low Pressure Compressor", "description": "Total temperature at LPC outlet"},
    "s_3": {"name": "T30", "dimension": "temperature", "unit": "°R", "subsystem": "High Pressure Compressor", "description": "Total temperature at HPC outlet"},
    "s_4": {"name": "T50", "dimension": "temperature", "unit": "°R", "subsystem": "Low Pressure Turbine", "description": "Total temperature at LPT outlet"},
    "s_5": {"name": "P2", "dimension": "pressure", "unit": "psia", "subsystem": "Fan Inlet", "description": "Pressure at fan inlet"},
    "s_6": {"name": "P15", "dimension": "pressure", "unit": "psia", "subsystem": "Bypass Duct", "description": "Total pressure in bypass-duct"},
    "s_7": {"name": "P30", "dimension": "pressure", "unit": "psia", "subsystem": "High Pressure Compressor", "description": "Total pressure at HPC outlet"},
    "s_8": {"name": "Nf", "dimension": "speed", "unit": "rpm", "subsystem": "Fan", "description": "Physical fan speed"},
    "s_9": {"name": "Nc", "dimension": "speed", "unit": "rpm", "subsystem": "Core Engine", "description": "Physical core speed"},
    "s_10": {"name": "epr", "dimension": "ratio", "unit": "--", "subsystem": "Overall Engine", "description": "Engine pressure ratio (P50/P2)"},
    "s_11": {"name": "Ps30", "dimension": "pressure", "unit": "psia", "subsystem": "High Pressure Compressor", "description": "Static pressure at HPC outlet"},
    "s_12": {"name": "phi", "dimension": "flow", "unit": "pps/psi", "subsystem": "Fuel System", "description": "Ratio of fuel flow to Ps30"},
    "s_13": {"name": "NRf", "dimension": "speed", "unit": "rpm", "subsystem": "Fan", "description": "Corrected fan speed"},
    "s_14": {"name": "NRc", "dimension": "speed", "unit": "rpm", "subsystem": "Core Engine", "description": "Corrected core speed"},
    "s_15": {"name": "BPR", "dimension": "ratio", "unit": "--", "subsystem": "Bypass Duct", "description": "Bypass Ratio"},
    "s_16": {"name": "farB", "dimension": "ratio", "unit": "--", "subsystem": "Combustor", "description": "Burner fuel-air ratio"},
    "s_17": {"name": "htBleed", "dimension": "enthalpy", "unit": "--", "subsystem": "Bleed Air System", "description": "Bleed Enthalpy"},
    "s_18": {"name": "Nf_dmd", "dimension": "speed", "unit": "rpm", "subsystem": "FADEC / Control", "description": "Demanded fan speed"},
    "s_19": {"name": "PCNfR_dmd", "dimension": "speed", "unit": "rpm", "subsystem": "FADEC / Control", "description": "Demanded corrected fan speed"},
    "s_20": {"name": "W31", "dimension": "flow", "unit": "lbm/s", "subsystem": "High Pressure Turbine", "description": "HPT cool air flow"},
    "s_21": {"name": "W32", "dimension": "flow", "unit": "lbm/s", "subsystem": "Low Pressure Turbine", "description": "LPT cool air flow"}
}

# Common Industrial Aliases (lowercase cleaned strings)
DEFAULT_ALIASES: Dict[str, str] = {
    # Temperature sensors
    "t2": "s_1", "fan_inlet_temp": "s_1", "fan_temp": "s_1", "temp_inlet": "s_1", "t_inlet": "s_1",
    "t24": "s_2", "lpc_outlet_temp": "s_2", "lpc_temp": "s_2", "temp_lpc": "s_2", "temp_01": "s_2",
    "t30": "s_3", "hpc_outlet_temp": "s_3", "hpc_temp": "s_3", "temp_hpc": "s_3", "motor_temperature": "s_3", "t_motor": "s_3",
    "t50": "s_4", "lpt_outlet_temp": "s_4", "lpt_temp": "s_4", "temp_lpt": "s_4", "egt": "s_4", "exhaust_gas_temp": "s_4",
    # Pressure sensors
    "p2": "s_5", "fan_inlet_press": "s_5", "p_inlet": "s_5",
    "p15": "s_6", "bypass_press": "s_6", "bypass_pressure": "s_6",
    "p30": "s_7", "hpc_outlet_press": "s_7", "hpc_pressure": "s_7", "p_hpc": "s_7",
    "epr": "s_10", "engine_pressure_ratio": "s_10",
    "ps30": "s_11", "hpc_static_press": "s_11", "static_pressure": "s_11",
    # Speed sensors
    "nf": "s_8", "fan_speed": "s_8", "fan_rpm": "s_8", "n1": "s_8", "speed_fan": "s_8",
    "nc": "s_9", "core_speed": "s_9", "core_rpm": "s_9", "n2": "s_9", "speed_core": "s_9",
    "nrf": "s_13", "corrected_fan_speed": "s_13", "nrf_rpm": "s_13",
    "nrc": "s_14", "corrected_core_speed": "s_14", "nrc_rpm": "s_14",
    "nf_dmd": "s_18", "demanded_fan_speed": "s_18",
    "pcnfr_dmd": "s_19", "demanded_corrected_fan_speed": "s_19",
    # Fuel & flow & ratios
    "phi": "s_12", "fuel_flow_ratio": "s_12", "fuel_ratio": "s_12",
    "bpr": "s_15", "bypass_ratio": "s_15",
    "farb": "s_16", "fuel_air_ratio": "s_16", "burner_far": "s_16",
    "htbleed": "s_17", "bleed_enthalpy": "s_17", "enthalpy": "s_17",
    "w31": "s_20", "hpt_cool_flow": "s_20", "hpt_coolant": "s_20", "coolant_hpt": "s_20",
    "w32": "s_21", "lpt_cool_flow": "s_21", "lpt_coolant": "s_21", "coolant_lpt": "s_21"
}


class SensorMappingService:
    """
    Service managing dynamic sensor taxonomy mappings from industrial source channels
    to canonical FactoryMind prognostic channels.
    """

    def __init__(self, custom_mappings: Optional[Dict[str, str]] = None):
        self._mappings: Dict[str, str] = dict(DEFAULT_ALIASES)
        if custom_mappings:
            self.register_custom_mappings(custom_mappings)

    def register_custom_mappings(self, mappings: Dict[str, str]):
        """Registers external sensor name overrides or extensions."""
        for external_name, canonical_target in mappings.items():
            clean_ext = external_name.strip().lower()
            clean_target = canonical_target.strip().lower()
            
            # If target is a canonical name like T50 or T30, map to s_4 or s_3
            if clean_target in CANONICAL_SENSOR_DEFINITIONS:
                self._mappings[clean_ext] = clean_target
            else:
                # Search by canonical name
                resolved = None
                for s_id, defn in CANONICAL_SENSOR_DEFINITIONS.items():
                    if defn["name"].lower() == clean_target:
                        resolved = s_id
                        break
                if resolved:
                    self._mappings[clean_ext] = resolved
                else:
                    self._mappings[clean_ext] = clean_target

    def resolve_sensor(self, raw_sensor_name: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Resolves an arbitrary external sensor name into its canonical definition.
        
        Returns:
            (canonical_sensor_id, definition_dict) or None if unmapped.
        """
        clean_name = raw_sensor_name.strip().lower()

        # Direct match with canonical sensor ID (s_1 to s_21)
        if clean_name in CANONICAL_SENSOR_DEFINITIONS:
            return clean_name, CANONICAL_SENSOR_DEFINITIONS[clean_name]

        # Check in alias dictionary
        if clean_name in self._mappings:
            target_id = self._mappings[clean_name]
            if target_id in CANONICAL_SENSOR_DEFINITIONS:
                return target_id, CANONICAL_SENSOR_DEFINITIONS[target_id]

        # Check by exact canonical name match (e.g. "T50", "P30", "Nf")
        for s_id, defn in CANONICAL_SENSOR_DEFINITIONS.items():
            if defn["name"].lower() == clean_name:
                return s_id, defn

        return None

    def get_all_canonical_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Returns all 21 canonical sensor channel definitions."""
        return CANONICAL_SENSOR_DEFINITIONS

    def get_active_mappings(self) -> Dict[str, str]:
        """Returns active dictionary of alias -> canonical sensor ID."""
        return dict(self._mappings)


# Singleton mapping service
_mapping_service_instance: Optional[SensorMappingService] = None


def get_sensor_mapping_service() -> SensorMappingService:
    global _mapping_service_instance
    if _mapping_service_instance is None:
        _mapping_service_instance = SensorMappingService()
    return _mapping_service_instance
