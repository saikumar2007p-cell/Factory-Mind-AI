"""
backend/app/routers/machines.py

Machine Fleet API routes.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.services.storage_service import StorageService
from backend.app.schemas.machine import MachineResponse, MachineListResponse

router = APIRouter(prefix="/machines", tags=["Machines"])


@router.get("", response_model=MachineListResponse)
async def list_machines(session: AsyncSession = Depends(get_db)):
    """Retrieves all registered turbofan engine units and fleet-level summary metrics."""
    service = StorageService(session)
    machines = await service.get_all_machines()

    operational = sum(1 for m in machines if m.status == "OPERATIONAL")
    warning = sum(1 for m in machines if m.status in ["MONITORING", "DEGRADED"])
    critical = sum(1 for m in machines if m.status == "CRITICAL")

    enriched = []
    for m in machines:
        latest_pred = await service.get_latest_prediction(m.id)
        active_alerts = await service.get_active_alerts(m.id)

        m_dict = m.to_dict()
        m_dict["latest_rul"] = latest_pred.rul_estimate if latest_pred else None
        m_dict["latest_health_index"] = latest_pred.health_index if latest_pred else None
        m_dict["latest_risk_level"] = latest_pred.risk_level if latest_pred else "NORMAL"
        m_dict["active_alert_count"] = len(active_alerts)
        enriched.append(MachineResponse(**m_dict))

    return MachineListResponse(
        total_machines=len(machines),
        operational_count=operational,
        warning_count=warning,
        critical_count=critical,
        machines=enriched
    )


@router.get("/{machine_id}", response_model=MachineResponse)
async def get_machine(machine_id: int, session: AsyncSession = Depends(get_db)):
    """Retrieves detailed information and real-time state for a specific machine."""
    service = StorageService(session)
    m = await service.get_machine_by_id(machine_id)
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {machine_id} not found."
        )

    latest_pred = await service.get_latest_prediction(m.id)
    active_alerts = await service.get_active_alerts(m.id)

    m_dict = m.to_dict()
    m_dict["latest_rul"] = latest_pred.rul_estimate if latest_pred else None
    m_dict["latest_health_index"] = latest_pred.health_index if latest_pred else None
    m_dict["latest_risk_level"] = latest_pred.risk_level if latest_pred else "NORMAL"
    m_dict["active_alert_count"] = len(active_alerts)

    return MachineResponse(**m_dict)


@router.get("/{machine_id}/work-orders")
async def get_machine_work_orders(machine_id: int, session: AsyncSession = Depends(get_db)):
    """Retrieves all maintenance work orders associated with a machine."""
    service = StorageService(session)
    orders = await service.list_work_orders(machine_id=machine_id)
    return [o.to_dict() for o in orders]

