"""
backend/app/models/maintenance_outcome.py

Maintenance Outcome (Ground-Truth Feedback) ORM for FactoryMind AI.

Closes the prediction → outcome loop:
  FactoryMind Prediction → Alert → Work Order → Actual Outcome
                                                      ↓
                           Prediction vs Reality → Model Performance
                                                      ↓
                                          Future Training Dataset

Outcome types:
  NO_ISSUE_FOUND        – technician inspected; machine was healthy
  PREVENTIVE_MAINTENANCE – planned PM performed as scheduled
  CORRECTIVE_MAINTENANCE – unplanned corrective action taken
  COMPONENT_REPLACED    – specific component identified and replaced
  MACHINE_FAILURE       – machine failed (FactoryMind should have caught this earlier)
  FALSE_ALARM           – prediction was incorrect; no real issue found
  OTHER                 – does not fit above categories
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey,
    Index, Text, func
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class MaintenanceOutcome(Base):
    __tablename__ = "maintenance_outcomes"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Foreign keys ---
    work_order_id = Column(
        Integer,
        ForeignKey("work_orders.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,   # One outcome per work order
        index=True
    )
    machine_id = Column(
        Integer,
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    linked_prediction_id = Column(
        Integer,
        ForeignKey("predictions.id", ondelete="SET NULL"),
        nullable=True
    )
    linked_alert_id = Column(
        Integer,
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True
    )

    # --- Outcome classification ---
    outcome_type = Column(String(40), nullable=False)
    # Values: NO_ISSUE_FOUND, PREVENTIVE_MAINTENANCE, CORRECTIVE_MAINTENANCE,
    #         COMPONENT_REPLACED, MACHINE_FAILURE, FALSE_ALARM, OTHER

    component_replaced = Column(String(200), nullable=True)   # e.g. "Bearing assembly #3"
    actual_finding = Column(Text, nullable=True)              # Free-text technician description

    # --- Prediction accuracy assessment ---
    prediction_was_correct = Column(Boolean, nullable=True)   # None = not assessed
    false_alarm_reason = Column(Text, nullable=True)          # if outcome_type = FALSE_ALARM

    # --- Retraining flag ---
    # True = include this case in next model retraining dataset
    retraining_candidate = Column(Boolean, nullable=False, default=False)

    # --- Recording metadata ---
    recorded_by = Column(String(100), nullable=False, default="Operator")
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notes = Column(Text, nullable=True)

    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- Relationships ---
    machine = relationship("Machine", back_populates="maintenance_outcomes")
    work_order = relationship("WorkOrder", back_populates="maintenance_outcome")

    __table_args__ = (
        Index("ix_mo_machine_outcome", "machine_id", "outcome_type"),
        Index("ix_mo_retraining", "retraining_candidate"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "work_order_id": self.work_order_id,
            "machine_id": self.machine_id,
            "linked_prediction_id": self.linked_prediction_id,
            "linked_alert_id": self.linked_alert_id,
            "outcome_type": self.outcome_type,
            "component_replaced": self.component_replaced,
            "actual_finding": self.actual_finding,
            "prediction_was_correct": self.prediction_was_correct,
            "false_alarm_reason": self.false_alarm_reason,
            "retraining_candidate": self.retraining_candidate,
            "recorded_by": self.recorded_by,
            "recorded_at": self.recorded_at.isoformat() if self.recorded_at else None,
            "notes": self.notes,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
