"""
backend/app/schemas/simulation.py

Pydantic schemas for simulation playback controls and live status.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    unit_number: int = Field(default=1, description="Engine unit ID to replay (1 to 100)")
    start_cycle: int = Field(default=1, description="Starting cycle for replay")
    speed_multiplier: float = Field(default=1.0, ge=0.1, le=10.0, description="Playback speed factor")
    auto_advance: bool = Field(default=True, description="Whether simulation advances on timer")


class SimulationStatusResponse(BaseModel):
    is_running: bool
    is_paused: bool
    unit_number: int
    current_cycle: int
    max_cycle: int
    speed_multiplier: float
    total_cycles_in_trajectory: int
    latest_rul: Optional[float] = None
    latest_health_index: Optional[float] = None
    latest_risk_level: Optional[str] = None
    latest_anomaly_score: Optional[float] = None
    active_alerts_count: int = 0


class SimulationStepResponse(BaseModel):
    unit_number: int
    cycle: int
    is_completed: bool
    prediction: Optional[Dict[str, Any]] = None
    telemetry: Optional[Dict[str, Any]] = None
    alert_triggered: bool = False
    alert: Optional[Dict[str, Any]] = None
