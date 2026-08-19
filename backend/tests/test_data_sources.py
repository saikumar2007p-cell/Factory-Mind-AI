"""
backend/tests/test_data_sources.py

Comprehensive Stage 7 Test Suite for FactoryMind AI:
- Real-world data source integration & telemetry abstraction
- Validation & Data Quality (GOOD, WARNING, INVALID, STALE, MISSING)
- Physical unit normalization & strict un-invented limits
- Sensor taxonomy mapping & aliases
- ML feature schema compatibility (21/21 vs incomplete, zero fake predictions)
- Grounded AI evidence integration
- Data source API routes, admin security & secret protection
"""

import io
from datetime import datetime, timezone, timedelta
import pytest
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.schemas.normalized_telemetry import (
    DataQuality,
    DataSourceType,
    DataSourceStatus,
    MLCompatibilityStatus,
    RestConnectorConfig,
    MqttConnectorConfig,
    TelemetryIngestRequest
)
from backend.app.services.data_sources.manager import get_data_source_manager
from backend.app.services.data_sources.cmapss_adapter import CMAPSSDataSourceAdapter
from backend.app.services.data_sources.rest_adapter import RestApiDataSourceAdapter
from backend.app.services.data_sources.mqtt_adapter import MqttDataSourceAdapter
from backend.app.services.data_sources.csv_adapter import CsvFileDataSourceAdapter
from backend.app.services.data_validator import DataValidator
from backend.app.services.unit_normalizer import normalize_unit
from backend.app.services.sensor_mapping import get_sensor_mapping_service
from backend.app.services.ml_compatibility import get_ml_compatibility_service
from backend.app.services.evidence_builder import build_evidence_from_normalized_frame


# ==========================================
# TEST 1: C-MAPSS Simulation Continues Working
# ==========================================
def test_cmapss_simulation_adapter_connected_and_normalizes():
    adapter = CMAPSSDataSourceAdapter()
    assert adapter.status == DataSourceStatus.CONNECTED
    assert adapter.is_simulation is True

    info = adapter.get_info()
    assert info.status == DataSourceStatus.CONNECTED
    assert info.is_simulation is True
    assert "NASA C-MAPSS FD001" in info.name

    # Convert authentic C-MAPSS raw dictionary to normalized frame
    raw_row = {
        "unit_number": 1,
        "time_cycle": 50,
        "setting_1": 0.001,
        "setting_2": 0.0002,
        "setting_3": 100.0,
        "s_1": 518.67,
        "s_2": 642.35,
        "s_3": 1589.70,
        "s_4": 1400.60,
        "s_7": 554.36,
        "s_8": 2388.06,
        "s_9": 9046.19,
        "s_11": 47.47,
        "s_12": 521.66,
        "s_13": 2388.02,
        "s_14": 8138.62,
        "s_15": 8.4195,
        "s_17": 392.0,
        "s_20": 39.06,
        "s_21": 23.4190
    }
    frame = adapter.convert_cmapss_row_to_frame(raw_row)
    assert frame.machine_id == "1"
    assert frame.cycle == 50
    assert frame.source_type == DataSourceType.CMAPSS_SIMULATION
    assert "T50" in frame.readings
    assert frame.readings["T50"].value == 1400.60
    assert frame.readings["T50"].unit == "°R"
    assert frame.frame_quality == DataQuality.GOOD


# ==========================================
# TEST 2: Valid External Telemetry Normalization
# ==========================================
def test_valid_external_telemetry_normalizes_correctly():
    validator = DataValidator(stale_threshold_seconds=120.0)
    raw_payload = {
        "fan_temp": 518.67,
        "temp_lpc": 642.5,
        "motor_temperature": 1590.0,
        "egt": 1405.2,
        "fan_rpm": 2388.1,
        "core_rpm": 9050.4
    }

    frame, errors = validator.validate_and_normalize_frame(
        machine_id="PLANT_TURBINE_09",
        raw_readings=raw_payload,
        timestamp=datetime.now(timezone.utc),
        cycle=12,
        source_type=DataSourceType.REST_API,
        source_id="rest_scada_gw"
    )

    assert errors == []
    assert frame is not None
    assert frame.machine_id == "PLANT_TURBINE_09"
    assert frame.cycle == 12
    assert frame.source_type == DataSourceType.REST_API
    # Verify canonical mappings resolved
    assert "T2" in frame.readings
    assert "T30" in frame.readings
    assert "T50" in frame.readings
    assert "Nf" in frame.readings
    assert frame.readings["T50"].value == 1405.2
    assert frame.readings["T50"].canonical_name == "T50"
    assert frame.readings["T50"].sensor_id == "s_4"


