"""
backend/app/services/fleet_intelligence.py

Fleet Intelligence Analytics Service for FactoryMind AI.
Aggregates existing verified records across Machine, Telemetry, Prediction, Alert,
Recommendation, and WorkOrder without creating secondary tables or fabricated data.
"""

from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.models.machine import Machine
from backend.app.models.telemetry import Telemetry
from backend.app.models.prediction import Prediction
from backend.app.models.alert import Alert
from backend.app.models.work_order import WorkOrder, WorkOrderAuditLog
from backend.app.services.storage_service import StorageService


KNOWN_SUBSYSTEMS = [
    "High Pressure Compressor (HPC)",
    "Low Pressure Turbine (LPT)",
    "High Pressure Turbine (HPT)",
    "Combustor",
    "Fan & Booster",
    "Turbofan Core"
]


class FleetIntelligenceService:
    """
    Deterministic Fleet Intelligence engine.
    Aggregates authentic database records to provide fleet-wide visibility.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.storage = StorageService(session)

    async def _get_all_latest_predictions(self) -> Dict[int, Prediction]:
        """Bulk fetches the single latest prediction for all machines in 1 query."""
        subq = (
            select(
                Prediction.machine_id,
                func.max(Prediction.id).label("max_id")
            )
            .group_by(Prediction.machine_id)
            .subquery()
        )
        stmt = select(Prediction).join(
            subq,
            and_(
                Prediction.machine_id == subq.c.machine_id,
                Prediction.id == subq.c.max_id
            )
        )
        res = await self.session.execute(stmt)
        preds = res.scalars().all()
        return {p.machine_id: p for p in preds}

    async def _get_all_active_alerts_map(self) -> Dict[int, List[Alert]]:
        """Bulk fetches active alerts for all machines in 1 query."""
        stmt = select(Alert).where(Alert.is_acknowledged == False)
        res = await self.session.execute(stmt)
        alerts = res.scalars().all()
        alert_map: Dict[int, List[Alert]] = {}
        for a in alerts:
            alert_map.setdefault(a.machine_id, []).append(a)
        return alert_map

    async def _get_all_active_work_orders_map(self) -> Dict[int, WorkOrder]:
        """Bulk fetches active work orders for all machines in 1 query."""
        stmt = (
            select(WorkOrder)
            .where(
                WorkOrder.status.in_(["OPEN", "RECOMMENDED", "ASSIGNED", "IN_PROGRESS", "VERIFICATION_REQUIRED"])
            )
            .order_by(WorkOrder.created_at.desc(), WorkOrder.id.desc())
        )
        res = await self.session.execute(stmt)
        wos = res.scalars().all()
        wo_map: Dict[int, WorkOrder] = {}
        for wo in wos:
            if wo.machine_id not in wo_map:
                wo_map[wo.machine_id] = wo
        return wo_map

    async def get_fleet_summary(self) -> Dict[str, Any]:
        """
        Calculates fleet-level summary metrics from actual database records.
        Distinguishes NORMAL, WARNING, CRITICAL, STALE, MISSING, and UNKNOWN.
        """
        machines = await self.storage.get_all_machines()
        if not machines:
            return {
                "total_machines": 0,
                "healthy_count": 0,
                "warning_count": 0,
                "critical_count": 0,
                "stale_count": 0,
                "missing_data_count": 0,
                "unknown_count": 0,
                "ml_compatible_count": 0,
                "ml_incompatible_count": 0,
                "rul_available_count": 0,
                "rul_unavailable_count": 0,
                "active_work_orders": 0,
                "verification_required_count": 0,
                "data_source": "NASA C-MAPSS FD001 — Simulation",
                "real_industrial_configured": False
            }

        preds_map = await self._get_all_latest_predictions()

        healthy_c = 0
        warning_c = 0
        critical_c = 0
        stale_c = 0
        missing_c = 0
        unknown_c = 0

        rul_avail_c = 0
        rul_unavail_c = 0
        ml_comp_c = 0
        ml_incomp_c = 0

        for m in machines:
            latest_pred = preds_map.get(m.id)
            
            # Telemetry status check
            if m.status == "OFFLINE":
                stale_c += 1
            elif m.current_cycle == 0 and not latest_pred:
                missing_c += 1
            elif latest_pred:
                if latest_pred.risk_level == "CRITICAL":
                    critical_c += 1
                elif latest_pred.risk_level in ["WARNING", "MONITOR"]:
                    warning_c += 1
                elif latest_pred.risk_level == "NORMAL":
                    healthy_c += 1
                else:
                    unknown_c += 1
            else:
                unknown_c += 1

            # ML Compatibility & RUL availability
            if latest_pred and latest_pred.rul_estimate is not None:
                rul_avail_c += 1
                ml_comp_c += 1
            elif latest_pred and latest_pred.rul_estimate is None:
                rul_unavail_c += 1
                ml_incomp_c += 1
            else:
                # Default baseline for C-MAPSS simulation machines
                rul_unavail_c += 1
                ml_comp_c += 1

        # Work order metrics from actual Stage 8 database
        wo_summary = await self.storage.get_work_orders_summary()
        active_wos = (
            wo_summary.get("open_count", 0) +
            wo_summary.get("assigned_count", 0) +
            wo_summary.get("in_progress_count", 0) +
            wo_summary.get("verification_required_count", 0)
        )
        verif_req = wo_summary.get("verification_required_count", 0)

        return {
            "total_machines": len(machines),
            "healthy_count": healthy_c,
            "warning_count": warning_c,
            "critical_count": critical_c,
            "stale_count": stale_c,
            "missing_data_count": missing_c,
            "unknown_count": unknown_c,
            "ml_compatible_count": ml_comp_c,
            "ml_incompatible_count": ml_incomp_c,
            "rul_available_count": rul_avail_c,
            "rul_unavailable_count": rul_unavail_c,
            "active_work_orders": active_wos,
            "verification_required_count": verif_req,
            "data_source": "NASA C-MAPSS FD001 — Simulation",
            "real_industrial_configured": False
        }

    async def get_fleet_machines(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieves all fleet machines enriched with genuine prognostic states,
        active alerts, active work orders, and deterministic evidence-based ranking.
        """
        machines = await self.storage.get_all_machines()
        machines_to_process = machines[:limit] if limit is not None else machines

        preds_map = await self._get_all_latest_predictions()
        alerts_map = await self._get_all_active_alerts_map()
        wos_map = await self._get_all_active_work_orders_map()

        enriched_list = []

        for m in machines_to_process:
            latest_pred = preds_map.get(m.id)
            active_alerts = alerts_map.get(m.id, [])
            active_wo = wos_map.get(m.id)

            # Health classification
            health_status = "NORMAL"
            risk_level = "NORMAL"
            rul_val = None
            rul_avail = False
            anomaly_score = None
            anomaly_status = "NORMAL"
            data_quality = "OPTIMAL"
            ml_compat = "COMPATIBLE"
            evidence = []
            score = 0.0

            if m.status == "OFFLINE":
                health_status = "STALE"
                data_quality = "STALE"
                evidence.append("Unit telemetry stream is OFFLINE / STALE.")
                score += 15.0
            elif m.current_cycle == 0 and not latest_pred:
                health_status = "MISSING"
                data_quality = "NO_DATA"
                evidence.append("No active telemetry cycles received.")
            elif latest_pred:
                risk_level = latest_pred.risk_level
                anomaly_score = latest_pred.anomaly_score
                anomaly_status = latest_pred.anomaly_status

                if latest_pred.rul_estimate is not None:
                    rul_val = float(latest_pred.rul_estimate)
                    rul_avail = True
                else:
                    rul_avail = False
                    ml_compat = "INCOMPATIBLE"
                    evidence.append("RUL Prognostic unavailable (ML Incompatible schema).")

                if risk_level == "CRITICAL":
                    health_status = "CRITICAL"
                    score += 50.0
                    evidence.append(f"CRITICAL risk state detected at cycle {latest_pred.cycle}.")
                elif risk_level in ["WARNING", "MONITOR"]:
                    health_status = "WARNING"
                    score += 25.0
                    evidence.append(f"{risk_level} degradation trend detected at cycle {latest_pred.cycle}.")
                else:
                    health_status = "NORMAL"

                if rul_avail and rul_val is not None:
                    if rul_val <= 20.0:
                        score += 30.0
                        evidence.append(f"Imminent end-of-life: estimated RUL is {rul_val:.1f} cycles.")
                    elif rul_val <= 45.0:
                        score += 15.0
                        evidence.append(f"Accelerated wear: estimated RUL is {rul_val:.1f} cycles.")

                if anomaly_status == "ANOMALOUS":
                    score += 20.0
                    evidence.append(f"Isolation Forest flagged anomaly score {anomaly_score:.2f}.")

            if active_alerts:
                score += min(len(active_alerts) * 5.0, 20.0)
                evidence.append(f"{len(active_alerts)} unacknowledged active alerts present.")

            if active_wo:
                evidence.append(f"Active maintenance work order {active_wo.work_order_code} ({active_wo.status}).")

            enriched_list.append({
                "id": m.id,
                "unit_number": m.unit_number,
                "name": m.name,
                "machine_type": m.machine_type,
                "location": m.location,
                "status": m.status,
                "current_cycle": m.current_cycle,
                "health_status": health_status,
                "risk_level": risk_level,
                "health_index": latest_pred.health_index if latest_pred else None,
                "rul_estimate": rul_val,
                "rul_available": rul_avail,
                "anomaly_score": anomaly_score,
                "anomaly_status": anomaly_status,
                "data_quality": data_quality,
                "ml_compatibility": ml_compat,
                "active_alert_count": len(active_alerts),
                "active_work_order_id": active_wo.id if active_wo else None,
                "active_work_order_code": active_wo.work_order_code if active_wo else None,
                "active_work_order_status": active_wo.status if active_wo else None,
                "ranking_score": round(score, 1),
                "ranking_evidence": evidence
            })

        # Deterministic sorting by ranking_score descending
        enriched_list.sort(key=lambda x: (x["ranking_score"], x["active_alert_count"]), reverse=True)
        return enriched_list

    async def get_fleet_risk_distribution(self) -> Dict[str, Any]:
        """
        Computes genuine counts and machine lists for each risk distribution tier.
        """
        machines = await self.storage.get_all_machines()
        preds_map = await self._get_all_latest_predictions()

        breakdown: Dict[str, List[int]] = {
            "CRITICAL": [],
            "WARNING": [],
            "MONITOR": [],
            "NORMAL": [],
            "STALE": [],
            "UNKNOWN_INSUFFICIENT": []
        }

        for m in machines:
            latest_pred = preds_map.get(m.id)
            if m.status == "OFFLINE":
                breakdown["STALE"].append(m.unit_number)
            elif not latest_pred:
                breakdown["UNKNOWN_INSUFFICIENT"].append(m.unit_number)
            elif latest_pred.risk_level == "CRITICAL":
                breakdown["CRITICAL"].append(m.unit_number)
            elif latest_pred.risk_level == "WARNING":
                breakdown["WARNING"].append(m.unit_number)
            elif latest_pred.risk_level == "MONITOR":
                breakdown["MONITOR"].append(m.unit_number)
            elif latest_pred.risk_level == "NORMAL":
                breakdown["NORMAL"].append(m.unit_number)
            else:
                breakdown["UNKNOWN_INSUFFICIENT"].append(m.unit_number)

        return {
            "critical": len(breakdown["CRITICAL"]),
            "warning": len(breakdown["WARNING"]),
            "monitor": len(breakdown["MONITOR"]),
            "normal": len(breakdown["NORMAL"]),
            "stale": len(breakdown["STALE"]),
            "unknown_insufficient": len(breakdown["UNKNOWN_INSUFFICIENT"]),
            "breakdown": breakdown
        }

    async def get_fleet_maintenance_load(self) -> Dict[str, Any]:
        """
        Aggregates real maintenance workload analytics from Stage 8 WorkOrders.
        """
        stmt = select(WorkOrder)
        res = await self.session.execute(stmt)
        work_orders = res.scalars().all()

        total = len(work_orders)
        open_c = 0
        assigned_c = 0
        in_prog_c = 0
        verif_req_c = 0
        verified_c = 0

        critical_wl = 0
        high_p_wl = 0
        med_low_wl = 0
        unresolved_verif = 0

        workload_by_machine: Dict[str, Dict[str, int]] = {}
        workload_by_subsystem: Dict[str, int] = {}

        for wo in work_orders:
            s = wo.status
            p = wo.priority
            subsys = wo.affected_subsystem or "Turbofan Core"

            # Machine mapping
            m_key = f"Unit #{wo.machine_id:03d}"
            if m_key not in workload_by_machine:
                workload_by_machine[m_key] = {
                    "open": 0,
                    "assigned": 0,
                    "in_progress": 0,
                    "verification_required": 0,
                    "verified": 0
                }

            # Subsystem mapping
            workload_by_subsystem[subsys] = workload_by_subsystem.get(subsys, 0) + 1

            if s in ["OPEN", "RECOMMENDED"]:
                open_c += 1
                workload_by_machine[m_key]["open"] += 1
            elif s == "ASSIGNED":
                assigned_c += 1
                workload_by_machine[m_key]["assigned"] += 1
            elif s == "IN_PROGRESS":
                in_prog_c += 1
                workload_by_machine[m_key]["in_progress"] += 1
            elif s in ["COMPLETED", "VERIFICATION_REQUIRED"]:
                verif_req_c += 1
                workload_by_machine[m_key]["verification_required"] += 1
            elif s == "VERIFIED":
                verified_c += 1
                workload_by_machine[m_key]["verified"] += 1

            # Priority workload
            if s != "VERIFIED":
                if p == "CRITICAL":
                    critical_wl += 1
                elif p == "HIGH":
                    high_p_wl += 1
                else:
                    med_low_wl += 1

            # Unresolved verifications check
            if wo.verification_status in ["NOT_RESOLVED", "PARTIALLY_RESOLVED", "UNABLE_TO_VERIFY"]:
                unresolved_verif += 1

        return {
            "total_work_orders": total,
            "open_count": open_c,
            "assigned_count": assigned_c,
            "in_progress_count": in_prog_c,
            "verification_required_count": verif_req_c,
            "verified_count": verified_c,
            "critical_workload": critical_wl,
            "high_priority_workload": high_p_wl,
            "medium_low_workload": med_low_wl,
            "verification_backlog_count": verif_req_c,
            "unresolved_verifications_count": unresolved_verif,
            "workload_by_machine": workload_by_machine,
            "workload_by_subsystem": workload_by_subsystem
        }

    async def get_fleet_subsystems(self) -> List[Dict[str, Any]]:
        """
        Analyzes authentic subsystem reliability and defect frequencies
        across alerts, recommendations, and Stage 8 work orders.
        """
        # 1. Fetch all work orders
        stmt_wo = select(WorkOrder)
        res_wo = await self.session.execute(stmt_wo)
        work_orders = res_wo.scalars().all()

        # 2. Fetch all alerts
        stmt_al = select(Alert)
        res_al = await self.session.execute(stmt_al)
        alerts = res_al.scalars().all()

        subsystem_stats: Dict[str, Dict[str, Any]] = {}
        for s in KNOWN_SUBSYSTEMS:
            subsystem_stats[s] = {
                "subsystem": s,
                "health_status": "HEALTHY",
                "associated_alert_count": 0,
                "work_order_count": 0,
                "critical_issue_count": 0,
                "warning_issue_count": 0,
                "verification_outcomes": {
                    "RESOLVED": 0,
                    "PARTIALLY_RESOLVED": 0,
                    "NOT_RESOLVED": 0,
                    "UNABLE_TO_VERIFY": 0
                },
                "recurring_issue_count": 0,
                "affected_units": set()
            }

        # Tally Alerts
        for al in alerts:
            # Map alert to subsystem from evidence or reason if available
            target_subsys = "Turbofan Core"
            if al.evidence and isinstance(al.evidence, dict):
                signals = al.evidence.get("contributing_signals", [])
                if signals and isinstance(signals, list) and len(signals) > 0:
                    target_subsys = signals[0].get("subsystem", "Turbofan Core")
            elif "Compressor" in al.reason or "HPC" in al.reason:
                target_subsys = "High Pressure Compressor (HPC)"
            elif "Turbine" in al.reason or "LPT" in al.reason:
                target_subsys = "Low Pressure Turbine (LPT)"

            if target_subsys not in subsystem_stats:
                subsystem_stats[target_subsys] = {
                    "subsystem": target_subsys,
                    "health_status": "HEALTHY",
                    "associated_alert_count": 0,
                    "work_order_count": 0,
                    "critical_issue_count": 0,
                    "warning_issue_count": 0,
                    "verification_outcomes": {
                        "RESOLVED": 0, "PARTIALLY_RESOLVED": 0, "NOT_RESOLVED": 0, "UNABLE_TO_VERIFY": 0
                    },
                    "recurring_issue_count": 0,
                    "affected_units": set()
                }

            subsystem_stats[target_subsys]["associated_alert_count"] += 1
            if al.severity == "CRITICAL" or al.risk_level == "CRITICAL":
                subsystem_stats[target_subsys]["critical_issue_count"] += 1
            else:
                subsystem_stats[target_subsys]["warning_issue_count"] += 1
            subsystem_stats[target_subsys]["affected_units"].add(al.machine_id)

        # Tally Work Orders
        for wo in work_orders:
            subsys = wo.affected_subsystem or "Turbofan Core"
            if subsys not in subsystem_stats:
                subsystem_stats[subsys] = {
                    "subsystem": subsys,
                    "health_status": "HEALTHY",
                    "associated_alert_count": 0,
                    "work_order_count": 0,
                    "critical_issue_count": 0,
                    "warning_issue_count": 0,
                    "verification_outcomes": {
                        "RESOLVED": 0, "PARTIALLY_RESOLVED": 0, "NOT_RESOLVED": 0, "UNABLE_TO_VERIFY": 0
                    },
                    "recurring_issue_count": 0,
                    "affected_units": set()
                }

            subsystem_stats[subsys]["work_order_count"] += 1
            subsystem_stats[subsys]["affected_units"].add(wo.machine_id)
            if wo.priority == "CRITICAL":
                subsystem_stats[subsys]["critical_issue_count"] += 1
            elif wo.priority == "HIGH":
                subsystem_stats[subsys]["warning_issue_count"] += 1

            if wo.verification_status in subsystem_stats[subsys]["verification_outcomes"]:
                subsystem_stats[subsys]["verification_outcomes"][wo.verification_status] += 1

        # Determine health status and format output
        result = []
        for s, data in subsystem_stats.items():
            units_list = sorted(list(data["affected_units"]))
            recur_count = max(0, data["work_order_count"] + data["associated_alert_count"] - len(units_list))
            
            if data["critical_issue_count"] >= 2:
                status = "CRITICAL"
            elif data["warning_issue_count"] >= 2 or data["critical_issue_count"] == 1:
                status = "DEGRADED"
            elif data["associated_alert_count"] == 0 and data["work_order_count"] == 0:
                status = "HEALTHY"
            else:
                status = "MONITORED"

            result.append({
                "subsystem": s,
                "health_status": status,
                "associated_alert_count": data["associated_alert_count"],
                "work_order_count": data["work_order_count"],
                "critical_issue_count": data["critical_issue_count"],
                "warning_issue_count": data["warning_issue_count"],
                "verification_outcomes": data["verification_outcomes"],
                "recurring_issue_count": recur_count,
                "affected_units": units_list
            })

        result.sort(key=lambda x: (x["critical_issue_count"], x["warning_issue_count"], x["work_order_count"]), reverse=True)
        return result

    async def get_fleet_attention_required(self) -> List[Dict[str, Any]]:
        """
        Extracts machines requiring priority attention based on verifiable risk triggers.
        """
        all_enriched = await self.get_fleet_machines()
        attention_items = []

        for m in all_enriched:
            score = m["ranking_score"]
            is_critical = m["health_status"] == "CRITICAL" or m["risk_level"] == "CRITICAL"
            is_warning = m["health_status"] == "WARNING" or m["risk_level"] in ["WARNING", "MONITOR"]
            has_alerts = m["active_alert_count"] > 0
            is_stale = m["health_status"] == "STALE"
            low_rul = m["rul_available"] and m["rul_estimate"] is not None and m["rul_estimate"] <= 40.0

            if is_critical or is_warning or has_alerts or is_stale or low_rul or score >= 20.0:
                rec_action = "Maintain continuous sensor monitoring."
                if is_critical:
                    rec_action = "Authorize priority borescope inspection and isolate subsystem."
                elif low_rul:
                    rec_action = "Schedule replacement line module before next duty cycle."
                elif is_warning:
                    rec_action = "Perform scheduled maintenance turnaround on highlighted core sensors."
                elif is_stale:
                    rec_action = "Inspect telemetry gateway / network connection logs."

                attention_items.append({
                    "machine_id": m["id"],
                    "unit_number": m["unit_number"],
                    "name": m["name"],
                    "risk_level": m["risk_level"],
                    "health_status": m["health_status"],
                    "rul_estimate": m["rul_estimate"],
                    "rul_available": m["rul_available"],
                    "anomaly_status": m["anomaly_status"],
                    "data_quality": m["data_quality"],
                    "ml_compatibility": m["ml_compatibility"],
                    "active_alert_count": m["active_alert_count"],
                    "active_work_order_id": m["active_work_order_id"],
                    "active_work_order_code": m["active_work_order_code"],
                    "active_work_order_status": m["active_work_order_status"],
                    "urgency_score": score,
                    "recommended_action": rec_action,
                    "evidence": m["ranking_evidence"]
                })

        attention_items.sort(key=lambda x: x["urgency_score"], reverse=True)
        return attention_items
