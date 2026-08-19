"""
backend/app/routers/work_orders.py

Closed-Loop Maintenance Work Orders & Verification REST API Router for FactoryMind AI.

Supports full lifecycle:
RECOMMENDED -> OPEN -> ASSIGNED -> IN_PROGRESS -> COMPLETED -> VERIFICATION_REQUIRED -> VERIFIED
Traceable evidence linking:
Telemetry -> Prediction -> Risk -> Alert -> Work Order -> Maintenance -> Verification
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.services.storage_service import StorageService
from backend.app.schemas.work_order import (
    WorkOrderStatus,
    WorkOrderPriority,
    VerificationStatus,
    WorkOrderResponse,
    WorkOrderCreateRequest,
    WorkOrderUpdateRequest,
    WorkOrderAssignRequest,
    WorkOrderVerifyRequest,
    WorkOrderSummaryResponse
)

from backend.app.security import AuthUser, require_role

router = APIRouter(prefix="/work-orders", tags=["Maintenance Work Orders & Operations"])

# Verification access requiring operational or administrative role
verify_maintenance_access = require_role(["admin", "operator", "engineer"])


@router.get("", response_model=List[WorkOrderResponse])
async def list_work_orders(
    status: Optional[str] = Query(default=None, description="Filter by status e.g. OPEN, ASSIGNED, IN_PROGRESS, VERIFICATION_REQUIRED, VERIFIED"),
    machine_id: Optional[int] = Query(default=None, description="Filter by target machine ID"),
    priority: Optional[str] = Query(default=None, description="Filter by priority e.g. CRITICAL, HIGH, MEDIUM, LOW"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db)
):
    """Lists all work orders with optional filtering and audit histories."""
    storage = StorageService(db)
    orders = await storage.list_work_orders(
        status=status,
        machine_id=machine_id,
        priority=priority,
        limit=limit,
        offset=offset
    )
    return [o.to_dict() for o in orders]


@router.get("/summary", response_model=WorkOrderSummaryResponse)
async def get_work_orders_summary(
    db: AsyncSession = Depends(get_db)
):
    """Returns real backend counts of active work orders for operational dashboards."""
    storage = StorageService(db)
    stats = await storage.get_work_orders_summary()
    return stats


@router.get("/{work_order_id}", response_model=WorkOrderResponse)
async def get_work_order_details(
    work_order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Retrieves full work order details including timeline audit logs."""
    storage = StorageService(db)
    wo = await storage.get_work_order(work_order_id)
    if not wo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Work order with ID {work_order_id} was not found."
        )
    return wo.to_dict()


@router.get("/{work_order_id}/comparison")
async def get_post_maintenance_comparison(
    work_order_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Returns genuine before-and-after maintenance prognostic telemetry.
    Never fabricates improvement if post-maintenance readings do not exist.
    """
    storage = StorageService(db)
    try:
        comparison = await storage.get_post_maintenance_comparison(work_order_id)
        return comparison
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", response_model=WorkOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_work_order(
    req: WorkOrderCreateRequest,
    user: AuthUser = Depends(verify_maintenance_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates an actionable maintenance work order from alert, AI recommendation, or operator directive.
    Deterministically computes priority if omitted.
    """
    storage = StorageService(db)

    # Check machine existence
    machine = await storage.get_machine(req.machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {req.machine_id} does not exist."
        )

    # Retrieve source alert if provided
    if req.source_alert_id:
        alert = await storage.get_alert(req.source_alert_id)
        if alert and not req.observed_evidence:
            req.observed_evidence = alert.evidence

    wo = await storage.create_work_order(
        machine_id=req.machine_id,
        title=req.title,
        recommended_action=req.recommended_action,
        affected_subsystem=req.affected_subsystem,
        priority=req.priority.value if req.priority else None,
        risk_level=req.risk_level,
        description=req.description,
        source_alert_id=req.source_alert_id,
        source_recommendation_id=req.source_recommendation_id,
        observed_evidence=req.observed_evidence,
        ml_evidence=req.ml_evidence,
        assigned_to=req.assigned_to or "Unassigned",
        data_source=req.data_source or "NASA C-MAPSS FD001 — Simulation",
        due_days=req.due_days or 7,
        actor=user.username
    )
    return wo.to_dict()


@router.post("/{work_order_id}/assign", response_model=WorkOrderResponse)
async def assign_work_order(
    work_order_id: int,
    req: WorkOrderAssignRequest,
    user: AuthUser = Depends(verify_maintenance_access),
    db: AsyncSession = Depends(get_db)
):
    """Assigns work order to a technician and sets status to ASSIGNED."""
    storage = StorageService(db)
    try:
        wo = await storage.assign_work_order(
            work_order_id=work_order_id,
            assigned_to=req.assigned_to,
            actor=req.actor or user.username,
            notes=req.notes
        )
        return wo.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{work_order_id}/start", response_model=WorkOrderResponse)
async def start_work_order(
    work_order_id: int,
    user: AuthUser = Depends(verify_maintenance_access),
    db: AsyncSession = Depends(get_db)
):
    """Records start of maintenance execution and sets status to IN_PROGRESS."""
    storage = StorageService(db)
    try:
        wo = await storage.start_work_order(
            work_order_id=work_order_id,
            actor=user.username
        )
        return wo.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{work_order_id}/complete", response_model=WorkOrderResponse)
async def complete_work_order(
    work_order_id: int,
    user: AuthUser = Depends(verify_maintenance_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Marks physical maintenance task completed.
    Automatically transitions to VERIFICATION_REQUIRED; does NOT declare repair successful.
    """
    storage = StorageService(db)
    try:
        wo = await storage.complete_work_order(
            work_order_id=work_order_id,
            actor=user.username
        )
        return wo.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))


@router.post("/{work_order_id}/verify", response_model=WorkOrderResponse)
async def verify_work_order(
    work_order_id: int,
    req: WorkOrderVerifyRequest,
    user: AuthUser = Depends(verify_maintenance_access),
    db: AsyncSession = Depends(get_db)
):
    """
    Records post-maintenance inspection outcome and marks work order as VERIFIED.
    Outcome must be: RESOLVED, NOT_RESOLVED, PARTIALLY_RESOLVED, or UNABLE_TO_VERIFY.
    """
    storage = StorageService(db)
    try:
        wo = await storage.verify_work_order(
            work_order_id=work_order_id,
            verification_status=req.verification_status.value,
            verification_notes=req.verification_notes,
            actor=req.actor or user.username
        )
        return wo.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
