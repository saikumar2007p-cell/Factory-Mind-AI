"""
backend/app/models/alert.py

Factory Alerts & Degradation Alarms ORM Model.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle = Column(Integer, nullable=False, index=True)

    severity = Column(String(20), nullable=False)   # LOW, MEDIUM, HIGH, CRITICAL
    risk_level = Column(String(20), nullable=False) # MONITOR, WARNING, CRITICAL
    reason = Column(String(255), nullable=False)
    evidence = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE") # ACTIVE, ACKNOWLEDGED, RESOLVED

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    machine = relationship("Machine", back_populates="alerts")
    recommendations = relationship("Recommendation", back_populates="alert")
    work_orders = relationship("WorkOrder", back_populates="alert")

    __table_args__ = (
        Index("ix_alert_machine_status", "machine_id", "status"),
        Index("ix_alert_machine_cycle", "machine_id", "cycle"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "cycle": self.cycle,
            "severity": self.severity,
            "risk_level": self.risk_level,
            "reason": self.reason,
            "evidence": self.evidence,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
        }
