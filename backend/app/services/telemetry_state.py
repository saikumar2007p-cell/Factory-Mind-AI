"""
backend/app/services/telemetry_state.py

Telemetry Data Freshness State Service for FactoryMind AI.

Computes and updates the telemetry_state field on Machine records.
Separates DATA availability from machine HEALTH status.

States:
  CURRENT      – telemetry received within machine's freshness window
  STALE        – last telemetry outside freshness window, machine state unknown
  NO_NEW_DATA  – has some historical data but nothing new since last session start
  NO_DATA      – registered but has never sent any telemetry
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.machine import Machine

import logging

logger = logging.getLogger("factorymind.telemetry_state")

# Human-readable display labels for UI
TELEMETRY_STATE_LABELS: Dict[str, Dict[str, str]] = {
    "CURRENT": {
        "label": "Current",
        "description": "Live telemetry stream active",
        "badge_color": "green",
        "icon": "wifi"
    },
    "STALE": {
        "label": "Stale",
        "description": "Last telemetry received outside freshness window",
        "badge_color": "amber",
        "icon": "clock"
    },
    "NO_NEW_DATA": {
        "label": "No New Data",
        "description": "Historical data exists but no new telemetry since last session",
        "badge_color": "grey",
        "icon": "pause"
    },
    "NO_DATA": {
        "label": "No Data",
        "description": "Machine registered but has never sent telemetry",
        "badge_color": "grey",
        "icon": "slash"
    },
}


class TelemetryStateService:
    """
    Computes and persists telemetry freshness states for machine records.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def compute_state(self, machine: Machine, now: Optional[datetime] = None) -> str:
        """
        Deterministic state computation from machine's last_telemetry_at
        and telemetry_freshness_seconds threshold.

        Args:
            machine: Machine ORM instance
            now: Reference time (defaults to UTC now)

        Returns:
            str: One of CURRENT | STALE | NO_NEW_DATA | NO_DATA
        """
        now = now or datetime.now(timezone.utc)

        if machine.last_telemetry_at is None:
            # Never received telemetry
            if machine.current_cycle == 0:
                return "NO_DATA"
            else:
                # Has cycle data but last_telemetry_at not recorded (legacy)
                return "NO_NEW_DATA"

        # Ensure timezone-aware comparison
        last_ts = machine.last_telemetry_at
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)

        elapsed_seconds = (now - last_ts).total_seconds()
        freshness_threshold = machine.telemetry_freshness_seconds or 300

        if elapsed_seconds <= freshness_threshold:
            return "CURRENT"
        elif elapsed_seconds <= freshness_threshold * 6:
            # Within 6x the freshness window — still potentially active, just delayed
            return "STALE"
        else:
            # Well outside any reasonable freshness window
            return "NO_NEW_DATA"

    async def update_machine_state(self, machine_id: int) -> Optional[str]:
        """Updates telemetry_state for a single machine. Returns new state."""
        stmt = select(Machine).where(Machine.id == machine_id)
        result = await self.session.execute(stmt)
        machine = result.scalar_one_or_none()
        if not machine:
            return None

        now = datetime.now(timezone.utc)
        new_state = self.compute_state(machine, now)

        if machine.telemetry_state != new_state:
            await self.session.execute(
                update(Machine)
                .where(Machine.id == machine_id)
                .values(telemetry_state=new_state)
            )
            logger.info(f"Machine {machine_id} telemetry_state: {machine.telemetry_state} → {new_state}")

        return new_state

    async def refresh_all_machine_states(self) -> Dict[str, int]:
        """
        Bulk-recomputes and updates telemetry_state for all machines.
        Called at startup and periodically to keep states fresh.

        Returns:
            Dict with counts per state.
        """
        stmt = select(Machine)
        result = await self.session.execute(stmt)
        machines = result.scalars().all()

        now = datetime.now(timezone.utc)
        state_counts: Dict[str, int] = {
            "CURRENT": 0, "STALE": 0, "NO_NEW_DATA": 0, "NO_DATA": 0
        }
        updates = []

        for machine in machines:
            new_state = self.compute_state(machine, now)
            state_counts[new_state] = state_counts.get(new_state, 0) + 1
            if machine.telemetry_state != new_state:
                updates.append({"id": machine.id, "telemetry_state": new_state})

        # Bulk update only changed records
        for upd in updates:
            await self.session.execute(
                update(Machine)
                .where(Machine.id == upd["id"])
                .values(telemetry_state=upd["telemetry_state"])
            )

        if updates:
            logger.info(f"Refreshed telemetry_state for {len(updates)} machines. Counts: {state_counts}")

        return state_counts

    async def mark_telemetry_received(self, machine_id: int) -> None:
        """
        Called immediately after successful telemetry ingestion to update
        last_telemetry_at and set state to CURRENT.
        """
        now = datetime.now(timezone.utc)
        await self.session.execute(
            update(Machine)
            .where(Machine.id == machine_id)
            .values(last_telemetry_at=now, telemetry_state="CURRENT")
        )
