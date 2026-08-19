"""
backend/app/models/work_order.py

Industrial Maintenance Work Order and Audit Trail ORM Models for FactoryMind AI.

Supports closed-loop maintenance lifecycle:
RECOMMENDED -> OPEN -> ASSIGNED -> IN_PROGRESS -> COMPLETED -> VERIFICATION_REQUIRED -> VERIFIED
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, JSON, func, Text
from sqlalchemy.orm import relationship
from backend.app.database import Base


class WorkOrder(Base):
    __tablename__ = "work_orders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_order_code = Column(String(30), unique=True, index=True, nullable=False)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    source_alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True)
    source_recommendation_id = Column(Integer, ForeignKey("recommendations.id", ondelete="SET NULL"), nullable=True, index=True)

    priority = Column(String(20), nullable=False, default="MEDIUM")       # CRITICAL, HIGH, MEDIUM, LOW
    risk_level = Column(String(20), nullable=False, default="MONITOR")     # CRITICAL, WARNING, MONITOR, NORMAL
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    observed_evidence = Column(JSON, nullable=True)
    ml_evidence = Column(JSON, nullable=True)
    recommended_action = Column(String(1000), nullable=False)
    affected_subsystem = Column(String(100), nullable=False, default="Turbofan Core")
    assigned_to = Column(String(100), nullable=True, default="Unassigned")
    status = Column(String(30), nullable=False, default="OPEN")            # RECOMMENDED, OPEN, ASSIGNED, IN_PROGRESS, COMPLETED, VERIFICATION_REQUIRED, VERIFIED
    data_source = Column(String(100), nullable=False, default="NASA C-MAPSS FD001 — Simulation")

    due_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)

    verification_status = Column(String(30), nullable=True)               # RESOLVED, NOT_RESOLVED, PARTIALLY_RESOLVED, UNABLE_TO_VERIFY, PENDING
    verification_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    machine = relationship("Machine", back_populates="work_orders")
    alert = relationship("Alert", back_populates="work_orders")
    recommendation = relationship("Recommendation", back_populates="work_orders")
    audit_logs = relationship("WorkOrderAuditLog", back_populates="work_order", cascade="all, delete-orphan", order_by="WorkOrderAuditLog.timestamp.asc()", lazy="selectin")

    __table_args__ = (
        Index("ix_wo_machine_status", "machine_id", "status"),
        Index("ix_wo_priority_status", "priority", "status"),
        Index("ix_wo_created_at", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "work_order_code": self.work_order_code,
            "machine_id": self.machine_id,
            "source_alert_id": self.source_alert_id,
            "source_recommendation_id": self.source_recommendation_id,
            "priority": self.priority,
            "risk_level": self.risk_level,
            "title": self.title,
            "description": self.description,
            "observed_evidence": self.observed_evidence,
            "ml_evidence": self.ml_evidence,
            "recommended_action": self.recommended_action,
            "affected_subsystem": self.affected_subsystem,
            "assigned_to": self.assigned_to or "Unassigned",
            "status": self.status,
            "data_source": self.data_source,
            "due_at": self.due_at.isoformat() if self.due_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "verification_status": self.verification_status,
            "verification_notes": self.verification_notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "audit_logs": [log.to_dict() for log in self.audit_logs] if self.audit_logs else []
        }


class WorkOrderAuditLog(Base):
    __tablename__ = "work_order_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_order_id = Column(Integer, ForeignKey("work_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False) # CREATED, ASSIGNED, STARTED, COMPLETED, VERIFIED, NOTE_ADDED, STATUS_CHANGED
    actor = Column(String(100), nullable=False, default="Operator")
    old_status = Column(String(30), nullable=True)
    new_status = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    work_order = relationship("WorkOrder", back_populates="audit_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "work_order_id": self.work_order_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "old_status": self.old_status,
            "new_status": self.new_status,
            "notes": self.notes,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
