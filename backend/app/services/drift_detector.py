"""
backend/app/services/drift_detector.py

Behavioral Change Detection Service for FactoryMind AI.

Detects statistically significant shifts in machine sensor behavior and records
them as CAUSALLY NEUTRAL observations. Does NOT conclude machine health impact —
that requires human investigation.

Detection methods:
  ZSCORE      – per-sensor z-score vs rolling baseline
  CUSUM       – cumulative sum control chart on health index
  IQR         – interquartile-range outlier test

Classification heuristics (suggested, not authoritative):
  Single sensor drifts                → suggest SENSOR_ISSUE
  All sensors shift together          → suggest OPERATING_CONDITION
  Health index CUSUM breach           → suggest MACHINE_ANOMALY
  Sporadic nulls / spikes             → suggest DATA_QUALITY
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.behavioral_change import BehavioralChange
from backend.app.models.machine import Machine
from backend.app.models.prediction import Prediction
import numpy as np
import logging

logger = logging.getLogger("factorymind.drift")

# Z-score threshold above which a sensor is flagged
ZSCORE_FLAG_THRESHOLD = 2.5

# CUSUM: if the cumulative sum of health deviations exceeds this, flag it
CUSUM_HEALTH_THRESHOLD = 15.0


class DriftDetectorService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def get_changes_for_machine(
        self,
        machine_id: int,
        status_filter: Optional[str] = None
    ) -> List[BehavioralChange]:
        stmt = select(BehavioralChange).where(BehavioralChange.machine_id == machine_id)
        if status_filter:
            stmt = stmt.where(BehavioralChange.investigation_status == status_filter)
        stmt = stmt.order_by(BehavioralChange.detected_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_fleet_pending_changes(self) -> List[BehavioralChange]:
        """Returns all PENDING behavioral changes across the fleet."""
        stmt = (
            select(BehavioralChange)
            .where(BehavioralChange.investigation_status == "PENDING")
            .order_by(BehavioralChange.detected_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_change_by_id(self, change_id: int) -> Optional[BehavioralChange]:
        stmt = select(BehavioralChange).where(BehavioralChange.id == change_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    # -------------------------------------------------------------------------
    # DETECTION
    # -------------------------------------------------------------------------

    def detect_zscore_drift(
        self,
        current_values: Dict[str, float],
        baseline_stats: Dict[str, Dict[str, float]]  # sensor_id → {mean, std}
    ) -> Tuple[List[str], float, Dict[str, float]]:
        """
        Computes z-score drift per sensor against provided baseline statistics.

        Returns:
            flagged_sensors: list of sensor IDs with |z| > threshold
            aggregate_magnitude: mean of flagged z-score magnitudes
            per_sensor_zscores: dict of sensor_id → z-score
        """
        flagged = []
        per_sensor: Dict[str, float] = {}

        for sensor_id, value in current_values.items():
            stats = baseline_stats.get(sensor_id)
            if not stats:
                continue
            mean = stats.get("mean", 0.0)
            std = stats.get("std", 1.0)
            if std < 1e-6:
                std = 1.0
            z = (value - mean) / std
            per_sensor[sensor_id] = round(z, 3)
            if abs(z) >= ZSCORE_FLAG_THRESHOLD:
                flagged.append(sensor_id)

        magnitude = float(np.mean([abs(per_sensor[s]) for s in flagged])) if flagged else 0.0
        return flagged, round(magnitude, 3), per_sensor

    def suggest_change_type(
        self,
        flagged_sensors: List[str],
        all_sensor_count: int,
        drift_details: Dict[str, float]
    ) -> str:
        """
        Heuristic classifier that suggests a POSSIBLE cause category.
        This is a SUGGESTION only — human investigation is required.
        Returns one of: MACHINE_ANOMALY, SENSOR_ISSUE, OPERATING_CONDITION, DATA_QUALITY, UNKNOWN
        """
        n_flagged = len(flagged_sensors)
        if n_flagged == 0:
            return "UNKNOWN"
        fraction = n_flagged / max(all_sensor_count, 1)

        if fraction >= 0.7:
            # Most sensors shifted simultaneously → likely operating condition change
            return "OPERATING_CONDITION"
        elif n_flagged == 1:
            # Only one sensor flagged → likely sensor issue
            return "SENSOR_ISSUE"
        elif n_flagged <= 3:
            # A few correlated sensors → possible machine anomaly
            return "MACHINE_ANOMALY"
        else:
            return "UNKNOWN"

    async def record_behavioral_change(
        self,
        machine_id: int,
        affected_sensors: List[str],
        drift_magnitude: float,
        drift_method: str,
        drift_details: Optional[Dict[str, Any]] = None,
        cycle: Optional[int] = None,
        linked_alert_id: Optional[int] = None
    ) -> BehavioralChange:
        """
        Persists a detected behavioral change as a PENDING observation.
        Does NOT set change_type — that requires investigation.
        """
        change = BehavioralChange(
            machine_id=machine_id,
            cycle=cycle,
            affected_sensors=affected_sensors,
            drift_magnitude=drift_magnitude,
            drift_method=drift_method,
            drift_details=drift_details,
            investigation_status="PENDING",
            linked_alert_id=linked_alert_id
        )
        self.session.add(change)
        await self.session.flush()
        await self.session.refresh(change)
        logger.info(
            f"Behavioral change recorded for machine {machine_id}: "
            f"{len(affected_sensors)} sensors flagged via {drift_method} "
            f"(magnitude={drift_magnitude:.3f})"
        )
        return change

    # -------------------------------------------------------------------------
    # INVESTIGATION
    # -------------------------------------------------------------------------

    async def record_investigation(
        self,
        change_id: int,
        change_type: str,
        root_cause: str,
        investigator: str,
        notes: Optional[str] = None,
        close: bool = True
    ) -> Optional[BehavioralChange]:
        """
        Records investigation result for a PENDING behavioral change.

        Args:
            change_id: ID of the BehavioralChange to investigate
            change_type: MACHINE_ANOMALY | SENSOR_ISSUE | OPERATING_CONDITION | DATA_QUALITY | UNKNOWN
            root_cause: Brief description of what was found
            investigator: Name of the person investigating
            notes: Optional extended notes
            close: If True, sets status to CLOSED; if False, sets to INVESTIGATED
        """
        valid_types = {
            "MACHINE_ANOMALY", "OPERATING_CONDITION",
            "SENSOR_ISSUE", "DATA_QUALITY", "UNKNOWN"
        }
        change_type = change_type.upper()
        if change_type not in valid_types:
            raise ValueError(f"Invalid change_type '{change_type}'. Must be one of: {', '.join(valid_types)}")

        change = await self.get_change_by_id(change_id)
        if not change:
            raise ValueError(f"Behavioral change ID {change_id} not found.")

        new_status = "CLOSED" if close else "INVESTIGATED"
        await self.session.execute(
            update(BehavioralChange)
            .where(BehavioralChange.id == change_id)
            .values(
                change_type=change_type,
                root_cause=root_cause,
                investigator=investigator,
                investigated_at=datetime.now(timezone.utc),
                notes=notes,
                investigation_status=new_status,
                updated_at=datetime.now(timezone.utc)
            )
        )
        logger.info(
            f"Behavioral change {change_id} investigated by {investigator}: "
            f"type={change_type}, status={new_status}"
        )
        return await self.get_change_by_id(change_id)