# ==========================================
# TEST 3: Invalid Telemetry Rejection (NaN / Inf / Malformed)
# ==========================================
def test_invalid_telemetry_rejected_and_quarantined():
    validator = DataValidator()

    # 1. Empty machine ID
    frame, errors = validator.validate_and_normalize_frame(
        machine_id="",
        raw_readings={"T50": 1400.0}
    )
    assert frame is None
    assert any("machine_id is missing" in e for e in errors)

    # 2. NaN and Inf values quarantined
    frame2, errors2 = validator.validate_and_normalize_frame(
        machine_id="M1",
        raw_readings={
            "T50": float("nan"),
            "P30": float("inf"),
            "Nf": 2388.0
        }
    )
    assert frame2 is not None
    # Nf accepted, NaN/Inf quarantined
    assert "Nf" in frame2.readings
    assert "T50" not in frame2.readings
    assert "P30" not in frame2.readings
    assert any("Quarantined non-finite value" in e for e in errors2)

    # 3. Completely non-numeric payload rejected
    frame3, errors3 = validator.validate_and_normalize_frame(
        machine_id="M1",
        raw_readings={"T50": "invalid_string_sensor"}
    )
    assert frame3 is None
    assert any("No valid numeric sensor readings" in e for e in errors3)


# ==========================================
# TEST 4: Missing Sensors Detected
# ==========================================
def test_missing_sensors_detected_in_compatibility_check():
    validator = DataValidator()
    compat_service = get_ml_compatibility_service()

    # Telemetry with only 3 sensors
    frame, _ = validator.validate_and_normalize_frame(
        machine_id="EXT_01",
        raw_readings={"T50": 1400.0, "P30": 554.0, "Nf": 2388.0}
    )
    assert frame is not None

    report = compat_service.evaluate_frame_compatibility(frame)
    assert report.status == MLCompatibilityStatus.INCOMPATIBLE
    assert report.is_rul_predictable is False
    assert report.is_anomaly_detectable is False
    assert report.available_compatible_channels == 3
    assert len(report.missing_channels) == 18
    assert "s_1" in report.missing_channels
    assert "s_2" in report.missing_channels
    assert "RUL prediction unavailable" in report.message


# ==========================================
# TEST 5: Known Units Normalize Correctly
# ==========================================
def test_known_units_normalize_correctly():
    # 1. Celsius to Rankine: (25 + 273.15) * 1.8 = 536.67 °R
    val_r, unit_r, note_r = normalize_unit(25.0, source_unit="°C", target_dimension="temperature")
    assert round(val_r, 2) == 536.67
    assert unit_r == "°R"
    assert "Converted from Celsius" in note_r

    # 2. Fahrenheit to Rankine: 100 + 459.67 = 559.67 °R
    val_f, unit_f, _ = normalize_unit(100.0, source_unit="°F", target_dimension="temperature")
    assert round(val_f, 2) == 559.67
    assert unit_f == "°R"

    # 3. Bar to psia: 10 bar * 14.50377 = 145.038 psia
    val_bar, unit_bar, note_bar = normalize_unit(10.0, source_unit="bar", target_dimension="pressure")
    assert round(val_bar, 1) == 145.0
    assert unit_bar == "psia"
    assert "Converted from Bar" in note_bar

    # 4. Rad/s to rpm: 100 rad/s * 60 / (2*pi) = 954.93 rpm
    val_rad, unit_rad, _ = normalize_unit(100.0, source_unit="rad/s", target_dimension="speed")
    assert round(val_rad, 1) == 954.9
    assert unit_rad == "rpm"

    # 5. kg/s to lbm/s: 10 kg/s * 2.20462 = 22.046 lbm/s
    val_flow, unit_flow, _ = normalize_unit(10.0, source_unit="kg/s", target_dimension="flow")
    assert round(val_flow, 2) == 22.05
    assert unit_flow == "lbm/s"


