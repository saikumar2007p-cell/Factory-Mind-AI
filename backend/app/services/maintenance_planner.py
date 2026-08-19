"""
backend/app/services/maintenance_planner.py

Deterministic Predictive Maintenance Planner Service for Stage 9.
Provides strictly read-only decision-support recommendations based on authentic fleet records.
NEVER autonomously creates, assigns, mutates, completes, or verifies work orders.
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.services.fleet_intelligence import FleetIntelligenceService


class MaintenancePlannerService:
    """
    Predictive Maintenance Planning Decision-Support Engine.
    Evaluates fleet health, prognostics, sensor drift, and work-order states
    to recommend human maintenance actions without automated state mutation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.fleet_service = FleetIntelligenceService(session)

    async def generate_fleet_plan(self) -> Dict[str, Any]:
        """
        Generates deterministic maintenance planning recommendations across all fleet units.
        Categorizes units into:
        - Immediate Attention
        - High Priority
        - Schedule Inspection
        - Monitor Closely
        - No Action Recommended
        - Insufficient Data
        """
        fleet_machines = await self.fleet_service.get_fleet_machines()

        imm_att_c = 0
        high_p_c = 0
        sched_insp_c = 0
        mon_close_c = 0
        no_act_c = 0
        insuff_data_c = 0

        plans = []
        for rank_idx, m in enumerate(fleet_machines, start=1):
            planning_state = "No Action Recommended"
            rec_title = "Nominal Operation"
            rec_details = "Engine core parameters are tracking within baseline operational limits."
            sugg_action = "Maintain standard operating schedule."
            evidence = list(m["ranking_evidence"])

            # 1. Check Insufficient Data / Stale
            if m["health_status"] == "MISSING":
                planning_state = "Insufficient Data"
                rec_title = "Telemetry Ingestion Required"
                rec_details = "No telemetry cycles have been recorded for this turbofan unit."
                sugg_action = "Verify data ingestion stream in Data Sources configuration."
                insuff_data_c += 1
            elif m["health_status"] == "STALE" or m["data_quality"] == "STALE":
                planning_state = "Insufficient Data"
                rec_title = "Stale Telemetry Feed"
                rec_details = "Telemetry feed is offline or delayed. Real-time condition cannot be confirmed."
                sugg_action = "Inspect physical IoT edge gateway and telemetry transmission logs."
                insuff_data_c += 1
            # 2. Check Immediate Attention Triggers
            elif (
                m["health_status"] == "CRITICAL"
                or m["risk_level"] == "CRITICAL"
                or (m["rul_available"] and m["rul_estimate"] is not None and m["rul_estimate"] <= 20.0)
            ):
                planning_state = "Immediate Attention"
                rul_txt = f"{m['rul_estimate']:.1f} cycles" if m["rul_available"] and m["rul_estimate"] is not None else "UNAVAILABLE"
                rec_title = "Immediate Inspection & Module Replacement Required"
                rec_details = f"Unit has reached critical failure threshold (RUL: {rul_txt}). Sustained thermal and pressure drift indicates imminent breakdown."
                sugg_action = "Issue high-priority work order for immediate borescope inspection and isolate the unit."
                imm_att_c += 1
            # 3. Check High Priority Triggers
            elif (
                m["health_status"] == "WARNING"
                or m["risk_level"] == "WARNING"
                or (m["rul_available"] and m["rul_estimate"] is not None and m["rul_estimate"] <= 45.0)
                or m["active_alert_count"] >= 2
            ):
                planning_state = "High Priority"
                rul_txt = f"{m['rul_estimate']:.1f} cycles" if m["rul_available"] and m["rul_estimate"] is not None else "UNAVAILABLE"
                rec_title = "Scheduled Core Turnaround Recommended"
                rec_details = f"Predictive degradation rate indicates accelerated core wear (RUL: {rul_txt}). Maintenance turnaround required within scheduled operating window."
                sugg_action = "Authorize maintenance work order and assign certified turbine technician."
                high_p_c += 1
            # 4. Check Schedule Inspection Triggers
            elif (
                m["risk_level"] == "MONITOR"
                or m["anomaly_status"] == "ANOMALOUS"
                or m["active_work_order_status"] == "VERIFICATION_REQUIRED"
                or m["active_alert_count"] == 1
            ):
                planning_state = "Schedule Inspection"
                if m["active_work_order_status"] == "VERIFICATION_REQUIRED":
                    rec_title = "Post-Maintenance Verification Sign-Off Pending"
                    rec_details = f"Work order {m['active_work_order_code']} completed by field technician. Pending engineering sign-off."
                    sugg_action = "Inspect post-maintenance telemetry and complete verification sign-off in Maintenance."
                else:
                    rec_title = "Targeted Sensor Inspection"
                    rec_details = "Mild thermodynamic divergence detected. Operational risk remains low but requires verification."
                    sugg_action = "Schedule non-destructive inspection during next scheduled turnaround."
                sched_insp_c += 1
            # 5. Check Monitor Closely Triggers
            elif m["health_index"] is not None and m["health_index"] < 80.0:
                planning_state = "Monitor Closely"
                rec_title = "Elevated Baseline Tracking"
                rec_details = f"Engine Health Index is at {m['health_index']:.1f}%. Baseline drift is beginning to accumulate."
                sugg_action = "Track sensor variance over subsequent 10 operational cycles."
                mon_close_c += 1
            # 6. No Action Recommended
            else:
                planning_state = "No Action Recommended"
                rec_title = "Nominal Operational Health"
                rec_details = "All turbofan sub-systems operating within validated normal envelopes."
                sugg_action = "Continue standard operational duty cycles."
                no_act_c += 1

            plans.append({
                "machine_id": m["id"],
                "unit_number": m["unit_number"],
                "machine_name": m["name"],
                "planning_state": planning_state,
                "urgency_rank": rank_idx,
                "risk_level": m["risk_level"],
                "rul_estimate": m["rul_estimate"],
                "rul_available": m["rul_available"],
                "anomaly_status": m["anomaly_status"],
                "data_quality": m["data_quality"],
                "ml_compatibility": m["ml_compatibility"],
                "active_work_order_id": m["active_work_order_id"],
                "active_work_order_code": m["active_work_order_code"],
                "active_work_order_status": m["active_work_order_status"],
                "recommendation_title": rec_title,
                "recommendation_details": rec_details,
                "suggested_action": sugg_action,
                "evidence_points": evidence
            })

        return {
            "total_planned": len(plans),
            "immediate_attention_count": imm_att_c,
            "high_priority_count": high_p_c,
            "schedule_inspection_count": sched_insp_c,
            "monitor_closely_count": mon_close_c,
            "no_action_count": no_act_c,
            "insufficient_data_count": insuff_data_c,
            "plans": plans
        }
