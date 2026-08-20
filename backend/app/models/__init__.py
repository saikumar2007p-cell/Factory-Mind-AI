"""
backend/app/models/__init__.py

Exports all database models.
"""

from backend.app.models.machine import Machine
from backend.app.models.telemetry import Telemetry
from backend.app.models.prediction import Prediction
from backend.app.models.anomaly import Anomaly
from backend.app.models.alert import Alert
from backend.app.models.recommendation import Recommendation
from backend.app.models.work_order import WorkOrder, WorkOrderAuditLog
from backend.app.models.model_version import ModelVersion
from backend.app.models.behavioral_change import BehavioralChange
from backend.app.models.maintenance_outcome import MaintenanceOutcome
from backend.app.models.user import User
from backend.app.models.machine_registration_request import MachineRegistrationRequest

__all__ = [
    "Machine",
    "Telemetry",
    "Prediction",
    "Anomaly",
    "Alert",
    "Recommendation",
    "WorkOrder",
    "WorkOrderAuditLog",
    "ModelVersion",
    "BehavioralChange",
    "MaintenanceOutcome",
    "User",
    "MachineRegistrationRequest",
]
