"""
backend/app/models/behavioral_change.py

Behavioral Change Detection ORM for FactoryMind AI.

Records statistically detected shifts in machine sensor behavior as NEUTRAL observations.
Does NOT conclude machine health impact — that requires human investigation.

Possible change types after investigation:
  MACHINE_ANOMALY      – genuine degradation signal
  OPERATING_CONDITION  – new setpoint, load, or environmental condition
  SENSOR_ISSUE         – replacement, calibration drift, or sensor failure
  DATA_QUALITY         – dropout, spike, freeze, transmission error
  UNKNOWN              – pattern does not match known categories
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey,
    Index, JSON, Text, func
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class BehavioralChange(Base):
    __tablename__ = "behavioral_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(
        Integer,
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    cycle = Column(Integer, nullable=True)
    detected_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # --- Detection details (causally neutral) ---
    affected_sensors = Column(JSON, nullable=True)         # list of sensor IDs with notable drift
    drift_magnitude = Column(Float, nullable=True)         # aggregate statistical distance from baseline
    drift_method = Column(String(30), nullable=False, default="ZSCORE")
    # Supported: MAHALANOBIS, ZSCORE, IQR, CUSUM
    drift_details = Column(JSON, nullable=True)            # per-sensor z-scores, magnitudes

    # --- Investigation lifecycle ---
    # PENDING      – detected, not yet reviewed by operator/engineer
    # INVESTIGATED – root cause identified
    # CLOSED       – resolved or acknowledged with no further action needed
    investigation_status = Column(String(20), nullable=False, default="PENDING", index=True)

    # --- Post-investigation classification (filled after investigation) ---
    # MACHINE_ANOMALY | OPERATING_CONDITION | SENSOR_ISSUE | DATA_QUALITY | UNKNOWN
    change_type = Column(String(30), nullable=True)
    root_cause = Column(String(500), nullable=True)
    investigator = Column(String(100), nullable=True)
    investigated_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # --- Optional link to an alert if this triggered one ---
    linked_alert_id = Column(
        Integer,
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- Relationships ---
    machine = relationship("Machine", back_populates="behavioral_changes")

    __table_args__ = (
        Index("ix_bc_machine_status", "machine_id", "investigation_status"),
        Index("ix_bc_detected_at", "detected_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "cycle": self.cycle,
            "detected_at": self.detected_at.isoformat() if self.detected_at else None,
            "affected_sensors": self.affected_sensors,
            "drift_magnitude": self.drift_magnitude,
            "drift_method": self.drift_method,
            "drift_details": self.drift_details,
            "investigation_status": self.investigation_status,
            "change_type": self.change_type,
            "root_cause": self.root_cause,
            "investigator": self.investigator,
            "investigated_at": self.investigated_at.isoformat() if self.investigated_at else None,
            "notes": self.notes,
            "linked_alert_id": self.linked_alert_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
