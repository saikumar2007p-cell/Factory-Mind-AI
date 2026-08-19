"""
backend/app/services/reliability_intelligence.py

Stage 10 Recurring Failure & Subsystem Reliability Intelligence Service.
Identifies deterministic failure patterns, repeat interventions, and machine maintenance histories.
Enforces a transparent >=2 event evidence threshold for recurring issue classification.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from backend.app.models.work_order import WorkOrder
from backend.app.models.machine import Machine
from backend.app.models.alert import Alert
from backend.app.models.prediction import Prediction
from backend.app.services.storage_service import StorageService


class ReliabilityIntelligenceService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.storage = StorageService(session)

    async def get_recurring_failures(self) -> List[Dict[str, Any]]:
        """
        Identifies recurring failure patterns across machines and subsystems.
        Requires at least 2 independent records to classify as a recurring issue.
        """
        all_wos = await self.storage.list_work_orders()
        machines = await self.storage.get_all_machines()
        machine_map = {m.id: m for m in machines}

        # Group work orders by (machine_id, subsystem)
        grouped_wos: Dict[tuple, List[WorkOrder]] = {}
        for w in all_wos:
            sub = w.affected_subsystem or "Turbofan Core"
            key = (w.machine_id, sub)
            if key not in grouped_wos:
                grouped_wos[key] = []
            grouped_wos[key].append(w)

        # Also get all alerts
        stmt_alerts = select(Alert)
        res_alerts = await self.session.execute(stmt_alerts)
        alerts = res_alerts.scalars().all()
        grouped_alerts: Dict[int, List[Alert]] = {}
        for a in alerts:
            if a.machine_id not in grouped_alerts:
                grouped_alerts[a.machine_id] = []
            grouped_alerts[a.machine_id].append(a)

        recurring_list = []

        # Analyze machines with >=2 work orders or multiple critical alerts
        for (m_id, sub), w_list in grouped_wos.items():
            m = machine_map.get(m_id)
            if not m:
                continue

            m_alerts = grouped_alerts.get(m_id, [])
            total_wo_count = len(w_list)
            total_alert_count = len(m_alerts)

            v_outcomes = {
                "RESOLVED": 0,
                "PARTIALLY_RESOLVED": 0,
                "NOT_RESOLVED": 0,
                "UNABLE_TO_VERIFY": 0,
                "PENDING": 0
            }
            for w in w_list:
                v_stat = (w.verification_status or "PENDING").upper()
                v_outcomes[v_stat] = v_outcomes.get(v_stat, 0) + 1

            unresolved_c = v_outcomes.get("NOT_RESOLVED", 0) + v_outcomes.get("PARTIALLY_RESOLVED", 0)

            # Strict >=2 evidence threshold
            if total_wo_count >= 2:
                if unresolved_c > 0:
                    status = "RECURRING_FAILURE"
                    evidence_level = "HIGH EVIDENCE" if total_wo_count >= 3 else "MODERATE EVIDENCE"
                    pattern = f"Repeated unresolved defect in {sub} across {total_wo_count} work orders."
                    explanation = f"Machine #{m.unit_number} has generated {total_wo_count} work orders targeting {sub} with {unresolved_c} non-resolved or partial outcomes."
                else:
                    status = "REPEATED_INTERVENTION"
                    evidence_level = "MODERATE EVIDENCE" if total_wo_count >= 2 else "LOW EVIDENCE"
                    pattern = f"Multiple maintenance interventions on {sub}."
                    explanation = f"Machine #{m.unit_number} has undergone {total_wo_count} maintenance procedures for {sub}."

                recurring_list.append({
                    "machine_id": m.id,
                    "unit_number": m.unit_number,
                    "machine_name": m.name,
                    "subsystem": sub,
                    "issue_pattern": pattern,
                    "alert_count": total_alert_count,
                    "work_order_count": total_wo_count,
                    "repeated_interventions": total_wo_count,
                    "verification_outcomes": v_outcomes,
                    "evidence_level": evidence_level,
                    "status": status,
                    "explanation": explanation,
                    "source_work_order_ids": [w.id for w in w_list]
                })

        return recurring_list

    async def get_machine_maintenance_history(self, machine_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieves full verified maintenance history and operational metrics for machines.
        """
        if machine_id:
            m_obj = await self.storage.get_machine(machine_id)
            machines = [m_obj] if m_obj else []
        else:
            machines = await self.storage.get_all_machines()

        all_wos = await self.storage.list_work_orders()
        wos_by_machine: Dict[int, List[WorkOrder]] = {}
        for w in all_wos:
            if w.machine_id not in wos_by_machine:
                wos_by_machine[w.machine_id] = []
            wos_by_machine[w.machine_id].append(w)

        history_list = []
        for m in machines:
            m_wos = wos_by_machine.get(m.id, [])
            latest_pred = await self.storage.get_latest_prediction(m.id)

            total_maint = len(m_wos)
            completed_c = sum(1 for w in m_wos if w.status in ["COMPLETED", "VERIFICATION_REQUIRED", "VERIFIED"])
            verified_c = sum(1 for w in m_wos if w.status == "VERIFIED")
            resolved_c = sum(1 for w in m_wos if (w.verification_status or "").upper() == "RESOLVED")
            unresolved_c = sum(1 for w in m_wos if (w.verification_status or "").upper() in ["NOT_RESOLVED", "PARTIALLY_RESOLVED"])

            latest_wo = m_wos[-1] if m_wos else None
            latest_status = latest_wo.status if latest_wo else "NO_MAINTENANCE"
            latest_verif = latest_wo.verification_status if latest_wo else None

            # Subsystems affected
            subs = list(set(w.affected_subsystem for w in m_wos if w.affected_subsystem))

            # Historical effectiveness
            if verified_c == 0:
                hist_eff = "UNAVAILABLE"
            elif resolved_c == verified_c:
                hist_eff = "HIGH_SUCCESS"
            elif resolved_c > 0:
                hist_eff = "MODERATE_SUCCESS"
            else:
                hist_eff = "LOW_SUCCESS"

            # Recurring issue status
            if total_maint >= 2 and unresolved_c > 0:
                rec_status = "RECURRING_FAILURE"
            elif total_maint >= 2:
                rec_status = "REPEATED_INTERVENTION"
            elif total_maint == 1:
                rec_status = "SINGLE_EVENT"
            else:
                rec_status = "STABLE"

            # ML Compatibility & RUL
            ml_compat = "COMPATIBLE"
            rul_avail = False
            rul_val = None
            if latest_pred:
                rul_val = float(latest_pred.rul_estimate) if latest_pred.rul_estimate is not None else None
                rul_avail = rul_val is not None
                if "Incompatible" in (latest_pred.model_version or "") or rul_val is None:
                    ml_compat = "INCOMPATIBLE"

            data_qual = "STALE" if m.status == "OFFLINE" else ("OPTIMAL" if latest_pred else "MISSING")

            history_list.append({
                "machine_id": m.id,
                "unit_number": m.unit_number,
                "name": m.name,
                "maintenance_count": total_maint,
                "completed_count": completed_c,
                "verified_count": verified_c,
                "resolved_count": resolved_c,
                "unresolved_count": unresolved_c,
                "repeat_intervention_count": max(0, total_maint - 1),
                "latest_maintenance_status": latest_status,
                "latest_verification_result": latest_verif,
                "historical_effectiveness": hist_eff,
                "recurring_issue_status": rec_status,
                "affected_subsystems": subs,
                "data_quality": data_qual,
                "ml_compatibility": ml_compat,
                "rul_available": rul_avail,
                "rul_estimate": rul_val
            })

        return history_list

    async def get_subsystem_reliability_trends(self) -> List[Dict[str, Any]]:
        """
        Calculates reliability, defect recurrence, and verification outcomes per subsystem.
        """
        all_wos = await self.storage.list_work_orders()
        stmt_alerts = select(Alert)
        res_alerts = await self.session.execute(stmt_alerts)
        all_alerts = res_alerts.scalars().all()

        standard_subsystems = [
            "High Pressure Compressor (HPC)",
            "Low Pressure Turbine (LPT)",
            "High Pressure Turbine (HPT)",
            "Combustor",
            "Bleed Air System",
            "Fan Module",
            "Turbofan Core"
        ]

        subsystem_data = {s: {
            "subsystem": s,
            "alert_count": 0,
            "critical_alert_count": 0,
            "work_order_count": 0,
            "verified_resolutions": 0,
            "repeat_interventions": 0,
            "unresolved_maintenance": 0,
            "recurrence_frequency": 0.0,
            "evidence_level": "INSUFFICIENT DATA",
            "status_label": "HEALTHY"
        } for s in standard_subsystems}

        for a in all_alerts:
            # Match subsystem if known or fallback
            sub = "Turbofan Core"
            for s in standard_subsystems:
                if s.lower() in (a.reason or "").lower():
                    sub = s
                    break
            if sub in subsystem_data:
                subsystem_data[sub]["alert_count"] += 1
                if (a.severity or "").upper() == "CRITICAL":
                    subsystem_data[sub]["critical_alert_count"] += 1

        # Track repeat interventions per machine per subsystem
        machine_sub_wos: Dict[str, Dict[int, int]] = {s: {} for s in standard_subsystems}

        for w in all_wos:
            sub = w.affected_subsystem or "Turbofan Core"
            if sub not in subsystem_data:
                subsystem_data[sub] = {
                    "subsystem": sub,
                    "alert_count": 0,
                    "critical_alert_count": 0,
                    "work_order_count": 0,
                    "verified_resolutions": 0,
                    "repeat_interventions": 0,
                    "unresolved_maintenance": 0,
                    "recurrence_frequency": 0.0,
                    "evidence_level": "INSUFFICIENT DATA",
                    "status_label": "HEALTHY"
                }
                machine_sub_wos[sub] = {}

            subsystem_data[sub]["work_order_count"] += 1
            machine_sub_wos[sub][w.machine_id] = machine_sub_wos[sub].get(w.machine_id, 0) + 1

            if w.status == "VERIFIED":
                v_stat = (w.verification_status or "").upper()
                if v_stat == "RESOLVED":
                    subsystem_data[sub]["verified_resolutions"] += 1
                elif v_stat in ["NOT_RESOLVED", "PARTIALLY_RESOLVED"]:
                    subsystem_data[sub]["unresolved_maintenance"] += 1

        for sub, data in subsystem_data.items():
            # Repeat interventions count
            repeats = sum(1 for m_id, count in machine_sub_wos.get(sub, {}).items() if count >= 2)
            data["repeat_interventions"] = repeats

            total_events = data["alert_count"] + data["work_order_count"]
            if total_events >= 10:
                data["evidence_level"] = "HIGH EVIDENCE"
            elif total_events >= 3:
                data["evidence_level"] = "MODERATE EVIDENCE"
            elif total_events >= 1:
                data["evidence_level"] = "LOW EVIDENCE"
            else:
                data["evidence_level"] = "INSUFFICIENT DATA"

            # Recurrence frequency
            if data["work_order_count"] > 0:
                data["recurrence_frequency"] = round((repeats / data["work_order_count"]), 2)

            # Status label
            if data["unresolved_maintenance"] >= 2 or data["critical_alert_count"] >= 5:
                data["status_label"] = "HIGH_DEGRADATION"
            elif data["work_order_count"] > 0 or data["alert_count"] > 0:
                data["status_label"] = "MONITORED"
            else:
                data["status_label"] = "HEALTHY"

        return list(subsystem_data.values())
