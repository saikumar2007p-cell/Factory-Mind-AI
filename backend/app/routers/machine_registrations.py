"""
backend/app/routers/machine_registrations.py

Machine Registration Review Router for FactoryMind AI.

Manages pending machine registration requests from uploaded telemetry.
Allows Administrators to approve (creating the machine and ingesting data)
or reject (quarantining/cleaning up data) unknown machine IDs.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.security import AuthUser, require_role
from backend.app.services.machine_registration_service import MachineRegistrationService
from backend.app.schemas.machine_registration import (
    MachineRegistrationRequestResponse,
    ApproveRegistrationRequest,
    RejectRegistrationRequest
)

router = APIRouter(prefix="/machine-registrations", tags=["Machine Registration Review"])

require_admin = require_role(["admin"])
require_operator = require_role(["admin", "operator"])


@router.get("", response_model=List[MachineRegistrationRequestResponse])
async def list_machine_registrations(
    status_filter: Optional[str] = Query(default=None, description="Filter: PENDING_REVIEW|APPROVED|REJECTED"),
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns all machine registration requests, optionally filtered by status."""
    svc = MachineRegistrationService(db)
    requests = await svc.get_all_requests(status_filter=status_filter)
    return [r.to_dict() for r in requests]


@router.get("/pending", response_model=List[MachineRegistrationRequestResponse])
async def list_pending_machine_registrations(
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns all PENDING_REVIEW machine registration requests."""
    svc = MachineRegistrationService(db)
    requests = await svc.get_pending_requests()
    return [r.to_dict() for r in requests]


@router.get("/count-pending", response_model=Dict[str, int])
async def get_pending_count(
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns the count of pending registration requests for UI badges."""
    svc = MachineRegistrationService(db)
    count = await svc.get_pending_count()
    return {"pending_count": count}


@router.get("/{request_id}", response_model=MachineRegistrationRequestResponse)
async def get_machine_registration(
    request_id: int,
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns a specific machine registration request by ID."""
    svc = MachineRegistrationService(db)
    req = await svc.get_request_by_id(request_id)
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Registration request {request_id} not found.")
    return req.to_dict()


@router.post("/{request_id}/approve", response_model=Dict[str, Any])
async def approve_machine_registration(
    request_id: int,
    payload: ApproveRegistrationRequest,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Administrator approves a pending machine registration request:
    - Atomically creates a new Machine in the registry
    - Marks request as APPROVED
    - Links created machine
    Requires ADMIN authorization.
    """
    svc = MachineRegistrationService(db)
    try:
        result = await svc.approve_registration(
            request_id=request_id,
            machine_name=payload.machine_name,
            machine_type=payload.machine_type,
            location=payload.location,
            reviewed_by=payload.reviewed_by or user.username,
            review_notes=payload.review_notes
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/{request_id}/reject", response_model=Dict[str, Any])
async def reject_machine_registration(
    request_id: int,
    payload: RejectRegistrationRequest,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Administrator rejects a pending machine registration request:
    - Marks request as REJECTED
    - Quarantined data file is safely removed
    Requires ADMIN authorization.
    """
    svc = MachineRegistrationService(db)
    try:
        result = await svc.reject_registration(
            request_id=request_id,
            reviewed_by=payload.reviewed_by or user.username,
            review_notes=payload.review_notes
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