# ==========================================
# TEST 6: Unknown Units Reported As Unavailable (No Guesswork)
# ==========================================
def test_unknown_or_missing_units_reported_as_unavailable():
    # When source unit is None/empty
    val, unit, note = normalize_unit(1500.0, source_unit=None, target_dimension="temperature")
    assert val == 1500.0
    assert unit == "Unit unavailable"
    assert "Source unit was not provided" in note

    val2, unit2, note2 = normalize_unit(1500.0, source_unit="", target_dimension="pressure")
    assert unit2 == "Unit unavailable"

    # When source unit is completely unrecognized (e.g. "parsec")
    val3, unit3, note3 = normalize_unit(1500.0, source_unit="unknown_industrial_metric", target_dimension="temperature")
    assert val3 == 1500.0
    assert unit3 == "unknown_industrial_metric"
    assert "Unknown conversion" in note3


# ==========================================
# TEST 7: Physical Plausibility Bounds & "Range Unavailable"
# ==========================================
def test_physical_plausibility_and_range_unavailable_rule():
    validator = DataValidator()

    # Rule: Never invent physical operating limits. Use only documented limits;
    # if no validated range exists, report "Range unavailable" instead of rejecting.
    raw_readings = {
        "T50": 1400.0,                     # Documented baseline: 1200-1600 °R
        "vibration_bearing_front": 4.2      # Unmapped/custom sensor without documented baseline
    }
    frame, errors = validator.validate_and_normalize_frame(
        machine_id="TURBO_01",
        raw_readings=raw_readings
    )
    assert errors == []
    assert frame is not None
    assert "T50" in frame.readings
    assert "Within documented range" in frame.readings["T50"].notes

    # Custom sensor accepted with "Range unavailable" note (NOT rejected or guessed)
    assert "vibration_bearing_front" in frame.readings
    vib_reading = frame.readings["vibration_bearing_front"]
    assert vib_reading.value == 4.2
    assert "Range unavailable" in vib_reading.notes
    assert vib_reading.quality == DataQuality.GOOD


# ==========================================
# TEST 8: Stale Data Detection
# ==========================================
def test_stale_data_detection():
    validator = DataValidator(stale_threshold_seconds=30.0)

    # Timestamp 10 minutes ago
    old_time = datetime.now(timezone.utc) - timedelta(minutes=10)
    frame, errors = validator.validate_and_normalize_frame(
        machine_id="M_STALE",
        raw_readings={"T50": 1400.0},
        timestamp=old_time
    )
    assert errors == []
    assert frame is not None
    assert frame.frame_quality == DataQuality.STALE
    assert frame.readings["T50"].quality == DataQuality.STALE

    # Timestamp now
    recent_time = datetime.now(timezone.utc)
    frame_fresh, _ = validator.validate_and_normalize_frame(
        machine_id="M_FRESH",
        raw_readings={"T50": 1400.0},
        timestamp=recent_time
    )
    assert frame_fresh.frame_quality == DataQuality.GOOD


# ==========================================
# TEST 9: Data Source Status & Switching
# ==========================================
def test_data_source_status_transitions():
    manager = get_data_source_manager()

    # Default active is C-MAPSS Simulation
    active_info = manager.get_active_source_info()
    assert active_info.source_id == "cmapss_fd001"
    assert active_info.status == DataSourceStatus.CONNECTED

    # REST Connector is NOT_CONFIGURED by default
    rest_info = manager.rest_adapter.get_info()
    assert rest_info.status == DataSourceStatus.NOT_CONFIGURED

    # Configure REST endpoint
    manager.configure_rest_connector(RestConnectorConfig(
        endpoint_url="https://scada.plant.internal/telemetry",
        polling_interval_seconds=2.0,
        is_enabled=True
    ))
    rest_info_after = manager.rest_adapter.get_info()
    assert rest_info_after.status == DataSourceStatus.DISCONNECTED

    # Switch active source
    success, msg = manager.set_active_source("rest_api_connector")
    assert success is True
    assert manager.active_source_id == "rest_api_connector"

    # Reset back to C-MAPSS
    manager.set_active_source("cmapss_fd001")
    assert manager.active_source_id == "cmapss_fd001"


