"""
backend/app/services/storage_service.py

Asynchronous Storage & Repository Service for FactoryMind AI.
Provides clean abstraction for persisting and querying machines, telemetry, predictions, anomalies, alerts, and recommendations.
"""

from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Union
import numpy as np
from sqlalchemy import select, update, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.machine import Machine
from backend.app.models.telemetry import Telemetry
from backend.app.models.prediction import Prediction
from backend.app.models.anomaly import Anomaly
from backend.app.models.alert import Alert
from backend.app.models.recommendation import Recommendation
from backend.app.models.work_order import WorkOrder, WorkOrderAuditLog
from backend.app.schemas.work_order import WorkOrderStatus, WorkOrderPriority, VerificationStatus
from backend.app.services.maintenance_decision import (
    calculate_deterministic_priority,
    validate_lifecycle_transition
)


class StorageService:
    """
    Asynchronous data access and persistence layer.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # MACHINE OPERATIONS
    # -------------------------------------------------------------------------

    async def create_machine(
        self,
        unit_number: int,
        name: str,
        machine_type: str = "Turbofan Engine (CF6-80C2)",
        location: str = "Test Cell 1",
        status: str = "OPERATIONAL"
    ) -> Machine:
        """Creates a new machine entry in the registry."""
        machine = Machine(
            unit_number=unit_number,
            name=name,
            machine_type=machine_type,
            location=location,
            status=status,
            current_cycle=0
        )
        self.session.add(machine)
        await self.session.flush()
        await self.session.refresh(machine)
        return machine

    async def get_machine_by_id(self, machine_id: int) -> Optional[Machine]:
        """Retrieves a machine by primary key."""
        stmt = select(Machine).where(Machine.id == machine_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    get_machine = get_machine_by_id

    async def get_machine_by_unit(self, unit_number: int) -> Optional[Machine]:
        """Retrieves a machine by unit_number."""
        stmt = select(Machine).where(Machine.unit_number == unit_number)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_machines(self) -> List[Machine]:
        """Retrieves all registered machines ordered by unit_number."""
        stmt = select(Machine).order_by(Machine.unit_number)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_machine_status_and_cycle(
        self,
        machine_id: int,
        current_cycle: int,
        status: Optional[str] = None
    ) -> Optional[Machine]:
        """Updates current cycle, operational status, and marks telemetry freshness as CURRENT."""
        now = datetime.now(timezone.utc)
        values: Dict[str, Any] = {
            "current_cycle": current_cycle,
            "last_telemetry_at": now,
            "telemetry_state": "CURRENT"
        }
        if status:
            values["status"] = status

        stmt = (
            update(Machine)
            .where(Machine.id == machine_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)
        return await self.get_machine_by_id(machine_id)


    # -------------------------------------------------------------------------
    # TELEMETRY OPERATIONS
    # -------------------------------------------------------------------------

    async def insert_telemetry_single(self, machine_id: int, row_data: Dict[str, Any]) -> Telemetry:
        """Inserts a single cycle telemetry record."""
        sensor_kwargs = {f"s_{i}": float(row_data[f"s_{i}"]) for i in range(1, 22)}
        telemetry = Telemetry(
            machine_id=machine_id,
            cycle=int(row_data["time_cycle"] if "time_cycle" in row_data else row_data["cycle"]),
            setting_1=float(row_data.get("setting_1", 0.0)),
            setting_2=float(row_data.get("setting_2", 0.0)),
            setting_3=float(row_data.get("setting_3", 100.0)),
            **sensor_kwargs
        )
        self.session.add(telemetry)
        await self.session.flush()
        return telemetry

    async def insert_telemetry_batch(self, machine_id: int, records: List[Dict[str, Any]]) -> int:
        """Inserts multiple telemetry records in bulk."""
        objects = []
        for r in records:
            cycle_val = int(r["time_cycle"] if "time_cycle" in r else r["cycle"])
            sensor_kwargs = {f"s_{i}": float(r[f"s_{i}"]) for i in range(1, 22)}
            t = Telemetry(
                machine_id=machine_id,
                cycle=cycle_val,
                setting_1=float(r.get("setting_1", 0.0)),
                setting_2=float(r.get("setting_2", 0.0)),
                setting_3=float(r.get("setting_3", 100.0)),
                **sensor_kwargs
            )
            objects.append(t)

        self.session.add_all(objects)
        await self.session.flush()
        return len(objects)

    async def get_telemetry_history(
        self,
        machine_id: int,
        limit: int = 100,
        start_cycle: Optional[int] = None,
        end_cycle: Optional[int] = None
    ) -> List[Telemetry]:
        """Queries time-series telemetry records for a machine."""
        conditions = [Telemetry.machine_id == machine_id]
        if start_cycle is not None:
            conditions.append(Telemetry.cycle >= start_cycle)
        if end_cycle is not None:
            conditions.append(Telemetry.cycle <= end_cycle)

        stmt = (
            select(Telemetry)
            .where(and_(*conditions))
            .order_by(Telemetry.cycle.asc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # PREDICTIONS & ANOMALIES
    # -------------------------------------------------------------------------

    async def insert_prediction(self, machine_id: int, result: Dict[str, Any]) -> Prediction:
        """Persists real Stage 2 inference output including confidence and uncertainty metrics."""
        rul_val = float(result["rul_estimate"]) if result.get("rul_estimate") is not None else None
        prediction = Prediction(
            machine_id=machine_id,
            cycle=int(result["cycle"]),
            rul_estimate=rul_val,
            anomaly_score=float(result.get("anomaly_score", 0.0)),
            anomaly_status=str(result.get("anomaly_status", "NORMAL")),
            health_index=float(result.get("health_index", 100.0)),
            risk_score=float(result.get("risk_score", 0.0)),
            risk_level=str(result.get("risk_level", "NORMAL")),
            model_version=str(result.get("model_version", "LightGBM-v1.0")),
            contributing_signals=result.get("contributing_signals"),
            trends=result.get("trends"),
            confidence_level=result.get("confidence_level", "HIGH"),
            confidence_score=float(result.get("confidence_score", 0.95)) if result.get("confidence_score") is not None else None,
            out_of_distribution_sensors=result.get("out_of_distribution_sensors"),
            confidence_reason=result.get("confidence_reason")
        )
        self.session.add(prediction)
        await self.session.flush()
        await self.session.refresh(prediction)
        return prediction


    async def get_latest_prediction(self, machine_id: int) -> Optional[Prediction]:
        """Retrieves most recent prediction for a machine."""
        stmt = (
            select(Prediction)
            .where(Prediction.machine_id == machine_id)
            .order_by(Prediction.cycle.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_prediction_history(self, machine_id: int, limit: int = 100) -> List[Prediction]:
        """Retrieves prediction history ordered by cycle."""
        stmt = (
            select(Prediction)
            .where(Prediction.machine_id == machine_id)
            .order_by(Prediction.cycle.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def insert_anomaly(
        self,
        machine_id: int,
        cycle: int,
        anomaly_score: float,
        anomaly_status: str,
        raw_decision: float,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Anomaly:
        """Records an anomaly event detected by Isolation Forest."""
        anomaly = Anomaly(
            machine_id=machine_id,
            cycle=cycle,
            anomaly_score=anomaly_score,
            anomaly_status=anomaly_status,
            raw_decision=raw_decision,
            evidence=evidence
        )
        self.session.add(anomaly)
        await self.session.flush()
        await self.session.refresh(anomaly)
        return anomaly

    async def get_anomalies(self, machine_id: int, limit: int = 50) -> List[Anomaly]:
        """Retrieves recorded anomalies for a machine."""
        stmt = (
            select(Anomaly)
            .where(Anomaly.machine_id == machine_id)
            .order_by(Anomaly.cycle.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # ALERTS & RECOMMENDATIONS
    # -------------------------------------------------------------------------

    async def create_alert(
        self,
        machine_id: int,
        cycle: int,
        severity: str,
        risk_level: str,
        reason: str,
        evidence: Optional[Dict[str, Any]] = None
    ) -> Alert:
        """Creates an actionable degradation alarm."""
        alert = Alert(
            machine_id=machine_id,
            cycle=cycle,
            severity=severity,
            risk_level=risk_level,
            reason=reason,
            evidence=evidence,
            status="ACTIVE"
        )
        self.session.add(alert)
        await self.session.flush()
        await self.session.refresh(alert)
        return alert

    async def get_active_alerts(self, machine_id: Optional[int] = None) -> List[Alert]:
        """Retrieves active (unacknowledged/unresolved) alerts."""
        conditions = [Alert.status == "ACTIVE"]
        if machine_id is not None:
            conditions.append(Alert.machine_id == machine_id)

        stmt = select(Alert).where(and_(*conditions)).order_by(Alert.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_alert_history(self, machine_id: int, limit: int = 50) -> List[Alert]:
        """Retrieves alert history for an engine."""
        stmt = (
            select(Alert)
            .where(Alert.machine_id == machine_id)
            .order_by(Alert.cycle.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_alert(self, alert_id: int) -> Optional[Alert]:
        """Retrieves a single alert by ID."""
        stmt = select(Alert).where(Alert.id == alert_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def acknowledge_alert(self, alert_id: int) -> Optional[Alert]:
        """Acknowledges an active alert."""
        stmt = (
            update(Alert)
            .where(Alert.id == alert_id)
            .values(status="ACKNOWLEDGED", acknowledged_at=datetime.now(timezone.utc))
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(stmt)
        stmt_sel = select(Alert).where(Alert.id == alert_id)
        res = await self.session.execute(stmt_sel)
        return res.scalar_one_or_none()

    async def insert_recommendation(
        self,
        machine_id: int,
        recommendation_text: str,
        alert_id: Optional[int] = None,
        prediction_id: Optional[int] = None,
        source: str = "DETERMINISTIC_RULES",
        is_fallback: bool = False
    ) -> Recommendation:
        """Stores a maintenance prescription."""
        rec = Recommendation(
            machine_id=machine_id,
            alert_id=alert_id,
            prediction_id=prediction_id,
            recommendation_text=recommendation_text,
            source=source,
            is_fallback=is_fallback
        )
        self.session.add(rec)
        await self.session.flush()
        await self.session.refresh(rec)
        return rec

    async def get_recommendations(self, machine_id: int, limit: int = 10) -> List[Recommendation]:
        """Retrieves maintenance recommendations for a machine."""
        stmt = (
            select(Recommendation)
            .where(Recommendation.machine_id == machine_id)
            .order_by(Recommendation.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # STAGE 2 INTEGRATION PIPELINE
    # -------------------------------------------------------------------------

    async def persist_inference_cycle(
        self,
        machine_id: int,
        inference_result: Dict[str, Any]
    ) -> Tuple[Prediction, Optional[Anomaly], Optional[Alert]]:
        """
        Integrates Stage 2 inference result into persistent database records:
        1. Persists Prediction record.
        2. If anomaly detected, records Anomaly event.
        3. If Risk Level is non-normal or state changed, generates Alert.
        4. Updates Machine current_cycle and status.
        """
        cycle = int(inference_result["cycle"])
        risk_level = str(inference_result["risk_level"])
        anomaly_status = str(inference_result["anomaly_status"])

        # 1. Insert Prediction
        pred = await self.insert_prediction(machine_id, inference_result)

        # 2. Insert Anomaly if anomalous
        anomaly = None
        if anomaly_status == "ANOMALOUS":
            anomaly = await self.insert_anomaly(
                machine_id=machine_id,
                cycle=cycle,
                anomaly_score=float(inference_result["anomaly_score"]),
                anomaly_status=anomaly_status,
                raw_decision=float(inference_result.get("raw_decision_function", 0.0)),
                evidence={"contributing_signals": inference_result.get("contributing_signals")}
            )

        # 3. Create Alert if risk escalation / warning / critical
        alert = None
        if risk_level in ["MONITOR", "WARNING", "CRITICAL"] and inference_result.get("state_changed", False):
            severity_map = {
                "MONITOR": "LOW",
                "WARNING": "HIGH",
                "CRITICAL": "CRITICAL"
            }
            alert = await self.create_alert(
                machine_id=machine_id,
                cycle=cycle,
                severity=severity_map.get(risk_level, "MEDIUM"),
                risk_level=risk_level,
                reason=f"Turbofan degradation threshold reached: {risk_level} (RUL estimate: {inference_result['rul_estimate']} cycles, Health Index: {inference_result['health_index']}%)",
                evidence={"contributing_signals": inference_result.get("contributing_signals")}
            )

        # 4. Update machine current cycle
        machine_status_map = {
            "NORMAL": "OPERATIONAL",
            "MONITOR": "MONITORING",
            "WARNING": "DEGRADED",
            "CRITICAL": "CRITICAL"
        }
        await self.update_machine_status_and_cycle(
            machine_id=machine_id,
            current_cycle=cycle,
            status=machine_status_map.get(risk_level, "OPERATIONAL")
        )

        return pred, anomaly, alert

    # -------------------------------------------------------------------------
    # WORK ORDERS & CLOSED-LOOP MAINTENANCE (STAGE 8)
    # -------------------------------------------------------------------------

    async def create_work_order(
        self,
        machine_id: int,
        title: str,
        recommended_action: str,
        affected_subsystem: str = "Turbofan Core",
        priority: Optional[str] = None,
        risk_level: Optional[str] = None,
        description: Optional[str] = None,
        source_alert_id: Optional[int] = None,
        source_recommendation_id: Optional[int] = None,
        observed_evidence: Optional[Dict[str, Any]] = None,
        ml_evidence: Optional[Dict[str, Any]] = None,
        assigned_to: Optional[str] = "Unassigned",
        data_source: Optional[str] = "NASA C-MAPSS FD001 — Simulation",
        due_days: Optional[int] = 7,
        actor: str = "Operator"
    ) -> WorkOrder:
        """
        Creates an actionable maintenance work order with deterministic priority calculation.
        """
        # If priority not specified, calculate deterministically from evidence
        if not priority:
            rul_val = ml_evidence.get("rul_estimate") if ml_evidence else None
            anom_val = ml_evidence.get("anomaly_score") if ml_evidence else None
            calc_priority = calculate_deterministic_priority(
                risk_level=risk_level,
                rul_estimate=float(rul_val) if rul_val is not None else None,
                anomaly_score=float(anom_val) if anom_val is not None else None,
                alert_severity=risk_level
            )
            priority = calc_priority.value
        else:
            priority = priority.upper()

        # Generate unique work order code
        count_stmt = select(func.count(WorkOrder.id))
        res = await self.session.execute(count_stmt)
        total_existing = res.scalar() or 0
        code = f"WO-{(total_existing + 1):04d}"

        from datetime import timedelta
        due_at = datetime.now(timezone.utc) + timedelta(days=due_days or 7)

        initial_status = WorkOrderStatus.OPEN.value

        wo = WorkOrder(
            work_order_code=code,
            machine_id=machine_id,
            source_alert_id=source_alert_id,
            source_recommendation_id=source_recommendation_id,
            priority=priority,
            risk_level=risk_level or "MONITOR",
            title=title,
            description=description or f"Prescriptive maintenance generated for machine #{machine_id}",
            observed_evidence=observed_evidence,
            ml_evidence=ml_evidence,
            recommended_action=recommended_action,
            affected_subsystem=affected_subsystem,
            assigned_to=assigned_to or "Unassigned",
            status=initial_status,
            data_source=data_source or "NASA C-MAPSS FD001 — Simulation",
            due_at=due_at
        )
        self.session.add(wo)
        await self.session.flush()
        await self.session.refresh(wo)

        # Record initial creation audit log
        audit = WorkOrderAuditLog(
            work_order_id=wo.id,
            event_type="CREATED",
            actor=actor,
            old_status=None,
            new_status=initial_status,
            notes=f"Work order created with priority {priority}",
            details={"priority": priority, "action": recommended_action}
        )
        self.session.add(audit)
        await self.session.flush()
        await self.session.refresh(wo)
        return wo

    async def get_work_order(self, work_order_id: int) -> Optional[WorkOrder]:
        """Retrieves a work order with eager audit logs."""
        from sqlalchemy.orm import selectinload
        stmt = (
            select(WorkOrder)
            .options(selectinload(WorkOrder.audit_logs))
            .where(WorkOrder.id == work_order_id)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_work_orders(
        self,
        status: Optional[str] = None,
        machine_id: Optional[int] = None,
        priority: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[WorkOrder]:
        """Lists work orders with optional filtering."""
        from sqlalchemy.orm import selectinload
        conditions = []
        if status:
            conditions.append(WorkOrder.status == status.upper())
        if machine_id:
            conditions.append(WorkOrder.machine_id == machine_id)
        if priority:
            conditions.append(WorkOrder.priority == priority.upper())

        stmt = (
            select(WorkOrder)
            .options(selectinload(WorkOrder.audit_logs))
            .order_by(WorkOrder.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if conditions:
            stmt = stmt.where(and_(*conditions))

        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def assign_work_order(
        self,
        work_order_id: int,
        assigned_to: str,
        actor: str = "Supervisor",
        notes: Optional[str] = None
    ) -> WorkOrder:
        """Assigns a work order to a technician and advances status to ASSIGNED."""
        wo = await self.get_work_order(work_order_id)
        if not wo:
            raise ValueError(f"Work order {work_order_id} not found")

        curr_enum = WorkOrderStatus(wo.status)
        target_enum = WorkOrderStatus.ASSIGNED
        valid, err = validate_lifecycle_transition(curr_enum, target_enum)
        if not valid:
            raise ValueError(err)

        old_status = wo.status
        wo.assigned_to = assigned_to
        wo.status = target_enum.value
        wo.updated_at = datetime.now(timezone.utc)

        audit = WorkOrderAuditLog(
            work_order_id=wo.id,
            event_type="ASSIGNED",
            actor=actor,
            old_status=old_status,
            new_status=wo.status,
            notes=notes or f"Assigned to {assigned_to}",
            details={"assigned_to": assigned_to}
        )
        self.session.add(audit)
        await self.session.flush()
        await self.session.refresh(wo)
        return wo

    async def start_work_order(
        self,
        work_order_id: int,
        actor: str = "Technician",
        notes: Optional[str] = None
    ) -> WorkOrder:
        """Marks maintenance work as IN_PROGRESS and records started_at timestamp."""
        wo = await self.get_work_order(work_order_id)
        if not wo:
            raise ValueError(f"Work order {work_order_id} not found")

        curr_enum = WorkOrderStatus(wo.status)
        target_enum = WorkOrderStatus.IN_PROGRESS
        valid, err = validate_lifecycle_transition(curr_enum, target_enum)
        if not valid:
            raise ValueError(err)

        old_status = wo.status
        wo.status = target_enum.value
        wo.started_at = datetime.now(timezone.utc)
        wo.updated_at = datetime.now(timezone.utc)

        audit = WorkOrderAuditLog(
            work_order_id=wo.id,
            event_type="STARTED",
            actor=actor,
            old_status=old_status,
            new_status=wo.status,
            notes=notes or "Maintenance operation started in field/cell"
        )
        self.session.add(audit)
        await self.session.flush()
        await self.session.refresh(wo)
        return wo

    async def complete_work_order(
        self,
        work_order_id: int,
        actor: str = "Technician",
        notes: Optional[str] = None
    ) -> WorkOrder:
        """
        Marks maintenance work as finished, automatically setting status to VERIFICATION_REQUIRED.
        Does NOT automatically declare the machine repaired.
        """
        wo = await self.get_work_order(work_order_id)
        if not wo:
            raise ValueError(f"Work order {work_order_id} not found")

        curr_enum = WorkOrderStatus(wo.status)
        target_enum = WorkOrderStatus.VERIFICATION_REQUIRED
        valid, err = validate_lifecycle_transition(curr_enum, target_enum)
        if not valid:
            raise ValueError(err)

        old_status = wo.status
        wo.status = target_enum.value
        wo.completed_at = datetime.now(timezone.utc)
        wo.verification_status = VerificationStatus.PENDING.value
        wo.updated_at = datetime.now(timezone.utc)

        audit = WorkOrderAuditLog(
            work_order_id=wo.id,
            event_type="COMPLETED",
            actor=actor,
            old_status=old_status,
            new_status=wo.status,
            notes=notes or "Maintenance procedure completed; pending post-maintenance telemetry verification."
        )
        self.session.add(audit)
        await self.session.flush()
        await self.session.refresh(wo)
        return wo

    async def verify_work_order(
        self,
        work_order_id: int,
        verification_status: str,
        verification_notes: Optional[str] = None,
        actor: str = "Lead Engineer"
    ) -> WorkOrder:
        """
        Records human / sensor verification outcome and marks work order as VERIFIED.
        Outcome must be one of: RESOLVED, NOT_RESOLVED, PARTIALLY_RESOLVED, UNABLE_TO_VERIFY.
        """
        wo = await self.get_work_order(work_order_id)
        if not wo:
            raise ValueError(f"Work order {work_order_id} not found")

        curr_enum = WorkOrderStatus(wo.status)
        target_enum = WorkOrderStatus.VERIFIED
        valid, err = validate_lifecycle_transition(curr_enum, target_enum)
        if not valid:
            raise ValueError(err)

        clean_outcome = verification_status.upper()
        if clean_outcome not in [v.value for v in VerificationStatus]:
            raise ValueError(f"Invalid verification outcome: {verification_status}")

        old_status = wo.status
        wo.status = target_enum.value
        wo.verification_status = clean_outcome
        wo.verification_notes = verification_notes
        wo.verified_at = datetime.now(timezone.utc)
        wo.updated_at = datetime.now(timezone.utc)

        audit = WorkOrderAuditLog(
            work_order_id=wo.id,
            event_type="VERIFIED",
            actor=actor,
            old_status=old_status,
            new_status=wo.status,
            notes=f"Verification completed with outcome: {clean_outcome}. {verification_notes or ''}",
            details={"verification_status": clean_outcome, "notes": verification_notes}
        )
        self.session.add(audit)
        await self.session.flush()
        await self.session.refresh(wo)
        return wo

    async def get_work_orders_summary(self) -> Dict[str, int]:
        """Calculates real backend operational work order statistics."""
        stmt = select(WorkOrder.status, WorkOrder.priority)
        res = await self.session.execute(stmt)
        rows = res.all()

        total = len(rows)
        open_c = sum(1 for s, _ in rows if s in ["OPEN", "RECOMMENDED"])
        assigned_c = sum(1 for s, _ in rows if s == "ASSIGNED")
        in_prog_c = sum(1 for s, _ in rows if s == "IN_PROGRESS")
        completed_c = sum(1 for s, _ in rows if s in ["COMPLETED", "VERIFICATION_REQUIRED"])
        verif_req_c = sum(1 for s, _ in rows if s == "VERIFICATION_REQUIRED")
        verified_c = sum(1 for s, _ in rows if s == "VERIFIED")
        high_p_c = sum(1 for _, p in rows if p in ["CRITICAL", "HIGH"])

        return {
            "total_work_orders": total,
            "open_count": open_c,
            "assigned_count": assigned_c,
            "in_progress_count": in_prog_c,
            "completed_count": completed_c,
            "verification_required_count": verif_req_c,
            "verified_count": verified_c,
            "high_priority_count": high_p_c
        }

    async def get_post_maintenance_comparison(self, work_order_id: int) -> Dict[str, Any]:
        """
        Computes genuine before vs after maintenance prognostic metrics.
        Never invents or fabricates improvement if post-maintenance telemetry is unavailable.
        """
        wo = await self.get_work_order(work_order_id)
        if not wo:
            raise ValueError(f"Work order {work_order_id} not found")

        # Before baseline from ml_evidence
        before_data = {
            "risk_level": wo.risk_level,
            "priority": wo.priority,
            "observed_at": wo.created_at.isoformat() if wo.created_at else None,
            "rul_estimate": wo.ml_evidence.get("rul_estimate") if wo.ml_evidence else None,
            "health_index": wo.ml_evidence.get("health_index") if wo.ml_evidence else None,
            "anomaly_score": wo.ml_evidence.get("anomaly_score") if wo.ml_evidence else None
        }

        # Check if completed and if newer predictions exist
        if not wo.completed_at:
            return {
                "work_order_id": wo.id,
                "has_post_maintenance_data": False,
                "message": "Post-maintenance verification data unavailable (maintenance not yet completed).",
                "before": before_data,
                "after": None
            }

        latest_pred = await self.get_latest_prediction(wo.machine_id)
        if not latest_pred:
            return {
                "work_order_id": wo.id,
                "has_post_maintenance_data": False,
                "message": "Post-maintenance verification data unavailable.",
                "before": before_data,
                "after": None
            }

        after_data = {
            "cycle": latest_pred.cycle,
            "risk_level": latest_pred.risk_level,
            "rul_estimate": float(latest_pred.rul_estimate) if latest_pred.rul_estimate is not None else None,
            "health_index": float(latest_pred.health_index) if latest_pred.health_index is not None else None,
            "anomaly_score": float(latest_pred.anomaly_score) if latest_pred.anomaly_score is not None else None,
            "recorded_at": latest_pred.created_at.isoformat() if latest_pred.created_at else None
        }

        return {
            "work_order_id": wo.id,
            "has_post_maintenance_data": True,
            "message": "Verified post-maintenance telemetry available.",
            "before": before_data,
            "after": after_data
        }

