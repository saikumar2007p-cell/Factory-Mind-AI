"""
backend/app/models/recommendation.py

Maintenance Recommendation ORM Model.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Index, func
from sqlalchemy.orm import relationship
from backend.app.database import Base


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    machine_id = Column(Integer, ForeignKey("machines.id", ondelete="CASCADE"), nullable=False, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id", ondelete="SET NULL"), nullable=True, index=True)

    recommendation_text = Column(String(1000), nullable=False)
    source = Column(String(50), nullable=False, default="DETERMINISTIC_RULES") # GEMINI_GENAI or DETERMINISTIC_RULES
    is_fallback = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    machine = relationship("Machine", back_populates="recommendations")
    alert = relationship("Alert", back_populates="recommendations")
    work_orders = relationship("WorkOrder", back_populates="recommendation")

    __table_args__ = (
        Index("ix_rec_machine_created", "machine_id", "created_at"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "alert_id": self.alert_id,
            "prediction_id": self.prediction_id,
            "recommendation_text": self.recommendation_text,
            "source": self.source,
            "is_fallback": self.is_fallback,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