# ==========================================
# TEST 10: ML Compatibility 21/21 vs Incomplete Schemas
# ==========================================
def test_ml_compatibility_21_channels_vs_incomplete():
    compat_service = get_ml_compatibility_service()
    validator = DataValidator()

    # Construct complete 21-channel payload
    all_21_readings = {f"s_{i}": 500.0 for i in range(1, 22)}
    all_21_readings["s_9"] = 9000.0
    all_21_readings["s_14"] = 8100.0

    frame_21, _ = validator.validate_and_normalize_frame(
        machine_id="1",
        raw_readings=all_21_readings
    )
    report_21 = compat_service.evaluate_frame_compatibility(frame_21)
    assert report_21.status == MLCompatibilityStatus.COMPATIBLE
    assert report_21.is_rul_predictable is True
    assert report_21.is_anomaly_detectable is True
    assert report_21.available_compatible_channels == 21
    assert len(report_21.missing_channels) == 0

    # Model row can be converted
    model_row = compat_service.convert_frame_to_model_row(frame_21)
    assert model_row is not None
    assert len(model_row) >= 26

    # Test Incomplete Schema (14/21 channels)
    incomplete_14 = {f"s_{i}": 500.0 for i in [2, 3, 4, 7, 8, 9, 11, 12, 13, 14, 15, 17, 20, 21]}
    frame_14, _ = validator.validate_and_normalize_frame(
        machine_id="2",
        raw_readings=incomplete_14
    )
    report_14 = compat_service.evaluate_frame_compatibility(frame_14)
    assert report_14.status == MLCompatibilityStatus.INCOMPATIBLE
    assert report_14.is_rul_predictable is False
    assert report_14.is_anomaly_detectable is False
    assert report_14.available_compatible_channels == 14
    assert len(report_14.missing_channels) == 7

    # Strictly NO fabricated prediction row
    model_row_14 = compat_service.convert_frame_to_model_row(frame_14)
    assert model_row_14 is None


# ==========================================
# TEST 11: AI Evidence Payload Grounding & Quality
# ==========================================
def test_ai_evidence_includes_source_and_quality():
    cmapss_adapter = CMAPSSDataSourceAdapter()
    compat_service = get_ml_compatibility_service()

    raw_row = {
        "unit_number": 1,
        "time_cycle": 1,
        "setting_1": 0.0,
        "setting_2": 0.0,
        "setting_3": 100.0,
        "s_1": 518.67, "s_2": 641.82, "s_3": 1589.70, "s_4": 1400.60, "s_5": 14.62,
        "s_6": 21.61, "s_7": 554.36, "s_8": 2388.06, "s_9": 9046.19, "s_10": 1.30,
        "s_11": 47.47, "s_12": 521.66, "s_13": 2388.02, "s_14": 8138.62, "s_15": 8.4195,
        "s_16": 0.03, "s_17": 392.0, "s_18": 2388.0, "s_19": 100.0, "s_20": 39.06, "s_21": 23.4190
    }
    frame = cmapss_adapter.convert_cmapss_row_to_frame(raw_row)
    ml_report = compat_service.evaluate_frame_compatibility(frame)

    evidence = build_evidence_from_normalized_frame(
        frame=frame,
        ml_report=ml_report,
        inference_result={
            "rul_estimate": 85.5,
            "anomaly_score": 0.04,
            "anomaly_status": "NORMAL",
            "health_index": 92.0,
            "risk_score": 8.0,
            "risk_level": "NORMAL",
            "contributing_signals": []
        }
    )

    assert "data_source" in evidence
    assert evidence["data_source"]["source_type"] == "CMAPSS_SIMULATION"
    assert evidence["data_source"]["is_simulation"] is True
    assert evidence["data_quality"] == "GOOD"
    assert evidence["ml_compatibility"]["is_rul_predictable"] is True
    assert evidence["rul_prediction_cycles"] == 85.5


