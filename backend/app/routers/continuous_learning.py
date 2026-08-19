"""
backend/app/routers/continuous_learning.py

FastAPI Router for Stage 10: Continuous Learning, Maintenance Effectiveness & Executive Intelligence.
Provides strictly read-only analytical endpoints without database mutation capability.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from backend.app.database import get_db
from backend.app.services.maintenance_effectiveness import MaintenanceEffectivenessService
from backend.app.services.reliability_intelligence import ReliabilityIntelligenceService
from backend.app.services.learning_signals import LearningSignalsService
from backend.app.services.executive_intelligence import ExecutiveIntelligenceService
from backend.app.services.historical_trends import HistoricalTrendsService
from backend.app.schemas.continuous_learning import (
    MaintenanceEffectivenessResponse,
    MachineMaintenanceHistory,
    SubsystemReliabilityTrend,
    RecurringFailure,
    LearningSignalsResponse,
    ExecutiveSummary,
    ExecutiveIntelligenceResponse,
    HistoricalTrend,
    LearningOverviewResponse
)

router = APIRouter(prefix="/learning", tags=["Continuous Learning & Executive Intelligence"])


@router.get("/maintenance-effectiveness", response_model=MaintenanceEffectivenessResponse)
async def get_maintenance_effectiveness(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns empirical maintenance effectiveness metrics derived from verified work orders.
    Zero fabricated data; explicitly reports unavailable states.
    """
    service = MaintenanceEffectivenessService(db)
    return await service.get_maintenance_effectiveness()


@router.get("/machine-history", response_model=List[MachineMaintenanceHistory])
async def get_machine_maintenance_history(
    machine_id: Optional[int] = Query(None, description="Optional machine ID filter"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns verified maintenance histories, repeat intervention counts, and ML compatibility per machine.
    """
    service = ReliabilityIntelligenceService(db)
    return await service.get_machine_maintenance_history(machine_id=machine_id)


@router.get("/recurring-failures", response_model=List[RecurringFailure])
async def get_recurring_failures(
    db: AsyncSession = Depends(get_db)
):
    """
    Identifies recurring failure patterns requiring at least 2 independent records.
    """
    service = ReliabilityIntelligenceService(db)
    return await service.get_recurring_failures()


@router.get("/subsystems", response_model=List[SubsystemReliabilityTrend])
async def get_subsystem_reliability(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns subsystem defect frequencies, verified resolution rates, and recurrence frequencies.
    """
    service = ReliabilityIntelligenceService(db)
    return await service.get_subsystem_reliability_trends()


@router.get("/signals", response_model=LearningSignalsResponse)
async def get_learning_signals(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns verified, evidence-grounded learning signals and operational observations.
    """
    service = LearningSignalsService(db)
    signals = await service.get_learning_signals()
    return {
        "total_signals": len(signals),
        "signals": signals
    }


@router.get("/trends")
async def get_historical_trends(
    trend_type: Optional[str] = Query(None, description="Optional trend type: RISK, ALERTS, MAINTENANCE, VERIFICATION, RECURRENCE"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns deterministic historical trend timelines from genuine database timestamps.
    """
    service = HistoricalTrendsService(db)
    return await service.get_historical_trends(trend_type=trend_type)


@router.get("/executive-summary", response_model=ExecutiveSummary)
async def get_executive_summary(
    db: AsyncSession = Depends(get_db)
):
    """
    Generates a read-only plant-level executive health and operational workload summary.
    """
    service = ExecutiveIntelligenceService(db)
    return await service.get_executive_summary()


@router.get("/overview", response_model=LearningOverviewResponse)
async def get_learning_overview(
    db: AsyncSession = Depends(get_db)
):
    """
    Returns the comprehensive Stage 10 executive overview with summary KPIs and learning signals.
    """
    exec_service = ExecutiveIntelligenceService(db)
    eff_service = MaintenanceEffectivenessService(db)
    rel_service = ReliabilityIntelligenceService(db)
    sig_service = LearningSignalsService(db)

    exec_summary = await exec_service.get_executive_summary()
    eff_res = await eff_service.get_maintenance_effectiveness()
    recurring = await rel_service.get_recurring_failures()
    signals = await sig_service.get_learning_signals()
    subsystems = await rel_service.get_subsystem_reliability_trends()

    return {
        "executive_summary": exec_summary,
        "effectiveness": eff_res["summary"],
        "recurring_count": len(recurring),
        "learning_signals_count": len(signals),
        "subsystems_monitored": len(subsystems),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
