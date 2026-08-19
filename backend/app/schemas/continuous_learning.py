"""
backend/app/schemas/continuous_learning.py

Pydantic Schemas for Stage 10: Continuous Learning, Maintenance Effectiveness & Executive Intelligence.
Enforces zero data fabrication, explicit unavailable states, and full traceability.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class MaintenanceEffectivenessSummary(BaseModel):
    total_completed_work_orders: int
    total_verified_work_orders: int
    resolved_count: int
    partially_resolved_count: int
    not_resolved_count: int
    unable_to_verify_count: int
    verification_rate_pct: Optional[float] = None
    resolution_rate_pct: Optional[float] = None
    repeat_intervention_count: int
    effectiveness_status: str  # "AVAILABLE", "INSUFFICIENT_DATA", "NO_RECORDS"
    status_message: str


class BeforeAfterComparison(BaseModel):
    work_order_id: int
    work_order_code: str
    machine_id: int
    unit_number: int
    subsystem: str
    action_taken: str
    verification_status: Optional[str] = None
    outcome: str  # "IMPROVED", "UNCHANGED", "DEGRADED", "INSUFFICIENT_DATA"
    before_metrics: Dict[str, Any]
    after_metrics: Optional[Dict[str, Any]] = None
    has_post_maintenance_data: bool
    explanation: str
    verified_at: Optional[str] = None


class MachineMaintenanceHistory(BaseModel):
    machine_id: int
    unit_number: int
    name: str
    maintenance_count: int
    completed_count: int
    verified_count: int
    resolved_count: int
    unresolved_count: int
    repeat_intervention_count: int
    latest_maintenance_status: str
    latest_verification_result: Optional[str] = None
    historical_effectiveness: str
    recurring_issue_status: str
    affected_subsystems: List[str]
    data_quality: str
    ml_compatibility: str
    rul_available: bool
    rul_estimate: Optional[float] = None


class SubsystemReliabilityTrend(BaseModel):
    subsystem: str
    alert_count: int
    critical_alert_count: int
    work_order_count: int
    verified_resolutions: int
    repeat_interventions: int
    unresolved_maintenance: int
    recurrence_frequency: float
    evidence_level: str  # "HIGH EVIDENCE", "MODERATE EVIDENCE", "LOW EVIDENCE", "INSUFFICIENT DATA"
    status_label: str


class RecurringFailure(BaseModel):
    machine_id: int
    unit_number: int
    machine_name: str
    subsystem: str
    issue_pattern: str
    alert_count: int
    work_order_count: int
    repeated_interventions: int
    verification_outcomes: Dict[str, int]
    evidence_level: str  # "HIGH EVIDENCE", "MODERATE EVIDENCE", "LOW EVIDENCE", "INSUFFICIENT DATA"
    status: str  # "RECURRING_FAILURE", "REPEATED_INTERVENTION", "PERSISTENT_DEGRADATION", "STABLE", "INSUFFICIENT_HISTORY"
    explanation: str
    source_work_order_ids: List[int]


class LearningSignal(BaseModel):
    signal_id: str
    signal_type: str
    affected_entity_type: str  # "MACHINE", "SUBSYSTEM", "FLEET", "ACTION"
    entity_id: Optional[int] = None
    entity_name: str
    subsystem: Optional[str] = None
    evidence_count: int
    source_records: Dict[str, List[int]]  # e.g. {"work_orders": [1, 2], "alerts": [3]}
    confidence_level: str  # "HIGH EVIDENCE", "MODERATE EVIDENCE", "LOW EVIDENCE", "INSUFFICIENT DATA"
    observation_title: str
    explanation: str
    generated_at: str


class ExecutiveAttentionItem(BaseModel):
    item_id: str
    category: str
    priority: str
    machine_id: Optional[int] = None
    unit_number: Optional[int] = None
    subsystem: Optional[str] = None
    reason: str
    evidence_summary: str
    recommended_action: str


class ExecutiveSummary(BaseModel):
    total_fleet: int
    healthy_count: int
    warning_count: int
    critical_count: int
    stale_count: int
    active_maintenance_workload: int
    verification_backlog: int
    verified_outcomes_count: int
    resolved_count: int
    recurring_failure_areas: int
    maintenance_effectiveness_label: str
    ml_coverage_pct: float
    rul_coverage_pct: float
    data_quality_summary: str
    top_attention_areas: List[ExecutiveAttentionItem]
    operational_savings_note: str = "Operational savings data not configured."
    data_source: str = "NASA C-MAPSS FD001 — Simulation"
    real_industrial_configured: bool = False


class HistoricalTrendPoint(BaseModel):
    timestamp: str
    label: str
    value: float
    metadata: Optional[Dict[str, Any]] = None


class HistoricalTrend(BaseModel):
    trend_type: str  # "RISK", "ALERTS", "MAINTENANCE", "VERIFICATION", "RECURRENCE"
    has_sufficient_data: bool
    data_points: List[HistoricalTrendPoint]
    message: str


class MaintenanceEffectivenessResponse(BaseModel):
    summary: MaintenanceEffectivenessSummary
    by_subsystem: List[Dict[str, Any]]
    by_action: List[Dict[str, Any]]
    before_after_comparisons: List[BeforeAfterComparison]


class LearningSignalsResponse(BaseModel):
    total_signals: int
    signals: List[LearningSignal]


class ExecutiveIntelligenceResponse(BaseModel):
    executive_summary: ExecutiveSummary
    recurring_failures: List[RecurringFailure]
    subsystem_reliability: List[SubsystemReliabilityTrend]
    learning_signals: List[LearningSignal]


class LearningOverviewResponse(BaseModel):
    executive_summary: ExecutiveSummary
    effectiveness: MaintenanceEffectivenessSummary
    recurring_count: int
    learning_signals_count: int
    subsystems_monitored: int
    timestamp: str
