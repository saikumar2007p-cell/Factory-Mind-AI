"""
backend/app/schemas/prediction.py

Pydantic schemas for prognostics, anomaly scores, and inference requests.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class ContributingSignal(BaseModel):
    sensor_id: str
    name: str
    subsystem: str
    units: str
    current_value: float
    baseline_value: float
    delta: float
    percent_change: float
    z_score: float
    trend_direction: str
    trend_slope: float
    importance_rank: int


class SensorTrend(BaseModel):
    sensor_id: str
    name: str
    subsystem: str
    trend_direction: str
    slope: float
    current_value: float


class PredictionResponse(BaseModel):
    id: Optional[int] = None
    machine_id: int
    cycle: int
    rul_estimate: float
    anomaly_score: float
    anomaly_status: str
    health_index: float
    risk_score: float
    risk_level: str
    model_version: str
    contributing_signals: Optional[List[Dict[str, Any]]] = None
    trends: Optional[List[Dict[str, Any]]] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class InferenceRequest(BaseModel):
    machine_id: int
    observations: List[Dict[str, Any]]
    apply_hysteresis: bool = True
