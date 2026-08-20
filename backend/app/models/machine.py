"""
backend/app/models/machine.py

Machine / Engine Registry ORM Model.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Float, func
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Machine(Base):
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    unit_number = Column(Integer, unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    machine_type = Column(String(100), nullable=False, default="Turbofan Engine (CF6-80C2)")
    location = Column(String(100), nullable=False, default="Test Cell 1")
    status = Column(String(50), nullable=False, default="OPERATIONAL")  # OPERATIONAL, MONITORING, DEGRADED, FAILED

    current_cycle = Column(Integer, nullable=False, default=0)

    # --- Telemetry data freshness state (independent of health status) ---
    # CURRENT      – telemetry received within freshness window
    # STALE        – last telemetry outside freshness window, machine state unknown
    # NO_NEW_DATA  – has historical data but nothing new since last session
    # NO_DATA      – registered but has never sent telemetry
    telemetry_state = Column(String(20), nullable=False, default="NO_DATA")
    last_telemetry_at = Column(DateTime(timezone=True), nullable=True)
    telemetry_freshness_seconds = Column(Integer, nullable=False, default=300)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    telemetry_records = relationship("Telemetry", back_populates="machine", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="machine", cascade="all, delete-orphan")
    anomalies = relationship("Anomaly", back_populates="machine", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="machine", cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="machine", cascade="all, delete-orphan")
    work_orders = relationship("WorkOrder", back_populates="machine", cascade="all, delete-orphan")
    model_versions = relationship("ModelVersion", back_populates="machine", cascade="all, delete-orphan")
    behavioral_changes = relationship("BehavioralChange", back_populates="machine", cascade="all, delete-orphan")
    maintenance_outcomes = relationship("MaintenanceOutcome", back_populates="machine", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "unit_number": self.unit_number,
            "name": self.name,
            "machine_type": self.machine_type,
            "location": self.location,
            "status": self.status,
            "current_cycle": self.current_cycle,
            "telemetry_state": self.telemetry_state,
            "last_telemetry_at": self.last_telemetry_at.isoformat() if self.last_telemetry_at else None,
            "telemetry_freshness_seconds": self.telemetry_freshness_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

