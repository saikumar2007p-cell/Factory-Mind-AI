"""
backend/app/schemas/work_order.py

Pydantic Schemas for Industrial Maintenance Work Orders & Verification.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class WorkOrderStatus(str, Enum):
    RECOMMENDED = "RECOMMENDED"
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    VERIFIED = "VERIFIED"


class WorkOrderPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class VerificationStatus(str, Enum):
    RESOLVED = "RESOLVED"
    NOT_RESOLVED = "NOT_RESOLVED"
    PARTIALLY_RESOLVED = "PARTIALLY_RESOLVED"
    UNABLE_TO_VERIFY = "UNABLE_TO_VERIFY"
    PENDING = "PENDING"


class WorkOrderAuditLogResponse(BaseModel):
    id: int
    work_order_id: int
    event_type: str
    actor: str
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    notes: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkOrderResponse(BaseModel):
    id: int
    work_order_code: str
    machine_id: int
    source_alert_id: Optional[int] = None
    source_recommendation_id: Optional[int] = None
    priority: WorkOrderPriority
    risk_level: str
    title: str
    description: Optional[str] = None
    observed_evidence: Optional[Dict[str, Any]] = None
    ml_evidence: Optional[Dict[str, Any]] = None
    recommended_action: str
    affected_subsystem: str
    assigned_to: str
    status: WorkOrderStatus
    data_source: str
    due_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verification_status: Optional[VerificationStatus] = None
    verification_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    audit_logs: List[WorkOrderAuditLogResponse] = []

    model_config = ConfigDict(from_attributes=True)


class WorkOrderCreateRequest(BaseModel):
    machine_id: int = Field(description="Target machine ID")
    title: str = Field(description="Work order summary title")
    recommended_action: str = Field(description="Prescriptive action required")
    affected_subsystem: str = Field(default="Turbofan Core", description="Subsystem affected e.g. Low Pressure Turbine")
    priority: Optional[WorkOrderPriority] = None # If None, calculated deterministically
    risk_level: Optional[str] = None
    description: Optional[str] = None
    source_alert_id: Optional[int] = None
    source_recommendation_id: Optional[int] = None
    observed_evidence: Optional[Dict[str, Any]] = None
    ml_evidence: Optional[Dict[str, Any]] = None
    assigned_to: Optional[str] = Field(default="Unassigned")
    data_source: Optional[str] = None
    due_days: Optional[int] = 7


class WorkOrderUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[WorkOrderPriority] = None
    affected_subsystem: Optional[str] = None
    assigned_to: Optional[str] = None
    due_at: Optional[datetime] = None


class WorkOrderAssignRequest(BaseModel):
    assigned_to: str = Field(description="Technician or Maintenance Engineer identifier")
    actor: Optional[str] = Field(default="Supervisor", description="Actor performing assignment")
    notes: Optional[str] = None


class WorkOrderVerifyRequest(BaseModel):
    verification_status: VerificationStatus = Field(description="Outcome: RESOLVED, NOT_RESOLVED, PARTIALLY_RESOLVED, UNABLE_TO_VERIFY")
    verification_notes: Optional[str] = Field(default=None, description="Operator post-maintenance inspection notes")
    actor: Optional[str] = Field(default="Lead Engineer")


class WorkOrderSummaryResponse(BaseModel):
    total_work_orders: int
    open_count: int
    assigned_count: int
    in_progress_count: int
    completed_count: int
    verification_required_count: int
    verified_count: int
    high_priority_count: int
