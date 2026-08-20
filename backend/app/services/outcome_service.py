"""
backend/app/services/outcome_service.py

Maintenance Outcome (Ground-Truth Feedback) Service for FactoryMind AI.

Records actual maintenance findings against predictions, closing the
prediction → outcome ground-truth loop for model performance evaluation.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.maintenance_outcome import MaintenanceOutcome
from backend.app.models.work_order import WorkOrder
from backend.app.models.prediction import Prediction
import logging

logger = logging.getLogger("factorymind.outcomes")

VALID_OUTCOME_TYPES = {
    "NO_ISSUE_FOUND",
    "PREVENTIVE_MAINTENANCE",
    "CORRECTIVE_MAINTENANCE",
    "COMPONENT_REPLACED",
    "MACHINE_FAILURE",
    "FALSE_ALARM",
    "OTHER"
}


class OutcomeService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def get_outcome_by_work_order(self, work_order_id: int) -> Optional[MaintenanceOutcome]:
        stmt = select(MaintenanceOutcome).where(MaintenanceOutcome.work_order_id == work_order_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_outcomes_for_machine(self, machine_id: int) -> List[MaintenanceOutcome]:
        stmt = (
            select(MaintenanceOutcome)
            .where(MaintenanceOutcome.machine_id == machine_id)
            .order_by(MaintenanceOutcome.recorded_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_all_outcomes(self, limit: int = 200) -> List[MaintenanceOutcome]:
        stmt = select(MaintenanceOutcome).order_by(MaintenanceOutcome.recorded_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_retraining_candidates(self) -> List[MaintenanceOutcome]:
        """Returns outcomes flagged as useful for model retraining."""
        stmt = select(MaintenanceOutcome).where(MaintenanceOutcome.retraining_candidate == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # MODEL PERFORMANCE METRICS
    # -------------------------------------------------------------------------

    async def compute_model_performance(self) -> Dict[str, Any]:
        """
        Derives model performance metrics from recorded outcomes.
        Only uses outcomes where prediction_was_correct is set (not None).
        """
        stmt = select(MaintenanceOutcome).where(
            MaintenanceOutcome.prediction_was_correct.isnot(None)
        )
        result = await self.session.execute(stmt)
        assessed = result.scalars().all()

        total_assessed = len(assessed)
        if total_assessed == 0:
            return {
                "status": "NO_ASSESSMENTS",
                "message": "No outcomes with prediction accuracy assessment recorded yet.",
                "total_assessed": 0,
                "true_positives": 0,
                "false_alarms": 0,
                "missed_failures": 0,
                "precision": None,
                "recall": None,
                "false_alarm_rate": None
            }

        correct = sum(1 for o in assessed if o.prediction_was_correct is True)
        incorrect = total_assessed - correct

        false_alarms = sum(
            1 for o in assessed
            if o.outcome_type == "FALSE_ALARM"
        )
        machine_failures = sum(
            1 for o in assessed
            if o.outcome_type == "MACHINE_FAILURE" and o.prediction_was_correct is False
        )

        precision = round(correct / total_assessed, 3) if total_assessed > 0 else None
        false_alarm_rate = round(false_alarms / total_assessed, 3) if total_assessed > 0 else None

        # Outcome type breakdown
        type_breakdown: Dict[str, int] = {}
        for o in assessed:
            type_breakdown[o.outcome_type] = type_breakdown.get(o.outcome_type, 0) + 1

        return {
            "status": "AVAILABLE",
            "total_assessed": total_assessed,
            "correct_predictions": correct,
            "incorrect_predictions": incorrect,
            "false_alarms": false_alarms,
            "missed_failures": machine_failures,
            "precision": precision,
            "false_alarm_rate": false_alarm_rate,
            "outcome_type_breakdown": type_breakdown,
            "retraining_candidates": len(await self.get_retraining_candidates()),
            "computed_at": datetime.now(timezone.utc).isoformat()
        }

    # -------------------------------------------------------------------------
    # MUTATIONS
    # -------------------------------------------------------------------------

    async def record_outcome(
        self,
        work_order_id: int,
        machine_id: int,
        outcome_type: str,
        recorded_by: str,
        component_replaced: Optional[str] = None,
        actual_finding: Optional[str] = None,
        prediction_was_correct: Optional[bool] = None,
        false_alarm_reason: Optional[str] = None,
        retraining_candidate: bool = False,
        linked_prediction_id: Optional[int] = None,
        linked_alert_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> MaintenanceOutcome:
        """
        Records a maintenance outcome for a completed work order.

        Validates:
        - Work order must be in COMPLETED or VERIFIED state
        - No duplicate outcome per work order
        - outcome_type must be a valid value
        """
        outcome_type = outcome_type.upper()
        if outcome_type not in VALID_OUTCOME_TYPES:
            raise ValueError(
                f"Invalid outcome_type '{outcome_type}'. "
                f"Must be one of: {', '.join(sorted(VALID_OUTCOME_TYPES))}"
            )

        # Validate work order exists and is in a completable state
        wo_stmt = select(WorkOrder).where(WorkOrder.id == work_order_id)
        wo_result = await self.session.execute(wo_stmt)
        wo = wo_result.scalar_one_or_none()
        if not wo:
            raise ValueError(f"Work order ID {work_order_id} not found.")
        if wo.status not in ["COMPLETED", "VERIFICATION_REQUIRED", "VERIFIED"]:
            raise ValueError(
                f"Cannot record outcome for work order in status '{wo.status}'. "
                "Work order must be COMPLETED, VERIFICATION_REQUIRED, or VERIFIED."
            )

        # Check for duplicate
        existing = await self.get_outcome_by_work_order(work_order_id)
        if existing:
            raise ValueError(
                f"An outcome is already recorded for work order {work_order_id}. "
                "Use PATCH to update it."
            )

        outcome = MaintenanceOutcome(
            work_order_id=work_order_id,
            machine_id=machine_id,
            outcome_type=outcome_type,
            component_replaced=component_replaced,
            actual_finding=actual_finding,
            prediction_was_correct=prediction_was_correct,
            false_alarm_reason=false_alarm_reason,
            retraining_candidate=retraining_candidate,
            linked_prediction_id=linked_prediction_id,
            linked_alert_id=linked_alert_id,
            recorded_by=recorded_by,
            notes=notes
        )
        self.session.add(outcome)
        await self.session.flush()
        await self.session.refresh(outcome)
        logger.info(
            f"Recorded outcome '{outcome_type}' for WO {work_order_id} "
            f"(machine {machine_id}, recorded by {recorded_by})"
        )
        return outcome

    async def update_outcome(
        self,
        outcome_id: int,
        updates: Dict[str, Any]
    ) -> Optional[MaintenanceOutcome]:
        """Partial update — only applies non-None values from updates dict."""
        allowed_fields = {
            "outcome_type", "component_replaced", "actual_finding",
            "prediction_was_correct", "false_alarm_reason",
            "retraining_candidate", "notes"
        }
        safe_updates = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}

        if "outcome_type" in safe_updates:
            safe_updates["outcome_type"] = safe_updates["outcome_type"].upper()
            if safe_updates["outcome_type"] not in VALID_OUTCOME_TYPES:
                raise ValueError(f"Invalid outcome_type '{safe_updates['outcome_type']}'.")

        from sqlalchemy import update as sa_update
        await self.session.execute(
            sa_update(MaintenanceOutcome)
            .where(MaintenanceOutcome.id == outcome_id)
            .values(**safe_updates, updated_at=datetime.now(timezone.utc))
        )
        stmt = select(MaintenanceOutcome).where(MaintenanceOutcome.id == outcome_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
