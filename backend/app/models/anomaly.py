"""
backend/app/models/anomaly.py

Anomaly Event ORM Model.
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index, JSON, func
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle = Column(Integer, nullable=False, index=True)

    anomaly_score = Column(Float, nullable=False)
    anomaly_status = Column(String(20), nullable=False)
    raw_decision = Column(Float, nullable=False)
    evidence = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    machine = relationship("Machine", back_populates="anomalies")

    __table_args__ = (
        Index("ix_anomaly_machine_cycle", "machine_id", "cycle"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "cycle": self.cycle,
            "anomaly_score": self.anomaly_score,
            "anomaly_status": self.anomaly_status,
            "raw_decision": self.raw_decision,
            "evidence": self.evidence,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
