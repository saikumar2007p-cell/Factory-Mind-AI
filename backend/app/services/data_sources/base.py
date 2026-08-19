"""
backend/app/services/data_sources/base.py

Abstract Base Class for FactoryMind AI Industrial Data Source Adapters.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import logging

from backend.app.schemas.normalized_telemetry import (
    DataSourceType,
    DataSourceStatus,
    DataSourceInfo,
    NormalizedTelemetryFrame
)
from backend.app.services.data_validator import DataValidator

logger = logging.getLogger("factorymind.adapters.base")


def mask_secret(secret_val: Optional[str]) -> str:
    """Masks secret keys and passwords for safe client presentation."""
    if not secret_val or str(secret_val).strip() == "":
        return "••••••••••" if secret_val else ""
    return "••••••••••"


class BaseDataSourceAdapter(ABC):
    """
    Abstract contract for industrial telemetry sources.
    """

    def __init__(
        self,
        source_id: str,
        name: str,
        source_type: DataSourceType,
        is_simulation: bool = False,
        stale_threshold_seconds: float = 60.0
    ):
        self.source_id = source_id
        self.name = name
        self.source_type = source_type
        self.is_simulation = is_simulation
        self.stale_threshold_seconds = stale_threshold_seconds
        
        self.status: DataSourceStatus = DataSourceStatus.NOT_CONFIGURED
        self.last_data_received: Optional[datetime] = None
        self.validator = DataValidator(stale_threshold_seconds=stale_threshold_seconds)
        self.error_message: Optional[str] = None

    def is_stale(self) -> bool:
        """Evaluates whether the last received telemetry timestamp is older than threshold."""
        if self.last_data_received is None:
            return False
        elapsed = (datetime.now(timezone.utc) - self.last_data_received).total_seconds()
        return elapsed > self.stale_threshold_seconds

    @abstractmethod
    async def connect(self) -> bool:
        """Establishes connection to the data source."""
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """Disconnects cleanly from the data source."""
        pass

    @abstractmethod
    def get_info(self, is_active: bool = False) -> DataSourceInfo:
        """Returns safe, secret-masked summary of data source state."""
        pass

    def record_heartbeat(self, timestamp: Optional[datetime] = None):
        """Updates last seen telemetry timestamp."""
        self.last_data_received = timestamp or datetime.now(timezone.utc)

    def normalize_payload(
        self,
        machine_id: str,
        raw_readings: Dict[str, Any],
        timestamp: Optional[Any] = None,
        cycle: Optional[int] = None,
        external_machine_id: Optional[str] = None,
        operating_settings: Optional[Dict[str, float]] = None,
        units: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Optional[NormalizedTelemetryFrame], List[str]]:
        """
        Passes raw telemetry into the validation & normalization engine.
        """
        frame, errors = self.validator.validate_and_normalize_frame(
            machine_id=machine_id,
            raw_readings=raw_readings,
            timestamp=timestamp,
            cycle=cycle,
            source_type=self.source_type,
            source_id=self.source_id,
            external_machine_id=external_machine_id,
            operating_settings=operating_settings,
            units=units,
            metadata=metadata
        )
        if frame:
            self.record_heartbeat(frame.timestamp)
        return frame, errors
