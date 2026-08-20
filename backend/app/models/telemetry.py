"""
backend/app/models/telemetry.py

Real Sensor Telemetry & Operating Conditions ORM Model.

Supports two storage modes:
  CMAPSS   – all 21 NASA C-MAPSS channels stored in fixed typed columns
  EXTERNAL – arbitrary customer sensor set stored in sensor_data JSON column
             (the 21 C-MAPSS columns are nullable in this mode)
"""

from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Index, UniqueConstraint, JSON, func
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle = Column(Integer, nullable=False, index=True)

    # --- Source discriminator ---
    # CMAPSS   – simulation / NASA dataset rows
    # EXTERNAL – customer-uploaded or real industrial data
    data_source_type = Column(String(20), nullable=False, default="CMAPSS")

    # Operational settings (nullable for external data that may not provide them)
    setting_1 = Column(Float, nullable=True)
    setting_2 = Column(Float, nullable=True)
    setting_3 = Column(Float, nullable=True)

    # 21 NASA C-MAPSS Sensor Channels — nullable so external data can be stored
    # without fabricating values. Non-null only for CMAPSS rows.
    s_1 = Column(Float, nullable=True)
    s_2 = Column(Float, nullable=True)
    s_3 = Column(Float, nullable=True)
    s_4 = Column(Float, nullable=True)
    s_5 = Column(Float, nullable=True)
    s_6 = Column(Float, nullable=True)
    s_7 = Column(Float, nullable=True)
    s_8 = Column(Float, nullable=True)
    s_9 = Column(Float, nullable=True)
    s_10 = Column(Float, nullable=True)
    s_11 = Column(Float, nullable=True)
    s_12 = Column(Float, nullable=True)
    s_13 = Column(Float, nullable=True)
    s_14 = Column(Float, nullable=True)
    s_15 = Column(Float, nullable=True)
    s_16 = Column(Float, nullable=True)
    s_17 = Column(Float, nullable=True)
    s_18 = Column(Float, nullable=True)
    s_19 = Column(Float, nullable=True)
    s_20 = Column(Float, nullable=True)
    s_21 = Column(Float, nullable=True)

    # Generic sensor data store for EXTERNAL rows (canonical_name → value)
    sensor_data = Column(JSON, nullable=True)

    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    machine = relationship("Machine", back_populates="telemetry_records")

    __table_args__ = (
        Index("ix_telemetry_machine_cycle", "machine_id", "cycle"),
        Index("ix_telemetry_source_type", "data_source_type"),
        UniqueConstraint("machine_id", "cycle", name="uq_telemetry_machine_cycle"),
    )

    def to_dict(self):
        d = {
            "id": self.id,
            "machine_id": self.machine_id,
            "cycle": self.cycle,
            "data_source_type": self.data_source_type,
            "setting_1": self.setting_1,
            "setting_2": self.setting_2,
            "setting_3": self.setting_3,
            "sensor_data": self.sensor_data,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
        }
        for i in range(1, 22):
            d[f"s_{i}"] = getattr(self, f"s_{i}")
        return d

