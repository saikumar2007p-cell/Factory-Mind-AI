"""
backend/app/schemas/telemetry.py

Pydantic schemas for sensor telemetry data.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class TelemetryReading(BaseModel):
    cycle: int
    setting_1: float
    setting_2: float
    setting_3: float
    s_1: float
    s_2: float
    s_3: float
    s_4: float
    s_5: float
    s_6: float
    s_7: float
    s_8: float
    s_9: float
    s_10: float
    s_11: float
    s_12: float
    s_13: float
    s_14: float
    s_15: float
    s_16: float
    s_17: float
    s_18: float
    s_19: float
    s_20: float
    s_21: float

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
