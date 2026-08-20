"""
backend/app/routers/drift.py

Behavioral Change Detection Router for FactoryMind AI.

Provides access to the causally-neutral behavioral change feed
and investigation recording endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.app.database import get_db
from backend.app.security import AuthUser, require_role
from backend.app.services.drift_detector import DriftDetectorService

router = APIRouter(prefix="/drift", tags=["Behavioral Change Detection"])

require_operator = require_role(["admin", "operator"])
require_viewer = require_role(["admin", "operator", "viewer"])


class RecordInvestigationRequest(BaseModel):
    change_type: str = Field(
        description="MACHINE_ANOMALY | SENSOR_ISSUE | OPERATING_CONDITION | DATA_QUALITY | UNKNOWN"
    )
    root_cause: str = Field(description="Brief root cause description")
    investigator: str = Field(description="Name of person investigating")
    notes: Optional[str] = None
    close: bool = Field(default=True, description="If true, marks as CLOSED; if false, marks as INVESTIGATED")


@router.get("/machine/{machine_id}", response_model=List[dict])
async def get_behavioral_changes(
    machine_id: int,
    investigation_status: Optional[str] = Query(default=None, description="Filter: PENDING|INVESTIGATED|CLOSED"),
    user: AuthUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    """Returns behavioral changes detected for a specific machine."""
    svc = DriftDetectorService(db)
    changes = await svc.get_changes_for_machine(machine_id, status_filter=investigation_status)
    return [c.to_dict() for c in changes]


@router.get("/fleet/pending", response_model=List[dict])
async def get_fleet_pending_changes(
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns all PENDING behavioral changes across the entire fleet."""
    svc = DriftDetectorService(db)
    changes = await svc.get_fleet_pending_changes()
    return [c.to_dict() for c in changes]


@router.get("/{change_id}", response_model=dict)
async def get_behavioral_change(
    change_id: int,
    user: AuthUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    """Returns a specific behavioral change record."""
    svc = DriftDetectorService(db)
    change = await svc.get_change_by_id(change_id)
    if not change:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Behavioral change {change_id} not found.")
    return change.to_dict()


@router.post("/{change_id}/investigate", response_model=dict)
async def record_investigation(
    change_id: int,
    payload: RecordInvestigationRequest,
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """
    Records investigation result for a PENDING behavioral change.
    Requires OPERATOR or higher authorization.
    """
    svc = DriftDetectorService(db)
    try:
        change = await svc.record_investigation(
            change_id=change_id,
            change_type=payload.change_type,
            root_cause=payload.root_cause,
            investigator=payload.investigator or user.username,
            notes=payload.notes,
            close=payload.close
        )
        await db.commit()
        return change.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
