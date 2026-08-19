"""
backend/app/services/data_sources/cmapss_adapter.py

NASA C-MAPSS FD001 Simulation & Demonstration Data Source Adapter.

Serves as the baseline demonstration source for FactoryMind AI.
Maintains continuous CONNECTED status for turbofan degradation simulations.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import logging

from backend.app.schemas.normalized_telemetry import (
    DataSourceType,
    DataSourceStatus,
    DataSourceInfo,
    NormalizedTelemetryFrame,
    NormalizedSensorReading,
    DataQuality
)
from backend.app.services.data_sources.base import BaseDataSourceAdapter
from backend.app.services.sensor_mapping import CANONICAL_SENSOR_DEFINITIONS
from ml.dataset import CMAPSSDataset

logger = logging.getLogger("factorymind.adapters.cmapss")


class CMAPSSDataSourceAdapter(BaseDataSourceAdapter):
    """
    Adapter for NASA C-MAPSS FD001 Turbofan Degradation Dataset & Replay Engine.
    """

    def __init__(self):
        super().__init__(
            source_id="cmapss_fd001",
            name="NASA C-MAPSS FD001",
            source_type=DataSourceType.CMAPSS_SIMULATION,
            is_simulation=True,
            stale_threshold_seconds=120.0
        )
        self.status = DataSourceStatus.CONNECTED
        self.dataset = CMAPSSDataset()
        self.record_heartbeat()

    async def connect(self) -> bool:
        self.status = DataSourceStatus.CONNECTED
        self.error_message = None
        self.record_heartbeat()
        return True

    async def disconnect(self) -> bool:
        # C-MAPSS remains connected as default demo source
        self.status = DataSourceStatus.DISCONNECTED
        return True

    def get_info(self, is_active: bool = True) -> DataSourceInfo:
        return DataSourceInfo(
            source_id=self.source_id,
            name=self.name,
            source_type=self.source_type,
            status=self.status,
            is_active=is_active,
            is_simulation=True,
            last_data_received=self.last_data_received,
            is_stale=self.is_stale(),
            description="High-fidelity turbofan run-to-failure degradation dataset (100 training engines, 100 test engines).",
            details={
                "dataset": "NASA C-MAPSS FD001",
                "subsystems": "Fan, LPC, HPC, Combustor, HPT, LPT, Bleed Air",
                "channels": 21,
                "operating_regimes": "Sea Level",
                "mode": "Deterministic Replay Simulation"
            }
        )

    def convert_cmapss_row_to_frame(
        self,
        row_dict: Dict[str, Any],
        timestamp: Optional[datetime] = None
    ) -> NormalizedTelemetryFrame:
        """
        Converts an authentic raw C-MAPSS row dict into a fully normalized telemetry frame.
        """
        unit_num = int(row_dict.get("unit_number", 1))
        cycle = int(row_dict.get("time_cycle", 1))
        ts = timestamp or datetime.now(timezone.utc)

        readings: Dict[str, NormalizedSensorReading] = {}
        for s_id, defn in CANONICAL_SENSOR_DEFINITIONS.items():
            if s_id in row_dict:
                val = float(row_dict[s_id])
                canonical_name = defn["name"]
                readings[canonical_name] = NormalizedSensorReading(
                    sensor_id=s_id,
                    canonical_name=canonical_name,
                    raw_name=s_id,
                    value=val,
                    raw_value=val,
                    unit=defn["unit"],
                    raw_unit=defn["unit"],
                    subsystem=defn["subsystem"],
                    quality=DataQuality.GOOD,
                    notes=f"Authentic C-MAPSS {defn['description']}"
                )

        settings_dict = {
            "setting_1": float(row_dict.get("setting_1", 0.0)),
            "setting_2": float(row_dict.get("setting_2", 0.0)),
            "setting_3": float(row_dict.get("setting_3", 100.0)),
        }

        frame = NormalizedTelemetryFrame(
            machine_id=str(unit_num),
            external_machine_id=f"CF6-80C2-U{unit_num:03d}",
            timestamp=ts,
            cycle=cycle,
            source_type=self.source_type,
            source_id=self.source_id,
            readings=readings,
            operating_settings=settings_dict,
            frame_quality=DataQuality.GOOD,
            metadata={"dataset": "NASA C-MAPSS FD001", "is_simulation": True}
        )

        self.record_heartbeat(ts)
        return frame
