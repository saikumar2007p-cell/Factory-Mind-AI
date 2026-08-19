"""
backend/app/routers/alerts.py

Degradation Alerts & Maintenance Work Orders API routes.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.services.storage_service import StorageService
from backend.app.schemas.alert import (
    AlertResponse,
    AlertListResponse,
    RecommendationResponse
)

router = APIRouter(prefix="/alerts", tags=["Alerts & Maintenance"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    machine_id: Optional[int] = Query(default=None, description="Optional machine ID filter"),
    session: AsyncSession = Depends(get_db)
):
    """Retrieves all active unacknowledged degradation alerts."""
    service = StorageService(session)
    active_alerts = await service.get_active_alerts(machine_id=machine_id)

    return AlertListResponse(
        total=len(active_alerts),
        active_count=len(active_alerts),
        alerts=[AlertResponse(**a.to_dict()) for a in active_alerts]
    )


@router.get("/{machine_id}", response_model=List[AlertResponse])
async def get_machine_alerts(
    machine_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    session: AsyncSession = Depends(get_db)
):
    """Retrieves complete chronological alert history for an engine."""
    service = StorageService(session)
    alerts = await service.get_alert_history(machine_id=machine_id, limit=limit)
    return [AlertResponse(**a.to_dict()) for a in alerts]


from backend.app.security import AuthUser, require_role

@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: int,
    user: AuthUser = Depends(require_role(["admin", "operator", "engineer"])),
    session: AsyncSession = Depends(get_db)
):
    """Marks an active degradation alert as acknowledged by an operator."""
    service = StorageService(session)
    updated = await service.acknowledge_alert(alert_id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert with ID {alert_id} not found."
        )
    await session.commit()
    return AlertResponse(**updated.to_dict())


@router.get("/{machine_id}/recommendations", response_model=List[RecommendationResponse])
async def get_machine_recommendations(
    machine_id: int,
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db)
):
    """Retrieves maintenance recommendations associated with a machine."""
    service = StorageService(session)
    recs = await service.get_recommendations(machine_id=machine_id, limit=limit)
    return [RecommendationResponse(**r.to_dict()) for r in recs]
