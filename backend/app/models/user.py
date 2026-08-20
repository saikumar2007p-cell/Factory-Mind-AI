"""
backend/app/models/user.py

Named User Identity Registry ORM for FactoryMind AI.

Enables multiple named administrators (and other roles) with distinct, persistent,
auditable identities. Auth itself remains header-based; this table provides the
identity store so that actions can be attributed to specific named individuals
(e.g. "alice approved model v2", "bob rolled back to v1").

Security note: No passwords are stored. The table is an identity registry only.
"""

from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, Index, func
)
from sqlalchemy.orm import relationship
from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # --- Identity ---
    username = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    email = Column(String(255), unique=True, nullable=True)

    # --- Role ---
    # ADMIN | OPERATOR | ENGINEER | VIEWER
    role = Column(String(20), nullable=False, default="OPERATOR")

    # --- Status ---
    is_active = Column(Boolean, nullable=False, default=True)

    # --- Audit metadata ---
    created_by = Column(String(100), nullable=True)        # username of admin who created this user
    notes = Column(Text, nullable=True)

    # --- Timestamps ---
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_user_role_active", "role", "is_active"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "display_name": self.display_name,
            "email": self.email,
            "role": self.role,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
        }
