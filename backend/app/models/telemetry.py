"""
backend/app/models/telemetry.py

Real Sensor Telemetry & Operating Conditions ORM Model.
"""

from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, Index, UniqueConstraint, func
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    cycle = Column(Integer, nullable=False, index=True)

    # Operational settings
    setting_1 = Column(Float, nullable=False)
    setting_2 = Column(Float, nullable=False)
    setting_3 = Column(Float, nullable=False)

    # 21 NASA C-MAPSS Sensor Channels
    s_1 = Column(Float, nullable=False)
    s_2 = Column(Float, nullable=False)
    s_3 = Column(Float, nullable=False)
    s_4 = Column(Float, nullable=False)
    s_5 = Column(Float, nullable=False)
    s_6 = Column(Float, nullable=False)
    s_7 = Column(Float, nullable=False)
    s_8 = Column(Float, nullable=False)
    s_9 = Column(Float, nullable=False)
    s_10 = Column(Float, nullable=False)
    s_11 = Column(Float, nullable=False)
    s_12 = Column(Float, nullable=False)
    s_13 = Column(Float, nullable=False)
    s_14 = Column(Float, nullable=False)
    s_15 = Column(Float, nullable=False)
    s_16 = Column(Float, nullable=False)
    s_17 = Column(Float, nullable=False)
    s_18 = Column(Float, nullable=False)
    s_19 = Column(Float, nullable=False)
    s_20 = Column(Float, nullable=False)
    s_21 = Column(Float, nullable=False)

    ingested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    machine = relationship("Machine", back_populates="telemetry_records")

    __table_args__ = (
        Index("ix_telemetry_machine_cycle", "machine_id", "cycle"),
        UniqueConstraint("machine_id", "cycle", name="uq_telemetry_machine_cycle"),
    )

    def to_dict(self):
        d = {
            "id": self.id,
            "machine_id": self.machine_id,
            "cycle": self.cycle,
            "setting_1": self.setting_1,
            "setting_2": self.setting_2,
            "setting_3": self.setting_3,
            "ingested_at": self.ingested_at.isoformat() if self.ingested_at else None,
        }
        for i in range(1, 22):
            d[f"s_{i}"] = getattr(self, f"s_{i}")
        return d
