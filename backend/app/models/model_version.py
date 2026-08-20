"""
backend/app/models/model_version.py

Model Version Registry ORM for FactoryMind AI.

Tracks the full lifecycle of every ML model version trained against a machine:
  CANDIDATE → (approval) → ACTIVE → (retire on supersession or rollback) → RETIRED
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, DateTime, Float, ForeignKey,
    Index, JSON, Text, func
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Identity ---
    machine_id = Column(
        Integer,
        ForeignKey("machines.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    version = Column(String(50), nullable=False)          # e.g. "v1.0.0", "v2.1.0"
    model_type = Column(String(100), nullable=False, default="LightGBM+IsolationForest")
    model_artifact_path = Column(String(500), nullable=True)   # abs path to joblib artefacts

    # --- Training provenance ---
    training_dataset_id = Column(String(200), nullable=True)   # filename / dataset reference
    training_date = Column(DateTime(timezone=True), nullable=True)
    training_sample_count = Column(Integer, nullable=True)
    feature_count = Column(Integer, nullable=True)

    # --- Validation metrics (stored as JSON for flexibility) ---
    # Expected keys: rul_rmse, rul_mae, anomaly_f1, anomaly_precision,
    #                anomaly_recall, validation_window, chronological
    validation_metrics = Column(JSON, nullable=True)

    # --- Lifecycle status ---
    # CANDIDATE  – trained, pending administrator approval
    # ACTIVE     – currently deployed for predictions
    # RETIRED    – superseded by a newer ACTIVE version
    # ROLLBACK_CANDIDATE – previously ACTIVE, demoted but available for rollback
    status = Column(String(30), nullable=False, default="CANDIDATE", index=True)

    # --- Approval audit ---
    approved_by = Column(String(100), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    deployed_at = Column(DateTime(timezone=True), nullable=True)
    retired_at = Column(DateTime(timezone=True), nullable=True)
    rollback_reason = Column(Text, nullable=True)

    # --- Lineage ---
    parent_version_id = Column(
        Integer,
        ForeignKey("model_versions.id", ondelete="SET NULL"),
        nullable=True
    )

    # --- Performance monitoring (filled post-deployment) ---
    deployment_prediction_count = Column(Integer, nullable=True, default=0)
    post_deploy_false_alarm_rate = Column(Float, nullable=True)
    post_deploy_accuracy_estimate = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- Relationships ---
    machine = relationship("Machine", back_populates="model_versions")
    child_versions = relationship(
        "ModelVersion",
        foreign_keys=[parent_version_id],
        backref="parent_version",
        remote_side=[id]
    )

    __table_args__ = (
        Index("ix_mv_machine_status", "machine_id", "status"),
        Index("ix_mv_machine_version", "machine_id", "version"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "machine_id": self.machine_id,
            "version": self.version,
            "model_type": self.model_type,
            "model_artifact_path": self.model_artifact_path,
            "training_dataset_id": self.training_dataset_id,
            "training_date": self.training_date.isoformat() if self.training_date else None,
            "training_sample_count": self.training_sample_count,
            "feature_count": self.feature_count,
            "validation_metrics": self.validation_metrics,
            "status": self.status,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "retired_at": self.retired_at.isoformat() if self.retired_at else None,
            "rollback_reason": self.rollback_reason,
            "parent_version_id": self.parent_version_id,
            "deployment_prediction_count": self.deployment_prediction_count,
            "post_deploy_false_alarm_rate": self.post_deploy_false_alarm_rate,
            "post_deploy_accuracy_estimate": self.post_deploy_accuracy_estimate,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
