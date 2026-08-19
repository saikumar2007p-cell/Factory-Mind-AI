"""
backend/app/schemas/alert.py

Pydantic schemas for alerts and recommendations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class AlertResponse(BaseModel):
    id: int
    machine_id: int
    cycle: int
    severity: str
    risk_level: str
    reason: str
    evidence: Optional[Dict[str, Any]] = None
    status: str
    created_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(BaseModel):
    total: int
    active_count: int
    alerts: List[AlertResponse]


class RecommendationResponse(BaseModel):
    id: int
    machine_id: int
    alert_id: Optional[int] = None
    prediction_id: Optional[int] = None
    recommendation_text: str
    source: str
    is_fallback: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
