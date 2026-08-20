"""
backend/app/models/machine_registration_request.py

Machine Registration Request ORM for FactoryMind AI.

When an uploaded file references a machine ID unknown to the registry,
the system stages the data as PENDING_REVIEW instead of auto-creating
a ghost machine or silently discarding the data.

Lifecycle:
  Upload with unknown machine ID
        ↓
  MachineRegistrationRequest created (PENDING_REVIEW)
        ↓
  Administrator reviews sample data
        ↓
  APPROVE → creates Machine + ingests staged rows
  REJECT  → quarantines data, records reason
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Index, JSON, Text, func
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class MachineRegistrationRequest(Base):
    __tablename__ = "machine_registration_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Source information ---
    requested_machine_id = Column(String(200), nullable=False)   # ID string from the uploaded file
    source_filename = Column(String(500), nullable=True)
    source_row_count = Column(Integer, nullable=True)
    detected_columns = Column(JSON, nullable=True)               # list of column names found in file
    sample_data = Column(JSON, nullable=True)                    # first 5 rows for admin preview
    quarantine_path = Column(String(1000), nullable=True)        # path to staged data file

    # --- Review status ---
    # PENDING_REVIEW | APPROVED | REJECTED
    status = Column(String(30), nullable=False, default="PENDING_REVIEW", index=True)

    # --- Review metadata ---
    requested_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    review_notes = Column(Text, nullable=True)

    # --- On approval: link to created machine ---
    auto_created_machine_id = Column(
        Integer,
        ForeignKey("machines.id", ondelete="SET NULL"),
        nullable=True
    )

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # --- Relationships ---
    created_machine = relationship("Machine", foreign_keys=[auto_created_machine_id])

    __table_args__ = (
        Index("ix_mrr_status", "status"),
        Index("ix_mrr_machine_id", "requested_machine_id"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "requested_machine_id": self.requested_machine_id,
            "source_filename": self.source_filename,
            "source_row_count": self.source_row_count,
            "detected_columns": self.detected_columns,
            "sample_data": self.sample_data,
            "quarantine_path": self.quarantine_path,
            "status": self.status,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "reviewed_by": self.reviewed_by,
            "review_notes": self.review_notes,
            "auto_created_machine_id": self.auto_created_machine_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