# ==========================================
# TEST 12: Data Sources REST API Endpoints & Secret Protection
# ==========================================
@pytest.mark.asyncio
async def test_data_sources_api_endpoints_and_secret_masking():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GET /api/v1/sources
        res = await client.get("/api/v1/sources")
        assert res.status_code == 200
        sources_list = res.json()
        assert len(sources_list) >= 4
        cmapss = next(s for s in sources_list if s["source_id"] == "cmapss_fd001")
        assert cmapss["status"] == "CONNECTED"
        assert cmapss["is_simulation"] is True

        # 2. GET /api/v1/sources/active
        res_active = await client.get("/api/v1/sources/active")
        assert res_active.status_code == 200
        assert res_active.json()["source_id"] == "cmapss_fd001"

        # 3. POST /api/v1/sources/configure (with secrets)
        config_payload = {
            "source_id": "rest_api_connector",
            "rest_config": {
                "endpoint_url": "https://api.plant.corp/v1/stream",
                "auth_type": "api_key",
                "api_key": "super_secret_production_key_12345",
                "is_enabled": True
            }
        }
        res_cfg = await client.post(
            "/api/v1/sources/configure",
            json=config_payload,
            headers={"X-Admin-Role": "admin"}
        )
        assert res_cfg.status_code == 200
        # Check that secret is MASKED on return and not leaked
        assert "super_secret_production_key_12345" not in res_cfg.text
        assert res_cfg.json()["source_info"]["details"]["api_key"] == "••••••••••"

        # 4. Admin Security check: Operator cannot configure
        res_forbidden = await client.post(
            "/api/v1/sources/configure",
            json=config_payload,
            headers={"X-Admin-Role": "operator"}
        )
        assert res_forbidden.status_code == 403

        # 5. POST /api/v1/sources/ingest
        ingest_payload = {
            "machine_id": "TEST_UNIT_99",
            "raw_readings": {
                "fan_temp": 518.67,
                "egt": 1400.0,
                "fan_rpm": 2388.0
            }
        }
        res_ingest = await client.post("/api/v1/sources/ingest", json=ingest_payload)
        assert res_ingest.status_code == 200
        ingest_json = res_ingest.json()
        assert ingest_json["status"] == "SUCCESS"
        assert ingest_json["ml_compatibility"]["is_rul_predictable"] is False

        # 6. GET /api/v1/sources/mappings
        res_map = await client.get("/api/v1/sources/mappings")
        assert res_map.status_code == 200
        assert "canonical_channels" in res_map.json()
        assert "s_4" in res_map.json()["canonical_channels"]


# ==========================================
# TEST 13: CSV Batch Telemetry Ingestion Path
# ==========================================
def test_csv_file_ingestion_and_column_mapping():
    csv_adapter = CsvFileDataSourceAdapter()
    
    csv_data = """unit_number,time_cycle,T2,T24,T30,T50,P2,P15,P30,Nf,Nc,epr,Ps30,phi,NRf,NRc,BPR,farB,htBleed,Nf_dmd,PCNfR_dmd,W31,W32
1,1,518.67,641.82,1589.70,1400.60,14.62,21.61,554.36,2388.06,9046.19,1.30,47.47,521.66,2388.02,8138.62,8.4195,0.03,392,2388,100.0,39.06,23.4190
1,2,518.67,642.15,1591.82,1403.14,14.62,21.61,553.75,2388.04,9044.07,1.30,47.49,522.28,2388.07,8131.49,8.4318,0.03,392,2388,100.0,39.00,23.4236
"""
    result = csv_adapter.process_csv_file(csv_data.encode("utf-8"), filename="test_turbofan_batch.csv")
    assert result.total_rows == 2
    assert result.valid_rows == 2
    assert result.invalid_rows == 0
    assert result.ml_compatibility.status == MLCompatibilityStatus.COMPATIBLE
    assert result.ml_compatibility.is_rul_predictable is True
    assert len(result.sample_normalized_frames) == 2
    assert result.sample_normalized_frames[0].readings["T50"].value == 1400.60
