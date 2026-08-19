"""
backend/app/services/simulation.py

Deterministic C-MAPSS FD001 Trajectory Replay Simulation Engine.

Plays back authentic turbofan degradation sequences cycle-by-cycle:
- Extracts authentic sensor telemetry per cycle
- Executes Stage 2 Feature Pipeline & ML Inference (LightGBM RUL + Isolation Forest Anomaly)
- Applies Stage 2 Decision Rules with Hysteresis & Persistence
- Persists telemetry, predictions, and alerts via StorageService
- Emits real-time WebSocket payloads via ConnectionManager
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
import numpy as np
import pandas as pd

from backend.app.database import get_session_maker
from backend.app.services.storage_service import StorageService
from backend.app.websockets.stream import ws_manager
from ml.dataset import CMAPSSDataset
from ml.inference import get_inference_engine

logger = logging.getLogger("factorymind.simulation")


class SimulationEngine:
    """
    Singleton Replay Controller managing real-time deterministic C-MAPSS playback.
    """

    def __init__(self):
        self.dataset = CMAPSSDataset()
        self.inference_engine = get_inference_engine()
        self.session_maker = get_session_maker()

        # Playback State
        self.unit_number: int = 1
        self.current_cycle: int = 0
        self.max_cycle: int = 192
        self.speed_multiplier: float = 1.0
        self.base_tick_seconds: float = 1.0
        self.is_running: bool = False
        self.is_paused: bool = False

        # Trajectory data
        self._trajectory_df: Optional[pd.DataFrame] = None
        self._buffer: List[Dict[str, Any]] = []
        self._replay_task: Optional[asyncio.Task] = None
        self._last_result: Optional[Dict[str, Any]] = None
        self._last_telemetry: Optional[Dict[str, Any]] = None
        self._machine_id: Optional[int] = None

        self._load_trajectory(1)

    def _load_trajectory(self, unit_id: int):
        """Loads complete authentic trajectory for the specified engine unit."""
        df_train = self.dataset.load_raw_train()
        unit_df = df_train[df_train["unit_number"] == unit_id].sort_values("time_cycle").reset_index(drop=True)
        if unit_df.empty:
            raise ValueError(f"Engine Unit #{unit_id} not found in C-MAPSS FD001.")

        self.unit_number = unit_id
        self._trajectory_df = unit_df
        self.max_cycle = int(unit_df["time_cycle"].max())
        self.current_cycle = 0
        self._buffer = []
        self._last_result = None
        self._last_telemetry = None
        self.inference_engine.reset_tracker(unit_id)
        logger.info(f"Loaded trajectory for Unit #{unit_id}: {len(unit_df)} operational cycles (max cycle {self.max_cycle})")

    async def _resolve_machine_id(self) -> int:
        """Finds or registers the Machine record in the database for the active unit."""
        if self._machine_id is not None:
            return self._machine_id

        async with self.session_maker() as session:
            service = StorageService(session)
            m = await service.get_machine_by_unit(self.unit_number)
            if m is None:
                m = await service.create_machine(
                    unit_number=self.unit_number,
                    name=f"Turbofan Engine #{self.unit_number:03d}",
                    machine_type="Turbofan CF6-80C2",
                    location=f"Test Cell {(self.unit_number % 4) + 1}",
                    status="OPERATIONAL"
                )
                await session.commit()
            self._machine_id = m.id
            return self._machine_id

    async def start(
        self,
        unit_number: int = 1,
        start_cycle: int = 1,
        speed_multiplier: float = 1.0
    ):
        """Starts real-time deterministic replay."""
        if self.unit_number != unit_number or self._trajectory_df is None:
            self._load_trajectory(unit_number)

        self._machine_id = None
        await self._resolve_machine_id()

        self.speed_multiplier = max(0.1, min(10.0, speed_multiplier))
        self.is_running = True
        self.is_paused = False

        # Fast forward buffer up to start_cycle - 1
        if start_cycle > 1:
            self.current_cycle = min(start_cycle - 1, self.max_cycle - 1)
            past_records = self._trajectory_df.iloc[:self.current_cycle].to_dict(orient="records")
            self._buffer = past_records
        else:
            self.current_cycle = 0
            self._buffer = []

        if self._replay_task is None or self._replay_task.done():
            self._replay_task = asyncio.create_task(self._replay_loop())

        logger.info(f"Simulation started for Unit #{self.unit_number} from cycle {self.current_cycle + 1}")

    def pause(self):
        """Pauses active replay."""
        self.is_paused = True
        logger.info(f"Simulation paused at cycle {self.current_cycle}")

    def resume(self):
        """Resumes paused replay."""
        if self.is_running:
            self.is_paused = False
            logger.info(f"Simulation resumed at cycle {self.current_cycle}")

    async def stop(self):
        """Stops active replay."""
        self.is_running = False
        self.is_paused = False
        if self._replay_task and not self._replay_task.done():
            self._replay_task.cancel()
            try:
                await self._replay_task
            except asyncio.CancelledError:
                pass
        self._replay_task = None
        logger.info("Simulation stopped.")

    async def reset(self, unit_number: int = 1, start_cycle: int = 1):
        """Resets replay back to initial cycle."""
        await self.stop()
        self._load_trajectory(unit_number)
        self.current_cycle = max(0, start_cycle - 1)
        self._buffer = []
        self._last_result = None
        self._last_telemetry = None
        logger.info(f"Simulation reset for Unit #{unit_number}")

    async def step(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Advances the replay by exactly ONE cycle observation:
        1. Extracts next real observation from C-MAPSS FD001 dataset
        2. Appends to active observation window
        3. Executes Stage 2 inference (RUL, Anomaly, Health Index, Risk Level)
        4. Persists telemetry, predictions, and alerts into database
        5. Broadcasts live frame via WebSocket
        
        Returns:
            (is_completed, telemetry_dict, prediction_dict, alert_dict)
        """
        if self._trajectory_df is None or self.current_cycle >= self.max_cycle:
            self.is_running = False
            return True, self._last_telemetry, self._last_result, None

        next_cycle_idx = self.current_cycle
        next_row = self._trajectory_df.iloc[next_cycle_idx].to_dict()
        self._buffer.append(next_row)
        self.current_cycle = int(next_row["time_cycle"])

        # Construct DataFrame window for feature engineering
        window_df = pd.DataFrame(self._buffer)

        # 2. Run real Stage 2 inference
        result = self.inference_engine.predict_window(window_df, apply_hysteresis=True)
        self._last_result = result
        self._last_telemetry = next_row

        # 3. Persist to database
        machine_id = await self._resolve_machine_id()
        alert_dict = None

        try:
            async with self.session_maker() as session:
                service = StorageService(session)
                # Ingest telemetry
                await service.insert_telemetry_single(machine_id, next_row)
                # Persist inference & alert lifecycle
                pred, anomaly, alert = await service.persist_inference_cycle(machine_id, result)
                await session.commit()

                if alert is not None:
                    alert_dict = alert.to_dict()
        except Exception as e:
            logger.error(f"Error persisting simulation cycle to database: {e}")

        # 4. Broadcast live frame to connected WebSocket clients
        broadcast_frame = {
            "type": "SIMULATION_TICK",
            "unit_number": self.unit_number,
            "machine_id": machine_id,
            "cycle": self.current_cycle,
            "max_cycle": self.max_cycle,
            "telemetry": next_row,
            "prediction": result,
            "alert": alert_dict,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await ws_manager.broadcast(broadcast_frame)

        is_completed = (self.current_cycle >= self.max_cycle)
        if is_completed:
            self.is_running = False

        return is_completed, next_row, result, alert_dict

    async def _replay_loop(self):
        """Background loop executing cycle steps at configured speed multiplier."""
        try:
            while self.is_running:
                if not self.is_paused:
                    is_completed, _, _, _ = await self.step()
                    if is_completed:
                        logger.info(f"Replay completed for Unit #{self.unit_number} at cycle {self.current_cycle}")
                        break

                interval = max(0.05, self.base_tick_seconds / self.speed_multiplier)
                await asyncio.sleep(interval)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Unexpected error in simulation loop: {e}", exc_info=True)
            self.is_running = False

    def get_status(self) -> Dict[str, Any]:
        """Returns instantaneous simulation state."""
        return {
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "unit_number": self.unit_number,
            "current_cycle": self.current_cycle,
            "max_cycle": self.max_cycle,
            "speed_multiplier": self.speed_multiplier,
            "total_cycles_in_trajectory": self.max_cycle,
            "latest_rul": self._last_result.get("rul_estimate") if self._last_result else None,
            "latest_health_index": self._last_result.get("health_index") if self._last_result else None,
            "latest_risk_level": self._last_result.get("risk_level") if self._last_result else None,
            "latest_anomaly_score": self._last_result.get("anomaly_score") if self._last_result else None,
        }


# Module singleton instance
_simulation_engine_instance: Optional[SimulationEngine] = None


def get_simulation_engine() -> SimulationEngine:
    global _simulation_engine_instance
    if _simulation_engine_instance is None:
        _simulation_engine_instance = SimulationEngine()
    return _simulation_engine_instance
