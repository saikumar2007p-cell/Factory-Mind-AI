"""
backend/app/services/decision_rules.py

Risk Stratification, Health Index Computation, Hysteresis, and Multi-Cycle Persistence Engine.

Guarantees:
- Deterministic, calibrated risk level assignment (NORMAL, MONITOR, WARNING, CRITICAL)
- Hysteresis band protection against boundary alert flapping
- Multi-cycle persistence requirement preventing spurious transitions from transient noise
- Clear separation between enter thresholds and exit thresholds
"""

from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np


class RiskLevel(str, Enum):
    NORMAL = "NORMAL"
    MONITOR = "MONITOR"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AnomalyStatus(str, Enum):
    NORMAL = "NORMAL"
    ANOMALOUS = "ANOMALOUS"


@dataclass
class SensorSignalEvidence:
    sensor_id: str
    name: str
    subsystem: str
    current_value: float
    baseline_value: float
    delta: float
    percent_change: float
    z_score: float
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_slope: float
    importance_rank: int


@dataclass
class RiskThresholds:
    """
    Calibrated Risk thresholds with asymmetric enter/exit boundaries (hysteresis).
    """
    # Enter thresholds (escalation)
    enter_monitor_score: float = 30.0
    enter_warning_score: float = 60.0
    enter_critical_score: float = 80.0

    # Exit thresholds (de-escalation margin = 5.0 to 10.0 points)
    exit_critical_score: float = 72.0
    exit_warning_score: float = 52.0
    exit_monitor_score: float = 24.0

    # Persistence requirements (consecutive cycles)
    escalation_persistence_cycles: int = 2
    deescalation_persistence_cycles: int = 3

    # Direct physical safety override
    critical_rul_override: float = 12.0


def compute_health_index(
    predicted_rul: float,
    anomaly_score: float,
    clip_rul: float = 125.0,
    rul_weight: float = 0.70,
    anomaly_weight: float = 0.30
) -> float:
    """
    Computes a deterministic, continuous Composite Health Index (0% to 100%).
    
    Formula:
        HI = clip(0.70 * (RUL_pred / 125.0 * 100) + 0.30 * ((1.0 - Anomaly_score) * 100), 0.0, 100.0)
    """
    rul_norm = np.clip(predicted_rul / clip_rul, 0.0, 1.0) * 100.0
    anomaly_norm = np.clip(1.0 - anomaly_score, 0.0, 1.0) * 100.0
    
    health_index = (rul_weight * rul_norm) + (anomaly_weight * anomaly_norm)
    return float(np.round(np.clip(health_index, 0.0, 100.0), 2))


def compute_risk_score(health_index: float) -> float:
    """
    Computes composite Risk Score (0 to 100) inversely proportional to Machine Health Index.
    """
    return float(np.round(np.clip(100.0 - health_index, 0.0, 100.0), 2))


