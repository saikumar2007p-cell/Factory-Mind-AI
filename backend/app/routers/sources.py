"""
backend/app/routers/sources.py

Data Sources and Industrial Telemetry Ingestion Router for FactoryMind AI.

Manages data source connectors (NASA C-MAPSS Simulation, Industrial REST API, MQTT/IoT, CSV File Ingestion),
sensor taxonomy mappings, and validated telemetry ingestion.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, UploadFile, File, Form, status
from pydantic import BaseModel, Field

from backend.app.schemas.normalized_telemetry import (
    DataSourceType,
    DataSourceStatus,
    DataSourceInfo,
    RestConnectorConfig,
    MqttConnectorConfig,
    SensorMappingConfig,
    TelemetryIngestRequest,
    TelemetryIngestResponse,
    FileUploadIngestResponse,
    MLCompatibilityReport
)
from backend.app.services.data_sources.manager import get_data_source_manager
from backend.app.services.sensor_mapping import get_sensor_mapping_service
from backend.app.services.ml_compatibility import get_ml_compatibility_service

from backend.app.security import AuthUser, require_role
from backend.app.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/sources", tags=["Data Sources & Ingestion"])

# Strictly Admin-only configuration access
verify_admin_access = require_role(["admin"])


class ConfigureSourceRequest(BaseModel):
    source_id: str
    rest_config: Optional[RestConnectorConfig] = None
    mqtt_config: Optional[MqttConnectorConfig] = None


class TestConnectionResponse(BaseModel):
    source_id: str
    success: bool
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class SetActiveSourceRequest(BaseModel):
    source_id: str


@router.get("", response_model=List[DataSourceInfo])
async def list_all_data_sources():
    """
    Lists all available data source connectors with connection state and secret-masked details.
    """
    manager = get_data_source_manager()
    return manager.list_sources()


@router.get("/active", response_model=DataSourceInfo)
async def get_active_data_source():
    """
    Retrieves the currently active data source (defaults to NASA C-MAPSS FD001 Simulation).
    """
    manager = get_data_source_manager()
    return manager.get_active_source_info()


@router.post("/set-active/{source_id}", response_model=Dict[str, Any], dependencies=[Depends(verify_admin_access)])
async def set_active_data_source(source_id: str):
    """
    Switches the platform's active data source. Requires administrator authorization.
    """
    manager = get_data_source_manager()
    success, msg = manager.set_active_source(source_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg
        )
    return {
        "status": "SUCCESS",
        "message": msg,
        "active_source": manager.get_active_source_info()
    }


@router.post("/configure", response_model=Dict[str, Any], dependencies=[Depends(verify_admin_access)])
async def configure_data_source(request: ConfigureSourceRequest):
    """
    Configures industrial REST or MQTT connectors. Requires administrator authorization.
    Credentials and secrets are safely stored server-side and never echoed in plain text.
    """
    manager = get_data_source_manager()

    if request.source_id == "rest_api_connector" and request.rest_config:
        manager.configure_rest_connector(request.rest_config)
        return {
            "status": "SUCCESS",
            "message": "REST API connector configuration saved successfully.",
            "source_info": manager.rest_adapter.get_info()
        }
    elif request.source_id == "mqtt_iot_connector" and request.mqtt_config:
        manager.configure_mqtt_connector(request.mqtt_config)
        return {
            "status": "SUCCESS",
            "message": "MQTT connector configuration saved successfully.",
            "source_info": manager.mqtt_adapter.get_info()
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid configuration request for source ID '{request.source_id}'."
        )


@router.post("/test-connection/{source_id}", response_model=TestConnectionResponse)
async def test_data_source_connection(source_id: str):
    """
    Performs a live connectivity test for the specified connector without modifying the active source.
    """
    manager = get_data_source_manager()
    success, msg, details = await manager.test_connection(source_id)
    return TestConnectionResponse(
        source_id=source_id,
        success=success,
        message=msg,
        details=details
    )


@router.post("/ingest", response_model=TelemetryIngestResponse)
async def ingest_telemetry_frame(request: TelemetryIngestRequest):
    """
    Ingests an external telemetry frame, normalizes readings into canonical format,
    validates numeric boundaries, and checks ML compatibility against the C-MAPSS model.
    """
    manager = get_data_source_manager()
    try:
        response = await manager.ingest_telemetry_payload(request)
        return response
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Telemetry ingestion failed: {str(e)}"
        )


@router.post("/upload-file", response_model=FileUploadIngestResponse)
async def upload_telemetry_file(
    file: UploadFile = File(...),
    default_machine_id: str = Form("EXT_UNIT_01"),
    db: AsyncSession = Depends(get_db)
):
    """
    Uploads a batch CSV/TSV telemetry file, parses columns, maps channels,
    evaluates data quality, validates prognostic ML compatibility,
    and stages unknown machine registrations for Administrator review.
    """
    if not file.filename.endswith((".csv", ".tsv", ".txt")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV, TSV, or TXT tabular files are supported."
        )

    manager = get_data_source_manager()
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty."
        )

    try:
        result = manager.csv_adapter.process_csv_file(
            file_content=content,
            filename=file.filename,
            default_machine_id=default_machine_id
        )

        # Check if the target machine exists in database; if unknown, stage for admin review
        from backend.app.services.storage_service import StorageService
        from backend.app.services.machine_registration_service import MachineRegistrationService
        from backend.app.schemas.normalized_telemetry import MachineRegistrationRequestSummary

        storage = StorageService(db)
        reg_service = MachineRegistrationService(db)

        # Check unit number if numeric or search by name
        machine = None
        if default_machine_id.isdigit():
            machine = await storage.get_machine_by_unit(int(default_machine_id))
        if not machine:
            # Check all machines to match by name or unit
            all_m = await storage.get_all_machines()
            for m in all_m:
                if str(m.unit_number) == str(default_machine_id) or m.name.lower() == default_machine_id.lower():
                    machine = m
                    break

        pending_reviews = []
        if not machine and result.valid_rows > 0:
            # Stage for administrator review
            sample_data_dicts = [
                {
                    "cycle": f.cycle,
                    "readings": {k: v.value for k, v in f.readings.items()}
                }
                for f in result.sample_normalized_frames[:5]
            ]
            req = await reg_service.stage_upload_for_review(
                requested_machine_id=default_machine_id,
                source_filename=file.filename,
                source_row_count=result.valid_rows,
                detected_columns=result.detected_columns,
                sample_data=sample_data_dicts
            )
            await db.commit()
            pending_reviews.append(
                MachineRegistrationRequestSummary(
                    request_id=req.id,
                    requested_machine_id=req.requested_machine_id,
                    source_filename=req.source_filename,
                    source_row_count=req.source_row_count,
                    detected_columns=req.detected_columns,
                    status=req.status,
                    requested_at=req.requested_at
                )
            )

        result.pending_machine_reviews = pending_reviews
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File processing failed: {str(e)}"
        )


@router.get("/mappings", response_model=Dict[str, Any])
async def get_sensor_mappings():
    """
    Retrieves the 21 canonical turbofan sensor channel taxonomy and active alias mappings.
    """
    mapping_service = get_sensor_mapping_service()
    return {
        "canonical_channels": mapping_service.get_all_canonical_definitions(),
        "active_aliases": mapping_service.get_active_mappings()
    }


@router.post("/mappings", response_model=Dict[str, Any], dependencies=[Depends(verify_admin_access)])
async def update_sensor_mappings(config: SensorMappingConfig):
    """
    Registers custom external sensor aliases. Requires administrator authorization.
    """
    mapping_service = get_sensor_mapping_service()
    mapping_service.register_custom_mappings(config.mappings)
    return {
        "status": "SUCCESS",
        "message": f"Successfully registered {len(config.mappings)} sensor alias mappings.",
        "active_aliases": mapping_service.get_active_mappings()
    }


@router.get("/compatibility/{machine_id}", response_model=MLCompatibilityReport)
async def check_machine_ml_compatibility(machine_id: str):
    """
    Checks prognostic ML schema compatibility for a machine or current telemetry.
    Supports both C-MAPSS 21-channel simulation and tiered customer sensor sets.
    """
    manager = get_data_source_manager()
    adapter = manager.get_active_source()
    compat_service = get_ml_compatibility_service()

    # If C-MAPSS simulation, evaluate full C-MAPSS compatibility
    if adapter.source_type == DataSourceType.CMAPSS_SIMULATION:
        row_dict = {"unit_number": machine_id, "time_cycle": 1}
        for i in range(1, 22):
            row_dict[f"s_{i}"] = 500.0
        frame = manager.cmapss_adapter.convert_cmapss_row_to_frame(row_dict)
        return compat_service.evaluate_frame_compatibility(frame)

    # For customer / external sources, use tiered evaluation
    return compat_service.evaluate_customer_frame_compatibility(
        machine_id=str(machine_id),
        available_sensor_ids=[]
    )

