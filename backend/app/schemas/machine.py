"""
backend/app/schemas/machine.py

Pydantic schemas for machine fleet entities.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class MachineBase(BaseModel):
    unit_number: int
    name: str
    machine_type: str = "Turbofan Engine (CF6-80C2)"
    location: str = "Test Cell 1"
    status: str = "OPERATIONAL"


class MachineCreate(MachineBase):
    pass


class MachineResponse(MachineBase):
    id: int
    current_cycle: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    latest_rul: Optional[float] = None
    latest_health_index: Optional[float] = None
    latest_risk_level: Optional[str] = None
    active_alert_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class MachineListResponse(BaseModel):
    total_machines: int
    operational_count: int
    warning_count: int
    critical_count: int
    machines: List[MachineResponse]
