"""
backend/app/services/data_sources/manager.py

Central Coordinator and Registry for Industrial Telemetry Data Sources in FactoryMind AI.

Manages adapter lifecycles, active source selection (defaulting to NASA C-MAPSS FD001 Simulation),
connector configurations, telemetry ingestion dispatch, and connection health.
"""

from typing import Dict, List, Optional, Any, Tuple
import logging

from backend.app.schemas.normalized_telemetry import (
    DataSourceType,
    DataSourceStatus,
    DataSourceInfo,
    RestConnectorConfig,
    MqttConnectorConfig,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    NormalizedTelemetryFrame,
    MLCompatibilityReport
)
from backend.app.services.data_sources.base import BaseDataSourceAdapter
from backend.app.services.data_sources.cmapss_adapter import CMAPSSDataSourceAdapter
from backend.app.services.data_sources.rest_adapter import RestApiDataSourceAdapter
from backend.app.services.data_sources.mqtt_adapter import MqttDataSourceAdapter
from backend.app.services.data_sources.csv_adapter import CsvFileDataSourceAdapter
from backend.app.services.ml_compatibility import get_ml_compatibility_service
from ml.inference import get_inference_engine

logger = logging.getLogger("factorymind.data_sources.manager")


class DataSourceManager:
    """
    Singleton manager tracking all data source connectors and active data stream routing.
    """

    def __init__(self):
        self._sources: Dict[str, BaseDataSourceAdapter] = {}
        
        # 1. Default Demonstration Source: NASA C-MAPSS Simulation (CONNECTED)
        self.cmapss_adapter = CMAPSSDataSourceAdapter()
        self._sources[self.cmapss_adapter.source_id] = self.cmapss_adapter

        # 2. Real Industrial REST API Connector (NOT_CONFIGURED by default)
        self.rest_adapter = RestApiDataSourceAdapter()
        self._sources[self.rest_adapter.source_id] = self.rest_adapter

        # 3. Real Industrial MQTT / IoT Connector (NOT_CONFIGURED by default)
        self.mqtt_adapter = MqttDataSourceAdapter()
        self._sources[self.mqtt_adapter.source_id] = self.mqtt_adapter

        # 4. CSV & File Ingestion Adapter (CONNECTED / READY)
        self.csv_adapter = CsvFileDataSourceAdapter()
        self._sources[self.csv_adapter.source_id] = self.csv_adapter

        # Active data source ID defaults to C-MAPSS simulation
        self._active_source_id: str = self.cmapss_adapter.source_id
        self._ml_compatibility_service = get_ml_compatibility_service()

    @property
    def active_source_id(self) -> str:
        return self._active_source_id

    def get_source(self, source_id: str) -> Optional[BaseDataSourceAdapter]:
        """Retrieves a data source adapter by its unique identifier."""
        return self._sources.get(source_id)

    def get_active_source(self) -> BaseDataSourceAdapter:
        """Returns the currently active data source adapter."""
        return self._sources.get(self._active_source_id, self.cmapss_adapter)

    def list_sources(self) -> List[DataSourceInfo]:
        """Returns safe, secret-masked summary of all registered data sources."""
        result = []
        for s_id, adapter in self._sources.items():
            is_active = (s_id == self._active_source_id)
            result.append(adapter.get_info(is_active=is_active))
        return result

    def get_active_source_info(self) -> DataSourceInfo:
        """Returns safe summary of the active data source."""
        adapter = self.get_active_source()
        return adapter.get_info(is_active=True)

    def set_active_source(self, source_id: str) -> Tuple[bool, str]:
        """
        Switches the active telemetry data source.
        Returns:
            (success, message)
        """
        if source_id not in self._sources:
            return False, f"Unknown data source ID: '{source_id}'."

        adapter = self._sources[source_id]
        self._active_source_id = source_id
        logger.info(f"Active data source switched to '{adapter.name}' ({source_id})")
        return True, f"Active data source switched to {adapter.name}."

    def configure_rest_connector(self, config: RestConnectorConfig) -> Tuple[bool, str]:
        """Updates and validates REST API connector settings."""
        self.rest_adapter.configure(config)
        return True, "REST API Connector configuration saved."

    def configure_mqtt_connector(self, config: MqttConnectorConfig) -> Tuple[bool, str]:
        """Updates and validates MQTT broker settings."""
        self.mqtt_adapter.configure(config)
        return True, "MQTT Connector configuration saved."

    async def test_connection(self, source_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Tests connection for a specific connector.
        Returns:
            (success, message, details_dict)
        """
        if source_id not in self._sources:
            return False, f"Data source '{source_id}' not found.", {}

        adapter = self._sources[source_id]
        if adapter.source_type == DataSourceType.CMAPSS_SIMULATION:
            return True, "NASA C-MAPSS FD001 dataset loaded and simulation engine ready.", {"status": "CONNECTED"}

        if adapter.source_type == DataSourceType.CSV_IMPORT:
            return True, "CSV file ingestion engine is operational and ready for uploads.", {"status": "CONNECTED"}

        if adapter.source_type == DataSourceType.REST_API:
            if not self.rest_adapter.config.endpoint_url:
                return False, "REST API endpoint URL is not configured.", {"status": "NOT_CONFIGURED"}
            connected = await self.rest_adapter.connect()
            if connected:
                return True, f"Successfully verified connection to REST endpoint: {self.rest_adapter.config.endpoint_url}", {"status": "CONNECTED"}
            else:
                return False, f"REST connection check failed: {self.rest_adapter.error_message}", {"status": "ERROR"}

        if adapter.source_type == DataSourceType.MQTT_IOT:
            if not self.mqtt_adapter.config.broker_url:
                return False, "MQTT broker URL is not configured.", {"status": "NOT_CONFIGURED"}
            connected = await self.mqtt_adapter.connect()
            if connected:
                return True, f"Successfully verified connection to MQTT broker: {self.mqtt_adapter.config.broker_url}:{self.mqtt_adapter.config.port}", {"status": "CONNECTED"}
            else:
                return False, f"MQTT connection check failed: {self.mqtt_adapter.error_message}", {"status": "ERROR"}

        return False, "Unsupported source type for connection testing.", {}

    async def ingest_telemetry_payload(
        self,
        request: TelemetryIngestRequest
    ) -> TelemetryIngestResponse:
        """
        Validates, normalizes, evaluates ML compatibility, and optionally triggers ML inference.
        """
        adapter = self.get_active_source()
        
        # Normalize and validate frame
        frame, errors = adapter.normalize_payload(
            machine_id=request.machine_id,
            raw_readings=request.raw_readings,
            timestamp=request.timestamp,
            cycle=request.cycle,
            external_machine_id=request.external_machine_id,
            operating_settings=request.operating_settings,
            units=request.units
        )

        if not frame:
            raise ValueError(f"Telemetry ingestion rejected: {'; '.join(errors)}")

        # Evaluate ML Compatibility
        ml_report = self._ml_compatibility_service.evaluate_frame_compatibility(frame)

        # Run ML inference ONLY if strictly compatible
        inference_result = None
        if ml_report.is_rul_predictable:
            try:
                row_dict = self._ml_compatibility_service.convert_frame_to_model_row(frame)
                if row_dict:
                    import pandas as pd
                    df_row = pd.DataFrame([row_dict])
                    engine = get_inference_engine()
                    res = engine.predict_cycle(df_row)
                    inference_result = {
                        "cycle": res.cycle,
                        "rul_estimate": res.rul_estimate,
                        "anomaly_score": res.anomaly_score,
                        "anomaly_status": res.anomaly_status,
                        "health_index": res.health_index,
                        "risk_score": res.risk_score,
                        "risk_level": res.risk_level,
                        "contributing_signals": res.contributing_signals
                    }
            except Exception as e:
                logger.warning(f"Inference execution on compatible telemetry failed: {e}")

        return TelemetryIngestResponse(
            status="SUCCESS",
            message="Telemetry normalized and validated successfully.",
            normalized_frame=frame,
            ml_compatibility=ml_report,
            inference_result=inference_result
        )


# Singleton manager
_manager_instance: Optional[DataSourceManager] = None


def get_data_source_manager() -> DataSourceManager:
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = DataSourceManager()
    return _manager_instance
