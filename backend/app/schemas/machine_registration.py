"""
backend/app/schemas/machine_registration.py

Pydantic schemas for the Machine Registration Review API.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class MachineRegistrationRequestResponse(BaseModel):
    id: int
    requested_machine_id: str
    source_filename: Optional[str] = None
    source_row_count: Optional[int] = None
    detected_columns: Optional[List[str]] = None
    sample_data: Optional[List[Dict[str, Any]]] = None
    quarantine_path: Optional[str] = None
    status: str
    requested_at: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None
    auto_created_machine_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ApproveRegistrationRequest(BaseModel):
    machine_name: str = Field(description="Human-readable machine name to assign")
    machine_type: str = Field(default="Industrial Equipment", description="Equipment type")
    location: str = Field(default="Plant Floor", description="Physical location")
    reviewed_by: str = Field(description="Administrator username approving this registration")
    review_notes: Optional[str] = None


class RejectRegistrationRequest(BaseModel):
    reviewed_by: str = Field(description="Administrator username rejecting this registration")
    review_notes: str = Field(description="Mandatory reason for rejection")
