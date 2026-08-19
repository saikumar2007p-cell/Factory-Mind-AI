"""
backend/app/services/historical_trends.py

Stage 10 Historical Trend Analytics Service.
Builds deterministic historical timelines from genuine database timestamps (telemetry, predictions, alerts, work orders, audit logs).
Strictly prevents the fabrication of synthetic historical data points.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from backend.app.models.work_order import WorkOrder, WorkOrderAuditLog
from backend.app.models.prediction import Prediction
from backend.app.models.alert import Alert
from backend.app.models.telemetry import Telemetry
from backend.app.services.storage_service import StorageService


class HistoricalTrendsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.storage = StorageService(session)

    async def get_historical_trends(self, trend_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves historical trends for RISK, ALERTS, MAINTENANCE, VERIFICATION, and RECURRENCE.
        """
        trend_keys = ["RISK", "ALERTS", "MAINTENANCE", "VERIFICATION", "RECURRENCE"]
        selected_types = [trend_type.upper()] if (trend_type and trend_type.upper() in trend_keys) else trend_keys

        trends_result = {}
        for t_type in selected_types:
            if t_type == "RISK":
                trends_result["RISK"] = await self._get_risk_trends()
            elif t_type == "ALERTS":
                trends_result["ALERTS"] = await self._get_alert_trends()
            elif t_type == "MAINTENANCE":
                trends_result["MAINTENANCE"] = await self._get_maintenance_trends()
            elif t_type == "VERIFICATION":
                trends_result["VERIFICATION"] = await self._get_verification_trends()
            elif t_type == "RECURRENCE":
                trends_result["RECURRENCE"] = await self._get_recurrence_trends()

        if trend_type and trend_type.upper() in trends_result:
            return trends_result[trend_type.upper()]

        return {
            "trends": trends_result
        }

    async def _get_risk_trends(self) -> Dict[str, Any]:
        """Calculates risk trend from genuine prediction records."""
        stmt = (
            select(
                Prediction.cycle,
                func.avg(Prediction.risk_score).label("avg_risk"),
                func.avg(Prediction.health_index).label("avg_health"),
                func.count(Prediction.id).label("pred_count")
            )
            .group_by(Prediction.cycle)
            .order_by(Prediction.cycle.asc())
            .limit(50)
        )
        res = await self.session.execute(stmt)
        rows = res.all()

        if len(rows) < 2:
            return {
                "trend_type": "RISK",
                "has_sufficient_data": False,
                "data_points": [],
                "message": "Insufficient historical data (requires at least 2 distinct operational cycles)."
            }

        points = []
        for r in rows:
            points.append({
                "timestamp": f"Cycle {r.cycle}",
                "label": f"Cycle {r.cycle}",
                "value": round(float(r.avg_risk), 3),
                "metadata": {
                    "avg_health_index": round(float(r.avg_health), 1),
                    "machines_sampled": int(r.pred_count)
                }
            })

        return {
            "trend_type": "RISK",
            "has_sufficient_data": True,
            "data_points": points,
            "message": f"Historical fleet risk trend computed across {len(points)} operational cycles."
        }

    async def _get_alert_trends(self) -> Dict[str, Any]:
        """Calculates alert frequency over genuine timestamps."""
        stmt = (
            select(
                func.date(Alert.created_at).label("alert_date"),
                func.count(Alert.id).label("alert_count")
            )
            .group_by(func.date(Alert.created_at))
            .order_by(func.date(Alert.created_at).asc())
        )
        res = await self.session.execute(stmt)
        rows = res.all()

        if len(rows) < 2:
            # Check total count of alerts
            stmt_all = select(Alert).order_by(Alert.created_at.asc()).limit(30)
            res_all = await self.session.execute(stmt_all)
            alerts = res_all.scalars().all()
            if len(alerts) < 2:
                return {
                    "trend_type": "ALERTS",
                    "has_sufficient_data": False,
                    "data_points": [],
                    "message": "Insufficient historical data (requires at least 2 alert events)."
                }
            points = []
            for idx, a in enumerate(alerts):
                points.append({
                    "timestamp": a.created_at.isoformat() if a.created_at else f"Event #{idx+1}",
                    "label": f"Alert #{a.id} ({a.severity})",
                    "value": 1.0 if a.severity == "CRITICAL" else (0.5 if a.severity == "WARNING" else 0.2),
                    "metadata": {"machine_id": a.machine_id, "reason": a.reason}
                })
            return {
                "trend_type": "ALERTS",
                "has_sufficient_data": True,
                "data_points": points,
                "message": f"Alert timeline generated from {len(points)} recorded alerts."
            }

        points = [{
            "timestamp": str(r.alert_date),
            "label": str(r.alert_date),
            "value": float(r.alert_count),
            "metadata": {}
        } for r in rows]

        return {
            "trend_type": "ALERTS",
            "has_sufficient_data": True,
            "data_points": points,
            "message": f"Alert frequency timeline across {len(points)} dates."
        }

    async def _get_maintenance_trends(self) -> Dict[str, Any]:
        """Calculates work order creation and completion activity."""
        all_wos = await self.storage.list_work_orders()
        if len(all_wos) < 2:
            return {
                "trend_type": "MAINTENANCE",
                "has_sufficient_data": False,
                "data_points": [],
                "message": "Insufficient historical data (requires at least 2 work order records)."
            }

        points = []
        for w in all_wos:
            points.append({
                "timestamp": w.created_at.isoformat() if w.created_at else "Initial",
                "label": w.work_order_code,
                "value": 1.0 if w.status in ["COMPLETED", "VERIFIED"] else 0.5,
                "metadata": {
                    "status": w.status,
                    "subsystem": w.affected_subsystem,
                    "machine_id": w.machine_id
                }
            })

        return {
            "trend_type": "MAINTENANCE",
            "has_sufficient_data": True,
            "data_points": points,
            "message": f"Maintenance activity trend computed from {len(points)} work order events."
        }

    async def _get_verification_trends(self) -> Dict[str, Any]:
        """Calculates verification outcomes over time."""
        all_wos = await self.storage.list_work_orders()
        verified_wos = [w for w in all_wos if w.status == "VERIFIED"]

        if len(verified_wos) < 2:
            return {
                "trend_type": "VERIFICATION",
                "has_sufficient_data": False,
                "data_points": [],
                "message": "Insufficient historical data (requires at least 2 verified work order records)."
            }

        points = []
        for w in verified_wos:
            v_val = 1.0 if (w.verification_status or "").upper() == "RESOLVED" else (0.5 if (w.verification_status or "").upper() == "PARTIALLY_RESOLVED" else 0.0)
            points.append({
                "timestamp": w.verified_at.isoformat() if w.verified_at else "Verified",
                "label": f"{w.work_order_code}: {w.verification_status}",
                "value": v_val,
                "metadata": {
                    "verification_status": w.verification_status,
                    "machine_id": w.machine_id,
                    "subsystem": w.affected_subsystem
                }
            })

        return {
            "trend_type": "VERIFICATION",
            "has_sufficient_data": True,
            "data_points": points,
            "message": f"Verification outcome trend computed from {len(points)} verified maintenance records."
        }

    async def _get_recurrence_trends(self) -> Dict[str, Any]:
        """Calculates recurrence activity over time."""
        all_wos = await self.storage.list_work_orders()
        # Group by machine
        m_counts: Dict[int, int] = {}
        repeat_points = []
        for w in all_wos:
            m_counts[w.machine_id] = m_counts.get(w.machine_id, 0) + 1
            if m_counts[w.machine_id] >= 2:
                repeat_points.append({
                    "timestamp": w.created_at.isoformat() if w.created_at else "Logged",
                    "label": f"Unit #{w.machine_id} repeat #{m_counts[w.machine_id]}",
                    "value": float(m_counts[w.machine_id]),
                    "metadata": {
                        "machine_id": w.machine_id,
                        "subsystem": w.affected_subsystem
                    }
                })

        if len(repeat_points) < 2:
            return {
                "trend_type": "RECURRENCE",
                "has_sufficient_data": False,
                "data_points": [],
                "message": "Insufficient historical data (no recurring patterns exceeding threshold)."
            }

        return {
            "trend_type": "RECURRENCE",
            "has_sufficient_data": True,
            "data_points": repeat_points,
            "message": f"Recurrence trend computed from {len(repeat_points)} repeat intervention events."
        }
