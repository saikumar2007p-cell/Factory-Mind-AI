"""
backend/app/routers/model_versions.py

Model Version Registry Router for FactoryMind AI.

Provides full lifecycle management: CANDIDATE → ACTIVE → RETIRED / ROLLBACK.
All approve and rollback actions require Administrator authorization.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.security import AuthUser, require_role
from backend.app.services.model_version_service import ModelVersionService
from backend.app.schemas.model_version import (
    ModelVersionResponse,
    RegisterCandidateRequest,
    ApproveVersionRequest,
    RollbackRequest
)

router = APIRouter(prefix="/model-versions", tags=["Model Versioning"])

require_admin = require_role(["admin"])
require_operator = require_role(["admin", "operator"])


# ---------------------------------------------------------------------------
# LIST / QUERY
# ---------------------------------------------------------------------------

@router.get("", response_model=List[ModelVersionResponse])
async def list_all_model_versions(
    machine_id: Optional[int] = Query(default=None, description="Filter by machine ID"),
    status_filter: Optional[str] = Query(default=None, description="Filter by status: CANDIDATE|ACTIVE|RETIRED|ROLLBACK_CANDIDATE"),
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns all model versions, optionally filtered by machine or status."""
    svc = ModelVersionService(db)
    if machine_id:
        versions = await svc.get_version_history(machine_id)
    else:
        versions = await svc.get_all_versions()

    if status_filter:
        versions = [v for v in versions if v.status == status_filter.upper()]

    return [v.to_dict() for v in versions]


@router.get("/{version_id}", response_model=ModelVersionResponse)
async def get_model_version(
    version_id: int,
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns a specific model version by ID."""
    svc = ModelVersionService(db)
    version = await svc.get_version_by_id(version_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Model version {version_id} not found.")
    return version.to_dict()


@router.get("/machine/{machine_id}/active", response_model=Optional[ModelVersionResponse])
async def get_active_model_version(
    machine_id: int,
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns the currently ACTIVE model version for a machine, or null if none."""
    svc = ModelVersionService(db)
    version = await svc.get_active_version(machine_id)
    if not version:
        return None
    return version.to_dict()


@router.get("/machine/{machine_id}/rollback-candidates", response_model=List[ModelVersionResponse])
async def get_rollback_candidates(
    machine_id: int,
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns all previous versions available for rollback for a machine."""
    svc = ModelVersionService(db)
    candidates = await svc.get_rollback_candidates(machine_id)
    return [v.to_dict() for v in candidates]


# ---------------------------------------------------------------------------
# REGISTER CANDIDATE
# ---------------------------------------------------------------------------

@router.post("", response_model=ModelVersionResponse, status_code=status.HTTP_201_CREATED)
async def register_candidate_version(
    payload: RegisterCandidateRequest,
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new CANDIDATE model version.
    Does not affect any currently running ACTIVE version.
    Requires OPERATOR or higher authorization.
    """
    svc = ModelVersionService(db)
    try:
        version = await svc.register_candidate(
            machine_id=payload.machine_id,
            version=payload.version,
            model_type=payload.model_type,
            model_artifact_path=payload.model_artifact_path,
            training_dataset_id=payload.training_dataset_id,
            training_date=payload.training_date,
            training_sample_count=payload.training_sample_count,
            feature_count=payload.feature_count,
            validation_metrics=payload.validation_metrics,
            parent_version_id=payload.parent_version_id
        )
        await db.commit()
        return version.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---------------------------------------------------------------------------
# APPROVE & DEPLOY (ADMIN only)
# ---------------------------------------------------------------------------

@router.post("/{version_id}/approve", response_model=ModelVersionResponse)
async def approve_model_version(
    version_id: int,
    payload: ApproveVersionRequest,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Administrator approves a CANDIDATE version.
    Atomically retires the current ACTIVE version (→ ROLLBACK_CANDIDATE)
    and promotes the CANDIDATE (→ ACTIVE).
    Requires ADMIN authorization.
    """
    svc = ModelVersionService(db)
    try:
        version = await svc.approve_and_deploy(
            version_id=version_id,
            approved_by=payload.approved_by or user.username,
            notes=payload.notes
        )
        await db.commit()
        return version.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# ---------------------------------------------------------------------------
# ROLLBACK (ADMIN only)
# ---------------------------------------------------------------------------

@router.post("/machine/{machine_id}/rollback", response_model=ModelVersionResponse)
async def rollback_model_version(
    machine_id: int,
    payload: RollbackRequest,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Administrator initiates a rollback for a machine:
    - Retires the current ACTIVE version with rollback_reason
    - Restores the most recently retired ROLLBACK_CANDIDATE to ACTIVE
    Requires ADMIN authorization.
    """
    svc = ModelVersionService(db)
    try:
        version = await svc.rollback(
            machine_id=machine_id,
            rollback_reason=payload.rollback_reason,
            rolled_back_by=payload.rolled_back_by or user.username
        )
        await db.commit()
        return version.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
