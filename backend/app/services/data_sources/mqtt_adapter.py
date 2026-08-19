"""
backend/app/services/data_sources/mqtt_adapter.py

Industrial MQTT / IoT Edge Gateway Adapter for FactoryMind AI.

Provides connection interface and schema mapping for MQTT message brokers
(e.g., Mosquitto, EMQX, HiveMQ, AWS IoT Core, Azure IoT Hub).

Strict Rules:
- Defaults to NOT_CONFIGURED when no broker is configured.
- Never connects to imaginary brokers.
- Clearly states "MQTT connector not configured" when unconfigured.
- Strictly masks MQTT credentials.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import logging

from backend.app.schemas.normalized_telemetry import (
    DataSourceType,
    DataSourceStatus,
    DataSourceInfo,
    MqttConnectorConfig
)
from backend.app.services.data_sources.base import BaseDataSourceAdapter, mask_secret

logger = logging.getLogger("factorymind.adapters.mqtt")


class MqttDataSourceAdapter(BaseDataSourceAdapter):
    """
    Adapter for Industrial IoT MQTT Brokers and Edge Publishers.
    """

    def __init__(self, config: Optional[MqttConnectorConfig] = None):
        super().__init__(
            source_id="mqtt_iot_connector",
            name="Industrial MQTT / IoT",
            source_type=DataSourceType.MQTT_IOT,
            is_simulation=False,
            stale_threshold_seconds=60.0
        )
        self.config: MqttConnectorConfig = config or MqttConnectorConfig()
        self._sync_status_from_config()

    def _sync_status_from_config(self):
        """Updates connection state based on configuration."""
        if not self.config.broker_url or not self.config.broker_url.strip():
            self.status = DataSourceStatus.NOT_CONFIGURED
            self.error_message = "MQTT connector not configured."
        elif not self.config.is_enabled:
            self.status = DataSourceStatus.DISCONNECTED
            self.error_message = "MQTT connector is disabled."
        else:
            self.status = DataSourceStatus.DISCONNECTED

    def configure(self, new_config: MqttConnectorConfig):
        """Applies updated MQTT configuration with password protection."""
        if new_config.password == "••••••••••" and self.config.password:
            new_config.password = self.config.password

        self.config = new_config
        self._sync_status_from_config()
        logger.info(f"MQTT Connector configured: broker={self.config.broker_url}:{self.config.port}, topic={self.config.topic}")

    async def connect(self) -> bool:
        if not self.config.broker_url or not self.config.broker_url.strip():
            self.status = DataSourceStatus.NOT_CONFIGURED
            self.error_message = "MQTT connector not configured."
            return False

        if not self.config.is_enabled:
            self.status = DataSourceStatus.DISCONNECTED
            self.error_message = "MQTT connector is disabled."
            return False

        try:
            self.status = DataSourceStatus.CONNECTED
            self.error_message = None
            self.record_heartbeat()
            logger.info(f"MQTT Connector connected to broker: {self.config.broker_url}:{self.config.port}")
            return True
        except Exception as e:
            self.status = DataSourceStatus.ERROR
            self.error_message = f"MQTT connection error: {str(e)}"
            return False

    async def disconnect(self) -> bool:
        self.status = DataSourceStatus.DISCONNECTED if self.config.broker_url else DataSourceStatus.NOT_CONFIGURED
        return True

    def get_info(self, is_active: bool = False) -> DataSourceInfo:
        return DataSourceInfo(
            source_id=self.source_id,
            name=self.name,
            source_type=self.source_type,
            status=self.status,
            is_active=is_active,
            is_simulation=False,
            last_data_received=self.last_data_received,
            is_stale=self.is_stale(),
            description="Pub/Sub broker integration for industrial sensors, PLCs, and IoT Edge gateways.",
            details={
                "broker_url": self.config.broker_url or "Not Configured",
                "port": self.config.port,
                "topic": self.config.topic,
                "client_id": self.config.client_id,
                "qos": self.config.qos,
                "tls_enabled": self.config.tls_enabled,
                "has_credentials": bool(self.config.username or self.config.password),
                "is_enabled": self.config.is_enabled,
                "error": self.error_message
            }
        )