class HysteresisRiskEngine:
    """
    Stateful risk decision engine applying threshold hysteresis and persistence checks
    for an individual engine unit over consecutive operational cycles.
    """

    def __init__(self, thresholds: Optional[RiskThresholds] = None):
        self.thresholds = thresholds or RiskThresholds()
        self.current_state: RiskLevel = RiskLevel.NORMAL
        self.candidate_state: Optional[RiskLevel] = None
        self.candidate_persistence_counter: int = 0
        self.history: List[Dict[str, Any]] = []

    def reset(self):
        """Resets state for a new engine run."""
        self.current_state = RiskLevel.NORMAL
        self.candidate_state = None
        self.candidate_persistence_counter = 0
        self.history.clear()

    def evaluate_instantaneous_level(self, risk_score: float, predicted_rul: float) -> RiskLevel:
        """
        Determines instantaneous target risk level before hysteresis and persistence filtering.
        """
        # Hard safety override: Very low RUL forces immediate CRITICAL intent
        if predicted_rul <= self.thresholds.critical_rul_override:
            return RiskLevel.CRITICAL

        if risk_score >= self.thresholds.enter_critical_score:
            return RiskLevel.CRITICAL
        elif risk_score >= self.thresholds.enter_warning_score:
            return RiskLevel.WARNING
        elif risk_score >= self.thresholds.enter_monitor_score:
            return RiskLevel.MONITOR
        else:
            return RiskLevel.NORMAL

    def update(
        self,
        cycle: int,
        risk_score: float,
        predicted_rul: float,
        anomaly_score: float
    ) -> Tuple[RiskLevel, bool]:
        """
        Updates machine risk state applying hysteresis and persistence rules.
        
        Returns:
            (filtered_risk_level, state_changed_boolean)
        """
        instant_level = self.evaluate_instantaneous_level(risk_score, predicted_rul)
        prev_state = self.current_state
        state_changed = False

        # State transition evaluation with hysteresis
        target_state = self._evaluate_with_hysteresis(risk_score, predicted_rul, instant_level)

        if target_state == self.current_state:
            # Reached stability at current state
            self.candidate_state = None
            self.candidate_persistence_counter = 0
        else:
            # Target is different from current state
            if target_state == self.candidate_state:
                self.candidate_persistence_counter += 1
            else:
                self.candidate_state = target_state
                self.candidate_persistence_counter = 1

            # Check if persistence threshold is satisfied
            required_cycles = self._get_required_persistence(self.current_state, target_state)
            
            # Emergency bypass: If RUL <= critical_rul_override, escalate immediately without delay
            if predicted_rul <= self.thresholds.critical_rul_override and target_state == RiskLevel.CRITICAL:
                required_cycles = 1

            if self.candidate_persistence_counter >= required_cycles:
                self.current_state = target_state
                state_changed = True
                self.candidate_state = None
                self.candidate_persistence_counter = 0

        # Record audit history
        record = {
            "cycle": cycle,
            "risk_score": risk_score,
            "predicted_rul": predicted_rul,
            "anomaly_score": anomaly_score,
            "instant_level": instant_level.value,
            "effective_level": self.current_state.value,
            "state_changed": state_changed
        }
        self.history.append(record)

        return self.current_state, state_changed

    def _evaluate_with_hysteresis(
        self,
        risk_score: float,
        predicted_rul: float,
        instant_level: RiskLevel
    ) -> RiskLevel:
        """Applies asymmetric exit margins to avoid oscillations."""
        # Safety override
        if predicted_rul <= self.thresholds.critical_rul_override:
            return RiskLevel.CRITICAL

        current = self.current_state

        if current == RiskLevel.CRITICAL:
            if risk_score < self.thresholds.exit_critical_score:
                if risk_score < self.thresholds.exit_warning_score:
                    if risk_score < self.thresholds.exit_monitor_score:
                        return RiskLevel.NORMAL
                    return RiskLevel.MONITOR
                return RiskLevel.WARNING
            return RiskLevel.CRITICAL

        elif current == RiskLevel.WARNING:
            if risk_score >= self.thresholds.enter_critical_score:
                return RiskLevel.CRITICAL
            elif risk_score < self.thresholds.exit_warning_score:
                if risk_score < self.thresholds.exit_monitor_score:
                    return RiskLevel.NORMAL
                return RiskLevel.MONITOR
            return RiskLevel.WARNING

        elif current == RiskLevel.MONITOR:
            if risk_score >= self.thresholds.enter_critical_score:
                return RiskLevel.CRITICAL
            elif risk_score >= self.thresholds.enter_warning_score:
                return RiskLevel.WARNING
            elif risk_score < self.thresholds.exit_monitor_score:
                return RiskLevel.NORMAL
            return RiskLevel.MONITOR

        else:  # NORMAL
            return instant_level

    def _get_required_persistence(self, from_state: RiskLevel, to_state: RiskLevel) -> int:
        """Escalations require 2 cycles; de-escalations require 3 cycles."""
        level_order = {
            RiskLevel.NORMAL: 0,
            RiskLevel.MONITOR: 1,
            RiskLevel.WARNING: 2,
            RiskLevel.CRITICAL: 3
        }
        if level_order[to_state] > level_order[from_state]:
            return self.thresholds.escalation_persistence_cycles
        else:
            return self.thresholds.deescalation_persistence_cycles
