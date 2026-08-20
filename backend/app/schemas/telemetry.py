"""
backend/app/schemas/telemetry.py

Pydantic schemas for sensor telemetry data.

Supports both C-MAPSS (21-channel fixed) and external (variable-channel) sources.
All 21 C-MAPSS sensor fields are Optional to allow external data to be ingested
without fabricating missing channels.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class TelemetryReading(BaseModel):
    cycle: int
    data_source_type: Optional[str] = "CMAPSS"

    # Operational settings — optional for external data
    setting_1: Optional[float] = None
    setting_2: Optional[float] = None
    setting_3: Optional[float] = None

    # 21 NASA C-MAPSS Sensor Channels — all Optional.
    # Non-null for C-MAPSS simulation rows; may be None for external data.
    s_1: Optional[float] = None
    s_2: Optional[float] = None
    s_3: Optional[float] = None
    s_4: Optional[float] = None
    s_5: Optional[float] = None
    s_6: Optional[float] = None
    s_7: Optional[float] = None
    s_8: Optional[float] = None
    s_9: Optional[float] = None
    s_10: Optional[float] = None
    s_11: Optional[float] = None
    s_12: Optional[float] = None
    s_13: Optional[float] = None
    s_14: Optional[float] = None
    s_15: Optional[float] = None
    s_16: Optional[float] = None
    s_17: Optional[float] = None
    s_18: Optional[float] = None
    s_19: Optional[float] = None
    s_20: Optional[float] = None
    s_21: Optional[float] = None

    # Generic sensor store for external / customer data (canonical_name → value)
    sensor_data: Optional[Dict[str, float]] = None

    model_config = ConfigDict(from_attributes=True)


class TelemetryResponse(TelemetryReading):
    id: int
    machine_id: int
    ingested_at: Optional[datetime] = None


class TelemetryHistoryResponse(BaseModel):
    machine_id: int
    unit_number: int
    count: int
    telemetry: List[TelemetryResponse]

