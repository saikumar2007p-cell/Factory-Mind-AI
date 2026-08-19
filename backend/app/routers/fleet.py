"""
backend/app/routers/fleet.py

FastAPI REST Router for Stage 9 Fleet Intelligence, Predictive Planning & Maintenance Analytics.
Exposes real-time fleet analytics, risk distributions, subsystem reliability, and planning priorities.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.schemas.fleet import (
    FleetSummaryResponse,
    FleetMachineListResponse,
    FleetRiskDistributionResponse,
    FleetMaintenanceLoadResponse,
    FleetSubsystemsResponse,
    FleetAttentionResponse,
    FleetPlanningResponse
)
from backend.app.services.fleet_intelligence import FleetIntelligenceService
from backend.app.services.maintenance_planner import MaintenancePlannerService

router = APIRouter(prefix="/fleet", tags=["Fleet Intelligence & Predictive Planning"])


@router.get("/summary", response_model=FleetSummaryResponse)
async def get_fleet_summary(session: AsyncSession = Depends(get_db)):
    """
    Returns authentic fleet-wide health, risk, ML coverage, and work order summary metrics.
    """
    service = FleetIntelligenceService(session)
    data = await service.get_fleet_summary()
    return FleetSummaryResponse(**data)


@router.get("/machines", response_model=FleetMachineListResponse)
async def list_fleet_machines(
    limit: int = 100,
    session: AsyncSession = Depends(get_db)
):
    """
    Returns all registered fleet machines enriched with prognostic state and deterministic ranking.
    """
    service = FleetIntelligenceService(session)
    machines = await service.get_fleet_machines(limit=limit)
    return FleetMachineListResponse(total=len(machines), machines=machines)


@router.get("/risk-distribution", response_model=FleetRiskDistributionResponse)
async def get_fleet_risk_distribution(session: AsyncSession = Depends(get_db)):
    """
    Returns genuine fleet risk distribution breakdown across all machines.
    """
    service = FleetIntelligenceService(session)
    dist = await service.get_fleet_risk_distribution()
    return FleetRiskDistributionResponse(**dist)


@router.get("/maintenance-load", response_model=FleetMaintenanceLoadResponse)
async def get_fleet_maintenance_load(session: AsyncSession = Depends(get_db)):
    """
    Returns real Stage 8 maintenance workload analytics, subsystem backlogs, and verification queues.
    """
    service = FleetIntelligenceService(session)
    load = await service.get_fleet_maintenance_load()
    return FleetMaintenanceLoadResponse(**load)


@router.get("/subsystems", response_model=FleetSubsystemsResponse)
async def get_fleet_subsystems(session: AsyncSession = Depends(get_db)):
    """
    Returns authentic turbofan subsystem defect frequencies and reliability metrics.
    """
    service = FleetIntelligenceService(session)
    subsystems = await service.get_fleet_subsystems()
    return FleetSubsystemsResponse(subsystems=subsystems, total_subsystems=len(subsystems))


@router.get("/attention-required", response_model=FleetAttentionResponse)
async def get_fleet_attention_required(session: AsyncSession = Depends(get_db)):
    """
    Returns machines requiring priority operational attention with actionable evidence points.
    """
    service = FleetIntelligenceService(session)
    items = await service.get_fleet_attention_required()
    return FleetAttentionResponse(total_attention_required=len(items), items=items)


@router.get("/planning", response_model=FleetPlanningResponse)
async def get_fleet_planning(session: AsyncSession = Depends(get_db)):
    """
    Generates deterministic decision-support maintenance planning recommendations.
    Strictly read-only; never automatically creates or mutates work orders.
    """
    planner = MaintenancePlannerService(session)
    plan_data = await planner.generate_fleet_plan()
    return FleetPlanningResponse(**plan_data)
