"""
backend/app/schemas/fleet.py

Pydantic Schemas for Stage 9 Fleet Intelligence, Predictive Planning & Maintenance Analytics.
Strictly aggregates verified backend database records without fabricated operational data.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FleetSummaryResponse(BaseModel):
    total_machines: int = Field(..., description="Total registered turbofan fleet units")
    healthy_count: int = Field(..., description="Machines in NORMAL operational condition")
    warning_count: int = Field(..., description="Machines in MONITOR or WARNING risk state")
    critical_count: int = Field(..., description="Machines in CRITICAL failure-risk state")
    stale_count: int = Field(..., description="Machines with delayed/stale telemetry")
    missing_data_count: int = Field(..., description="Machines with no telemetry records")
    unknown_count: int = Field(..., description="Machines with insufficient diagnostic data")
    ml_compatible_count: int = Field(..., description="Machines with complete 21-sensor ML schema")
    ml_incompatible_count: int = Field(..., description="Machines with incomplete sensor schema")
    rul_available_count: int = Field(..., description="Machines with genuine RUL prognostics")
    rul_unavailable_count: int = Field(..., description="Machines where RUL is unavailable")
    active_work_orders: int = Field(..., description="Total non-verified active work orders")
    verification_required_count: int = Field(..., description="Work orders awaiting engineering sign-off")
    data_source: str = Field(default="NASA C-MAPSS FD001 — Simulation", description="Active demonstration telemetry source")
    real_industrial_configured: bool = Field(default=False, description="Whether real industrial connector is active")


class FleetMachineItem(BaseModel):
    id: int
    unit_number: int
    name: str
    machine_type: str
    location: str
    status: str
    current_cycle: int
    health_status: str = Field(..., description="NORMAL, WARNING, CRITICAL, STALE, MISSING, UNKNOWN")
    risk_level: str
    health_index: Optional[float] = None
    rul_estimate: Optional[float] = None
    rul_available: bool = False
    anomaly_score: Optional[float] = None
    anomaly_status: Optional[str] = None
    data_quality: str
    ml_compatibility: str
    active_alert_count: int = 0
    active_work_order_id: Optional[int] = None
    active_work_order_code: Optional[str] = None
    active_work_order_status: Optional[str] = None
    ranking_score: float = 0.0
    ranking_evidence: List[str] = Field(default_factory=list)


class FleetMachineListResponse(BaseModel):
    total: int
    machines: List[FleetMachineItem]


class FleetRiskDistributionResponse(BaseModel):
    critical: int = 0
    warning: int = 0
    monitor: int = 0
    normal: int = 0
    stale: int = 0
    unknown_insufficient: int = 0
    breakdown: Dict[str, List[int]] = Field(default_factory=dict, description="Machine IDs grouped by risk category")


class FleetMaintenanceLoadResponse(BaseModel):
    total_work_orders: int
    open_count: int
    assigned_count: int
    in_progress_count: int
    verification_required_count: int
    verified_count: int
    critical_workload: int
    high_priority_workload: int
    medium_low_workload: int
    verification_backlog_count: int
    unresolved_verifications_count: int
    workload_by_machine: Dict[str, Dict[str, int]] = Field(default_factory=dict)
    workload_by_subsystem: Dict[str, int] = Field(default_factory=dict)


class FleetSubsystemItem(BaseModel):
    subsystem: str
    health_status: str
    associated_alert_count: int = 0
    work_order_count: int = 0
    critical_issue_count: int = 0
    warning_issue_count: int = 0
    verification_outcomes: Dict[str, int] = Field(default_factory=dict)
    recurring_issue_count: int = 0
    affected_units: List[int] = Field(default_factory=list)


class FleetSubsystemsResponse(BaseModel):
    subsystems: List[FleetSubsystemItem]
    total_subsystems: int


class FleetAttentionItem(BaseModel):
    machine_id: int
    unit_number: int
    name: str
    risk_level: str
    health_status: str
    rul_estimate: Optional[float] = None
    rul_available: bool = False
    anomaly_status: Optional[str] = None
    data_quality: str
    ml_compatibility: str
    active_alert_count: int = 0
    active_work_order_id: Optional[int] = None
    active_work_order_code: Optional[str] = None
    active_work_order_status: Optional[str] = None
    urgency_score: float = 0.0
    recommended_action: str
    evidence: List[str] = Field(default_factory=list)


class FleetAttentionResponse(BaseModel):
    total_attention_required: int
    items: List[FleetAttentionItem]


class FleetPlanningItem(BaseModel):
    machine_id: int
    unit_number: int
    machine_name: str
    planning_state: str = Field(..., description="Immediate Attention, High Priority, Schedule Inspection, Monitor Closely, No Action Recommended, Insufficient Data")
    urgency_rank: int
    risk_level: str
    rul_estimate: Optional[float] = None
    rul_available: bool = False
    anomaly_status: Optional[str] = None
    data_quality: str
    ml_compatibility: str
    active_work_order_id: Optional[int] = None
    active_work_order_code: Optional[str] = None
    active_work_order_status: Optional[str] = None
    recommendation_title: str
    recommendation_details: str
    suggested_action: str
    evidence_points: List[str] = Field(default_factory=list)


class FleetPlanningResponse(BaseModel):
    total_planned: int
    immediate_attention_count: int = 0
    high_priority_count: int = 0
    schedule_inspection_count: int = 0
    monitor_closely_count: int = 0
    no_action_count: int = 0
    insufficient_data_count: int = 0
    plans: List[FleetPlanningItem]
