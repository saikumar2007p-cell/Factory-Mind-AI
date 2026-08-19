"""
backend/app/schemas/normalized_telemetry.py

Normalized Telemetry Model and Data Quality Schemas for FactoryMind AI.
Establishes a universal standard internal telemetry contract for all industrial data sources.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


class DataQuality(str, Enum):
    GOOD = "GOOD"
    WARNING = "WARNING"
    INVALID = "INVALID"
    STALE = "STALE"
    MISSING = "MISSING"


class DataSourceType(str, Enum):
    CMAPSS_SIMULATION = "CMAPSS_SIMULATION"
    REST_API = "REST_API"
    MQTT_IOT = "MQTT_IOT"
    CSV_IMPORT = "CSV_IMPORT"


class DataSourceStatus(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    ERROR = "ERROR"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class MLCompatibilityStatus(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    PARTIALLY_COMPATIBLE = "PARTIALLY_COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class NormalizedSensorReading(BaseModel):
    sensor_id: str = Field(description="Internal canonical sensor ID e.g. s_4 or T50")
    canonical_name: str = Field(description="Canonical measurement name e.g. T50, P30, Nf")
    raw_name: Optional[str] = Field(default=None, description="Original external sensor label from source system")
    value: float = Field(description="Validated finite numerical sensor value")
    raw_value: Optional[float] = Field(default=None, description="Original un-normalized value before unit conversion")
    unit: str = Field(description="Target normalized physical unit e.g. °R, psia, rpm, lbm/s")
    raw_unit: Optional[str] = Field(default=None, description="Source unit as reported by external system")
    subsystem: str = Field(default="Unknown Subsystem", description="Machine subsystem associated with this sensor")
    quality: DataQuality = Field(default=DataQuality.GOOD, description="Sensor data quality status")
    notes: Optional[str] = None


class NormalizedTelemetryFrame(BaseModel):
    machine_id: str = Field(description="Canonical FactoryMind machine/unit identifier")
    external_machine_id: Optional[str] = Field(default=None, description="External equipment identifier")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Observation timestamp")
    cycle: Optional[int] = Field(default=None, description="Operational cycle or sequence number")
    source_type: DataSourceType = Field(description="Type of data source emitting this frame")
    source_id: str = Field(default="default", description="Data source instance identifier")
    readings: Dict[str, NormalizedSensorReading] = Field(default_factory=dict, description="Dictionary of canonical_name -> reading")
    operating_settings: Dict[str, float] = Field(default_factory=dict, description="Operating regime/condition settings")
    frame_quality: DataQuality = Field(default=DataQuality.GOOD, description="Overall frame quality")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Extensible telemetry metadata")

    model_config = ConfigDict(from_attributes=True)


class MLCompatibilityReport(BaseModel):
    machine_id: str
    status: MLCompatibilityStatus
    total_required_channels: int = 21
    available_compatible_channels: int
    missing_channels: List[str] = []
    is_rul_predictable: bool
    is_anomaly_detectable: bool
    message: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DataSourceInfo(BaseModel):
    source_id: str
    name: str
    source_type: DataSourceType
    status: DataSourceStatus
    is_active: bool
    is_simulation: bool
    last_data_received: Optional[datetime] = None
    is_stale: bool = False
    description: str
    details: Dict[str, Any] = Field(default_factory=dict)


class RestConnectorConfig(BaseModel):
    endpoint_url: str = Field(default="", description="Industrial REST API endpoint")
    polling_interval_seconds: float = Field(default=5.0, ge=0.5, le=3600.0)
    auth_type: str = Field(default="none", description="'none', 'api_key', 'bearer_token', 'basic'")
    api_key: Optional[str] = Field(default=None, description="Secret API key (masked on output)")
    bearer_token: Optional[str] = Field(default=None, description="Bearer token (masked on output)")
    username: Optional[str] = None
    password: Optional[str] = Field(default=None, description="Password (masked on output)")
    headers: Dict[str, str] = Field(default_factory=dict)
    is_enabled: bool = False


class MqttConnectorConfig(BaseModel):
    broker_url: str = Field(default="", description="MQTT broker hostname or IP")
    port: int = Field(default=1883, ge=1, le=65535)
    topic: str = Field(default="factory/telemetry/#", description="Telemetry topic subscription")
    client_id: str = Field(default="factorymind-edge-client")
    qos: int = Field(default=1, ge=0, le=2)
    username: Optional[str] = None
    password: Optional[str] = Field(default=None, description="MQTT password (masked on output)")
    tls_enabled: bool = False
    is_enabled: bool = False


class SensorMappingItem(BaseModel):
    external_name: str
    canonical_sensor_id: str
    canonical_name: str
    target_unit: str
    source_unit: Optional[str] = None
    subsystem: str


class SensorMappingConfig(BaseModel):
    mappings: Dict[str, str] = Field(default_factory=dict, description="external_name -> canonical_id or canonical_name")
    unit_mappings: Dict[str, str] = Field(default_factory=dict, description="sensor_name -> explicit source_unit")


class TelemetryIngestRequest(BaseModel):
    machine_id: str = Field(description="Target machine identifier")
    external_machine_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    cycle: Optional[int] = None
    source_type: DataSourceType = DataSourceType.REST_API
    raw_readings: Dict[str, Any] = Field(description="Key-value mapping of external sensor names to raw values")
    operating_settings: Optional[Dict[str, float]] = None
    units: Optional[Dict[str, str]] = None


class TelemetryIngestResponse(BaseModel):
    status: str
    message: str
    normalized_frame: NormalizedTelemetryFrame
    ml_compatibility: MLCompatibilityReport
    inference_result: Optional[Dict[str, Any]] = None


class FileUploadIngestResponse(BaseModel):
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    detected_columns: List[str]
    mapped_channels: Dict[str, str]
    unmapped_columns: List[str]
    ml_compatibility: MLCompatibilityReport
    sample_normalized_frames: List[NormalizedTelemetryFrame]
    quarantine_errors: List[str]

