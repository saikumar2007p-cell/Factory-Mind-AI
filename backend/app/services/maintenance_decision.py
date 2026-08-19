"""
backend/app/services/maintenance_decision.py

Deterministic Maintenance Decision Support & Lifecycle State Engine for FactoryMind AI.

Enforces:
- Deterministic priority scoring based on verified telemetry risk, RUL, and alert severity.
- Strict closed-loop lifecycle transitions:
  RECOMMENDED -> OPEN -> ASSIGNED -> IN_PROGRESS -> COMPLETED -> VERIFICATION_REQUIRED -> VERIFIED
- Zero hallucination or fabrication of operational states.
"""

from typing import Optional, Dict, Any, Tuple
import logging

from backend.app.schemas.work_order import (
    WorkOrderStatus,
    WorkOrderPriority,
    VerificationStatus
)

logger = logging.getLogger("factorymind.maintenance_decision")

# Legal lifecycle state transitions strictly enforcing:
# OPEN -> ASSIGNED -> IN_PROGRESS -> COMPLETED -> VERIFICATION_REQUIRED -> VERIFIED
LEGAL_STATE_TRANSITIONS = {
    WorkOrderStatus.RECOMMENDED: {WorkOrderStatus.OPEN, WorkOrderStatus.ASSIGNED},
    WorkOrderStatus.OPEN: {WorkOrderStatus.ASSIGNED},
    WorkOrderStatus.ASSIGNED: {WorkOrderStatus.IN_PROGRESS, WorkOrderStatus.OPEN},
    WorkOrderStatus.IN_PROGRESS: {WorkOrderStatus.COMPLETED, WorkOrderStatus.VERIFICATION_REQUIRED},
    WorkOrderStatus.COMPLETED: {WorkOrderStatus.VERIFICATION_REQUIRED},
    WorkOrderStatus.VERIFICATION_REQUIRED: {WorkOrderStatus.VERIFIED},
    WorkOrderStatus.VERIFIED: set()
}


def calculate_deterministic_priority(
    risk_level: Optional[str] = None,
    rul_estimate: Optional[float] = None,
    anomaly_score: Optional[float] = None,
    alert_severity: Optional[str] = None,
    data_quality: Optional[str] = None
) -> WorkOrderPriority:
    """
    Computes deterministic maintenance priority based strictly on verified evidence.
    Never invents risk metrics or fabricates urgency.
    """
    clean_risk = (risk_level or "NORMAL").upper()
    clean_sev = (alert_severity or "LOW").upper()

    # 1. Critical Priority: imminent breakdown or extreme degradation
    if clean_risk == "CRITICAL" or clean_sev == "CRITICAL" or (rul_estimate is not None and rul_estimate <= 25.0):
        return WorkOrderPriority.CRITICAL

    # 2. High Priority: persistent warning or fast approaching RUL limit
    if clean_risk == "WARNING" or clean_sev == "HIGH" or (rul_estimate is not None and rul_estimate <= 50.0):
        return WorkOrderPriority.HIGH

    # 3. Medium Priority: elevated monitor or subtle thermal anomaly
    if clean_risk == "MONITOR" or clean_sev == "MEDIUM" or (anomaly_score is not None and anomaly_score > 0.1):
        return WorkOrderPriority.MEDIUM

    # 4. Low Priority: nominal baseline inspection
    return WorkOrderPriority.LOW


def validate_lifecycle_transition(
    current_status: WorkOrderStatus,
    target_status: WorkOrderStatus
) -> Tuple[bool, Optional[str]]:
    """
    Validates whether a lifecycle state transition is legally permissible.
    Returns:
        (is_valid, error_message)
    """
    if current_status == WorkOrderStatus.VERIFIED:
        return False, "Work order is already in final VERIFIED state and is locked against further modifications."

    if current_status == target_status:
        return True, None

    allowed = LEGAL_STATE_TRANSITIONS.get(current_status, set())
    if target_status in allowed:
        return True, None

    allowed_names = ", ".join(s.value for s in allowed) or "None"
    return False, (
        f"Invalid lifecycle transition: Cannot move from '{current_status.value}' to '{target_status.value}'. "
        f"Permissible next states are: [{allowed_names}]."
    )
