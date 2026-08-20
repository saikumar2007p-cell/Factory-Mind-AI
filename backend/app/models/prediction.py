"""
backend/app/models/prediction.py

Machine Learning Prognostics & Risk Prediction ORM Model.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle = Column(Integer, nullable=False, index=True)

    rul_estimate = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=False)
    anomaly_status = Column(String(20), nullable=False)  # NORMAL, ANOMALOUS
    health_index = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False)
    risk_level = Column(String(20), nullable=False)      # NORMAL, MONITOR, WARNING, CRITICAL
    model_version = Column(String(100), nullable=False)

    contributing_signals = Column(JSON, nullable=True)
    trends = Column(JSON, nullable=True)

    # --- Prediction confidence / uncertainty (added Phase 2) ---
    # confidence_level: HIGH | MEDIUM | LOW | INSUFFICIENT_DATA
    confidence_level = Column(String(25), nullable=True)
    confidence_score = Column(Float, nullable=True)            # 0.0 (no confidence) – 1.0 (full confidence)
    out_of_distribution_sensors = Column(JSON, nullable=True)  # list of sensor names outside training range
    confidence_reason = Column(String(500), nullable=True)     # human-readable explanation

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    machine = relationship("Machine", back_populates="predictions")
    maintenance_outcomes = relationship("MaintenanceOutcome", foreign_keys="[MaintenanceOutcome.linked_prediction_id]")

    __table_args__ = (
        Index("ix_prediction_machine_cycle", "machine_id", "cycle"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "cycle": self.cycle,
            "rul_estimate": self.rul_estimate,
            "anomaly_score": self.anomaly_score,
            "anomaly_status": self.anomaly_status,
            "health_index": self.health_index,
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "model_version": self.model_version,
            "contributing_signals": self.contributing_signals,
            "trends": self.trends,
            "confidence_level": self.confidence_level,
            "confidence_score": self.confidence_score,
            "out_of_distribution_sensors": self.out_of_distribution_sensors,
            "confidence_reason": self.confidence_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
