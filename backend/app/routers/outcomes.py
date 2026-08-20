"""
backend/app/routers/outcomes.py

Maintenance Outcome (Ground-Truth Feedback) Router for FactoryMind AI.

Records actual maintenance findings and derives model performance metrics.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.app.database import get_db
from backend.app.security import AuthUser, require_role
from backend.app.services.outcome_service import OutcomeService

router = APIRouter(prefix="/outcomes", tags=["Maintenance Outcomes"])

require_operator = require_role(["admin", "operator"])
require_viewer = require_role(["admin", "operator", "viewer"])


class RecordOutcomeRequest(BaseModel):
    work_order_id: int
    machine_id: int
    outcome_type: str = Field(
        description="NO_ISSUE_FOUND | PREVENTIVE_MAINTENANCE | CORRECTIVE_MAINTENANCE | "
                    "COMPONENT_REPLACED | MACHINE_FAILURE | FALSE_ALARM | OTHER"
    )
    recorded_by: str = Field(description="Operator/technician recording the outcome")
    component_replaced: Optional[str] = None
    actual_finding: Optional[str] = None
    prediction_was_correct: Optional[bool] = Field(
        default=None,
        description="True if the prediction that triggered this WO was accurate; False if false alarm/missed"
    )
    false_alarm_reason: Optional[str] = None
    retraining_candidate: bool = Field(
        default=False,
        description="Flag this outcome as useful for next model retraining"
    )
    linked_prediction_id: Optional[int] = None
    linked_alert_id: Optional[int] = None
    notes: Optional[str] = None


class UpdateOutcomeRequest(BaseModel):
    outcome_type: Optional[str] = None
    component_replaced: Optional[str] = None
    actual_finding: Optional[str] = None
    prediction_was_correct: Optional[bool] = None
    false_alarm_reason: Optional[str] = None
    retraining_candidate: Optional[bool] = None
    notes: Optional[str] = None


@router.get("", response_model=List[dict])
async def list_outcomes(
    limit: int = Query(default=50, ge=1, le=500),
    user: AuthUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    """Returns recorded maintenance outcomes, newest first."""
    svc = OutcomeService(db)
    outcomes = await svc.get_all_outcomes(limit=limit)
    return [o.to_dict() for o in outcomes]


@router.get("/machine/{machine_id}", response_model=List[dict])
async def list_machine_outcomes(
    machine_id: int,
    user: AuthUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    """Returns all outcomes for a specific machine."""
    svc = OutcomeService(db)
    outcomes = await svc.get_outcomes_for_machine(machine_id)
    return [o.to_dict() for o in outcomes]


@router.get("/performance", response_model=Dict[str, Any])
async def get_model_performance(
    user: AuthUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns fleet-wide model performance metrics derived from ground-truth outcomes:
    precision, false alarm rate, outcome type breakdown, retraining candidates.
    """
    svc = OutcomeService(db)
    return await svc.compute_model_performance()


@router.get("/retraining-candidates", response_model=List[dict])
async def get_retraining_candidates(
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Returns outcomes flagged as candidates for inclusion in next model retraining dataset."""
    svc = OutcomeService(db)
    candidates = await svc.get_retraining_candidates()
    return [c.to_dict() for c in candidates]


@router.get("/work-order/{work_order_id}", response_model=Optional[dict])
async def get_outcome_by_work_order(
    work_order_id: int,
    user: AuthUser = Depends(require_viewer),
    db: AsyncSession = Depends(get_db)
):
    """Returns the outcome recorded for a specific work order, if any."""
    svc = OutcomeService(db)
    outcome = await svc.get_outcome_by_work_order(work_order_id)
    if not outcome:
        return None
    return outcome.to_dict()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def record_outcome(
    payload: RecordOutcomeRequest,
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """
    Records a maintenance outcome against a completed work order.
    Validates work order state and prevents duplicate outcomes.
    Requires OPERATOR or higher authorization.
    """
    svc = OutcomeService(db)
    try:
        outcome = await svc.record_outcome(
            work_order_id=payload.work_order_id,
            machine_id=payload.machine_id,
            outcome_type=payload.outcome_type,
            recorded_by=payload.recorded_by or user.username,
            component_replaced=payload.component_replaced,
            actual_finding=payload.actual_finding,
            prediction_was_correct=payload.prediction_was_correct,
            false_alarm_reason=payload.false_alarm_reason,
            retraining_candidate=payload.retraining_candidate,
            linked_prediction_id=payload.linked_prediction_id,
            linked_alert_id=payload.linked_alert_id,
            notes=payload.notes
        )
        await db.commit()
        return outcome.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{outcome_id}", response_model=dict)
async def update_outcome(
    outcome_id: int,
    payload: UpdateOutcomeRequest,
    user: AuthUser = Depends(require_operator),
    db: AsyncSession = Depends(get_db)
):
    """Updates an existing outcome record (partial update)."""
    svc = OutcomeService(db)
    try:
        outcome = await svc.update_outcome(outcome_id, payload.model_dump(exclude_unset=True))
        if not outcome:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Outcome {outcome_id} not found.")
        await db.commit()
        return outcome.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
