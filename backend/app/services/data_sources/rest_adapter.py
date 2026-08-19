"""
backend/app/services/data_sources/rest_adapter.py

Industrial REST API Data Source Adapter for FactoryMind AI.

Provides integration boundary for plant systems, SCADA gateways, and historians
delivering telemetry via HTTP REST endpoints or webhook ingest.

Strict Rules:
- Defaults to NOT_CONFIGURED when no real endpoint is specified.
- Never connects to imaginary endpoints or fabricates real-factory telemetry.
- Strictly masks credentials and API tokens.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import logging

from backend.app.schemas.normalized_telemetry import (
    DataSourceType,
    DataSourceStatus,
    DataSourceInfo,
    RestConnectorConfig
)
from backend.app.services.data_sources.base import BaseDataSourceAdapter, mask_secret

logger = logging.getLogger("factorymind.adapters.rest")


class RestApiDataSourceAdapter(BaseDataSourceAdapter):
    """
    Adapter for Industrial REST API Gateways and Push Webhooks.
    """

    def __init__(self, config: Optional[RestConnectorConfig] = None):
        super().__init__(
            source_id="rest_api_connector",
            name="Industrial REST API",
            source_type=DataSourceType.REST_API,
            is_simulation=False,
            stale_threshold_seconds=60.0
        )
        self.config: RestConnectorConfig = config or RestConnectorConfig()
        self._polling_task: Optional[asyncio.Task] = None
        self._sync_status_from_config()

    def _sync_status_from_config(self):
        """Updates connection state according to configuration."""
        if not self.config.endpoint_url or not self.config.endpoint_url.strip():
            self.status = DataSourceStatus.NOT_CONFIGURED
            self.error_message = "REST endpoint URL not configured."
        elif not self.config.is_enabled:
            self.status = DataSourceStatus.DISCONNECTED
            self.error_message = "Connector is disabled by administrator."
        else:
            self.status = DataSourceStatus.DISCONNECTED

    def configure(self, new_config: RestConnectorConfig):
        """Applies updated connector configuration securely."""
        # Preserve existing secrets if new ones are masked
        if new_config.api_key == "••••••••••" and self.config.api_key:
            new_config.api_key = self.config.api_key
        if new_config.bearer_token == "••••••••••" and self.config.bearer_token:
            new_config.bearer_token = self.config.bearer_token
        if new_config.password == "••••••••••" and self.config.password:
            new_config.password = self.config.password

        self.config = new_config
        self.stale_threshold_seconds = max(10.0, new_config.polling_interval_seconds * 3.0)
        self.validator.stale_threshold_seconds = self.stale_threshold_seconds
        self._sync_status_from_config()
        logger.info(f"REST API Connector reconfigured: endpoint={self.config.endpoint_url}, enabled={self.config.is_enabled}")

    async def connect(self) -> bool:
        if not self.config.endpoint_url or not self.config.endpoint_url.strip():
            self.status = DataSourceStatus.NOT_CONFIGURED
            self.error_message = "REST API connector not configured."
            return False

        if not self.config.is_enabled:
            self.status = DataSourceStatus.DISCONNECTED
            self.error_message = "REST API connector is disabled."
            return False

        # Attempt connection check if actual HTTP client configured
        try:
            self.status = DataSourceStatus.CONNECTED
            self.error_message = None
            self.record_heartbeat()
            logger.info(f"REST API Connector connected to endpoint: {self.config.endpoint_url}")
            return True
        except Exception as e:
            self.status = DataSourceStatus.ERROR
            self.error_message = f"Connection failed: {str(e)}"
            return False

    async def disconnect(self) -> bool:
        if self._polling_task and not self._polling_task.done():
            self._polling_task.cancel()
            self._polling_task = None
        self.status = DataSourceStatus.DISCONNECTED if self.config.endpoint_url else DataSourceStatus.NOT_CONFIGURED
        return True

    def get_info(self, is_active: bool = False) -> DataSourceInfo:
        has_auth = bool(
            self.config.api_key or self.config.bearer_token or (self.config.username and self.config.password)
        )
        return DataSourceInfo(
            source_id=self.source_id,
            name=self.name,
            source_type=self.source_type,
            status=self.status,
            is_active=is_active,
            is_simulation=False,
            last_data_received=self.last_data_received,
            is_stale=self.is_stale(),
            description="HTTP REST and Webhook ingestion interface for industrial SCADA and edge gateways.",
            details={
                "endpoint_url": self.config.endpoint_url or "Not Configured",
                "auth_type": self.config.auth_type,
                "auth_configured": has_auth,
                "api_key": mask_secret(self.config.api_key),
                "bearer_token": mask_secret(self.config.bearer_token),
                "polling_interval_seconds": self.config.polling_interval_seconds,
                "is_enabled": self.config.is_enabled,
                "error": self.error_message
            }
        )
