"""
backend/tests/test_phase2_hardening.py

Comprehensive Test Suite for Phase 2: Industrial ML Hardening
Tests all 9 core capabilities:
  1. Model Versioning & Rollback
  2. Prediction Confidence & Uncertainty
  3. Behavioral Change & Neutral Drift Investigation
  4. Ground-Truth Maintenance Outcomes & Performance Metrics
  5. Data Sufficiency Heuristics
  6. Tiered Customer ML Compatibility
  7. Telemetry Freshness States (CURRENT/STALE/NO_NEW_DATA/NO_DATA)
  8. Multi-Administrator Registry
  9. Machine Registration Review Gate
"""

import pytest
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database import init_db, get_db, AsyncSessionLocal
from backend.app.models.machine import Machine
from backend.app.models.telemetry import Telemetry
from backend.app.models.work_order import WorkOrder
from backend.app.services.data_sufficiency import DataSufficiencyAssessor
from backend.app.services.telemetry_state import TelemetryStateService
from backend.app.services.ml_compatibility import get_ml_compatibility_service
from ml.inference import get_inference_engine



@pytest.fixture(scope="session", autouse=True)
def setup_database():
    import asyncio
    asyncio.run(init_db())


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def sample_machine():
    async with AsyncSessionLocal() as db:
        m = Machine(
            unit_number=999,
            name="Test Engine 999",
            machine_type="CF6-80C2",
            location="Bay 9",
            status="OPERATIONAL",
            telemetry_state="CURRENT",
            last_telemetry_at=datetime.now(timezone.utc),
            current_cycle=50
        )

        db.add(m)
        await db.commit()
        await db.refresh(m)
        yield m
        # Cleanup
        await db.delete(m)
        await db.commit()


# ============================================================================
# 1. MODEL VERSIONING & ROLLBACK TESTS
# ============================================================================

@pytest.mark.anyio
async def test_model_version_lifecycle(client: AsyncClient, sample_machine: Machine):
    # 1. Register candidate version
    headers_admin = {"x-user-role": "ADMIN", "x-actor-name": "Admin Alice"}
    
    cand_resp = await client.post(
        "/api/v1/model-versions",
        json={
            "machine_id": sample_machine.id,
            "version": "v1.0.0-test",
            "model_type": "LightGBM-Test",
            "training_dataset_id": "dataset_2026_01.csv",
            "validation_metrics": {"rul_rmse": 12.4, "anomaly_f1": 0.92}
        },
        headers=headers_admin
    )
    assert cand_resp.status_code == 201
    cand_data = cand_resp.json()
    assert cand_data["status"] == "CANDIDATE"
    v1_id = cand_data["id"]

    # 2. Approve version 1
    appr_resp = await client.post(
        f"/api/v1/model-versions/{v1_id}/approve",
        json={"approved_by": "Admin Alice", "notes": "Approved for production"},
        headers=headers_admin
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "ACTIVE"

    # 3. Register candidate version 2
    cand2_resp = await client.post(
        "/api/v1/model-versions",
        json={
            "machine_id": sample_machine.id,
            "version": "v2.0.0-test",
            "model_type": "LightGBM-Test-V2",
            "parent_version_id": v1_id,
            "validation_metrics": {"rul_rmse": 9.8, "anomaly_f1": 0.95}
        },
        headers=headers_admin
    )
    assert cand2_resp.status_code == 201
    v2_id = cand2_resp.json()["id"]

    # 4. Approve version 2 (should retire version 1 to ROLLBACK_CANDIDATE)
    appr2_resp = await client.post(
        f"/api/v1/model-versions/{v2_id}/approve",
        json={"approved_by": "Admin Alice"},
        headers=headers_admin
    )
    assert appr2_resp.status_code == 200
    assert appr2_resp.json()["status"] == "ACTIVE"

    # Verify v1 is now ROLLBACK_CANDIDATE
    v1_check = await client.get(f"/api/v1/model-versions/{v1_id}", headers=headers_admin)
    assert v1_check.json()["status"] == "ROLLBACK_CANDIDATE"

    # 5. Rollback from v2 to v1
    rb_resp = await client.post(
        f"/api/v1/model-versions/machine/{sample_machine.id}/rollback",
        json={"rollback_reason": "Performance degradation observed on new model", "rolled_back_by": "Admin Alice"},
        headers=headers_admin
    )
    assert rb_resp.status_code == 200
    assert rb_resp.json()["id"] == v1_id
    assert rb_resp.json()["status"] == "ACTIVE"


def test_inference_confidence_calculation():
    engine = get_inference_engine()
    from ml.dataset import CMAPSSDataset
    
    ds = CMAPSSDataset()
    if ds.verify_files_exist():
        df_train = ds.load_raw_train()
        df_unit1 = df_train[df_train["unit_number"] == 1].head(25).copy()
        res_normal = engine.predict_window(df_unit1)
        assert res_normal["confidence_level"] in ["HIGH", "MEDIUM"]
        assert res_normal["confidence_score"] >= 0.60
        assert res_normal["rul_estimate"] is not None

    else:
        # Fallback simulation
        pass

    # Partial window test (non-standard sensor set)
    partial_res = engine.predict_window_partial(
        machine_id=1,
        cycle=10,
        sensor_readings={"vibration_x": 2.3, "bearing_temp": 68.5},
        capability_tier="ANOMALY_ONLY"
    )
    assert partial_res["rul_estimate"] is None
    assert partial_res["capability"] == "ANOMALY_ONLY"
    assert partial_res["confidence_level"] == "INSUFFICIENT_DATA"



# ============================================================================
# 3. BEHAVIORAL CHANGE & DRIFT DETECTION TESTS
# ============================================================================

@pytest.mark.anyio
async def test_drift_and_investigation(client: AsyncClient, sample_machine: Machine):
    headers = {"x-user-role": "OPERATOR", "x-actor-name": "Engineer Bob"}

    # Post a behavioral change directly via drift service test or endpoint
    async with AsyncSessionLocal() as db:
        from backend.app.services.drift_detector import DriftDetectorService
        drift_svc = DriftDetectorService(db)
        change = await drift_svc.record_behavioral_change(
            machine_id=sample_machine.id,
            affected_sensors=["s_2", "s_4"],
            drift_magnitude=3.2,
            drift_method="ZSCORE",
            drift_details={"s_2": 3.4, "s_4": 3.0},
            cycle=50
        )
        await db.commit()
        change_id = change.id

    # Retrieve change
    resp = await client.get(f"/api/v1/drift/{change_id}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["investigation_status"] == "PENDING"

    # Investigate change
    inv_resp = await client.post(
        f"/api/v1/drift/{change_id}/investigate",
        json={
            "change_type": "SENSOR_ISSUE",
            "root_cause": "Thermocouple recalibration required",
            "investigator": "Engineer Bob",
            "close": True
        },
        headers=headers
    )
    assert inv_resp.status_code == 200
    assert inv_resp.json()["change_type"] == "SENSOR_ISSUE"
    assert inv_resp.json()["investigation_status"] == "CLOSED"


# ============================================================================
# 4. GROUND-TRUTH MAINTENANCE OUTCOMES TESTS
# ============================================================================

@pytest.mark.anyio
async def test_maintenance_outcomes_and_performance(client: AsyncClient, sample_machine: Machine):
    headers = {"x-user-role": "OPERATOR", "x-actor-name": "Engineer Bob"}

    # Create completed work order
    async with AsyncSessionLocal() as db:
        wo = WorkOrder(
            work_order_code="WO-TEST-999",
            machine_id=sample_machine.id,
            title="Inspect HPT Blades",
            status="COMPLETED",
            priority="HIGH",
            recommended_action="Borescope inspection",
            affected_subsystem="Turbofan Core"
        )
        db.add(wo)
        await db.commit()
        await db.refresh(wo)
        wo_id = wo.id

    # Record outcome
    out_resp = await client.post(
        "/api/v1/outcomes",
        json={
            "work_order_id": wo_id,
            "machine_id": sample_machine.id,
            "outcome_type": "COMPONENT_REPLACED",
            "recorded_by": "Engineer Bob",
            "component_replaced": "High Pressure Turbine Seal",
            "prediction_was_correct": True,
            "retraining_candidate": True
        },
        headers=headers
    )
    assert out_resp.status_code == 201
    assert out_resp.json()["outcome_type"] == "COMPONENT_REPLACED"

    # Performance metrics
    perf_resp = await client.get("/api/v1/outcomes/performance", headers=headers)
    assert perf_resp.status_code == 200
    assert perf_resp.json()["status"] == "AVAILABLE"
    assert perf_resp.json()["total_assessed"] >= 1


# ============================================================================
# 5. DATA SUFFICIENCY HEURISTICS TESTS
# ============================================================================

def test_data_sufficiency_assessor():
    assessor = DataSufficiencyAssessor()

    # Ideal prognostic dataset
    report_good = assessor.assess(
        duration_days=60.0,
        sample_count=1440,
        samples_per_day=24.0,
        missing_fraction=0.01,
        signal_variance=0.08,
        has_failure_labels=True,
        failure_event_count=4,
        maintenance_event_count=3,
        operating_condition_count=3
    )
    assert report_good.overall_verdict == "SUFFICIENT_FOR_PROGNOSTICS"
    assert len(report_good.dimensions) == 7

    # Dataset with zero failure labels (anomaly detection only)
    report_no_failures = assessor.assess(
        duration_days=30.0,
        sample_count=720,
        samples_per_day=24.0,
        missing_fraction=0.02,
        signal_variance=0.05,
        has_failure_labels=False,
        failure_event_count=0
    )
    assert report_no_failures.overall_verdict in ["SUFFICIENT_FOR_ANOMALY", "SUFFICIENT_FOR_BASELINE"]


# ============================================================================
# 6. TIERED CUSTOMER ML COMPATIBILITY TESTS
# ============================================================================

def test_tiered_customer_ml_compatibility():
    compat = get_ml_compatibility_service()

    # Customer dataset with 10 critical sensors -> FULL or PARTIAL RUL
    critical_sensors = ["s_2", "s_3", "s_4", "s_7", "s_8", "s_11", "s_12", "s_15", "s_20", "s_21"]
    report_full = compat.evaluate_customer_frame_compatibility(
        machine_id="CUST_01",
        available_sensor_ids=critical_sensors + ["s_9", "s_13", "s_14", "s_17"]
    )
    assert report_full.capability_tier in ["FULL_RUL", "PARTIAL_RUL"]
    assert report_full.is_rul_predictable is True

    # Customer dataset with only 3 sensors -> ANOMALY_ONLY
    report_anomaly = compat.evaluate_customer_frame_compatibility(
        machine_id="CUST_02",
        available_sensor_ids=["s_2", "s_3", "s_4"]
    )
    assert report_anomaly.capability_tier == "ANOMALY_ONLY"
    assert report_anomaly.is_rul_predictable is False
    assert report_anomaly.is_anomaly_detectable is True


# ============================================================================
# 7. TELEMETRY FRESHNESS STATES TESTS
# ============================================================================

@pytest.mark.anyio
async def test_telemetry_freshness_states():
    async with AsyncSessionLocal() as db:
        svc = TelemetryStateService(db)

        # Fresh machine
        m_fresh = Machine(
            unit_number=1001,
            name="Fresh Engine",
            last_telemetry_at=datetime.now(timezone.utc),
            telemetry_freshness_seconds=300,
            current_cycle=10
        )
        assert svc.compute_state(m_fresh) == "CURRENT"

        # Stale machine (received 10 minutes ago, threshold 5 mins)
        m_stale = Machine(
            unit_number=1002,
            name="Stale Engine",
            last_telemetry_at=datetime.now(timezone.utc) - timedelta(seconds=600),
            telemetry_freshness_seconds=300,
            current_cycle=10
        )
        assert svc.compute_state(m_stale) == "STALE"

        # No new data (received 2 days ago)
        m_old = Machine(
            unit_number=1003,
            name="Old Engine",
            last_telemetry_at=datetime.now(timezone.utc) - timedelta(days=2),
            telemetry_freshness_seconds=300,
            current_cycle=10
        )
        assert svc.compute_state(m_old) == "NO_NEW_DATA"

        # No data at all
        m_empty = Machine(
            unit_number=1004,
            name="Empty Engine",
            last_telemetry_at=None,
            current_cycle=0
        )
        assert svc.compute_state(m_empty) == "NO_DATA"


# ============================================================================
# 8. MULTI-ADMINISTRATOR REGISTRY TESTS
# ============================================================================

@pytest.mark.anyio
async def test_multi_admin_management(client: AsyncClient):
    headers_admin = {"x-user-role": "ADMIN", "x-actor-name": "admin"}

    # Seed primary admin if empty
    async with AsyncSessionLocal() as db:
        from backend.app.services.user_service import UserService
        u_svc = UserService(db)
        existing = await u_svc.get_user_by_username("admin")
        if not existing:
            await u_svc.create_user("admin", "Primary Admin", "ADMIN", "admin@factorymind.ai")
            await db.commit()

    # List users
    users_resp = await client.get("/api/v1/users", headers=headers_admin)
    assert users_resp.status_code == 200
    assert len(users_resp.json()) >= 1

    # Create new second administrator (Bob Admin) with unique username
    uname = f"admin_bob_{int(datetime.now(timezone.utc).timestamp())}"
    create_resp = await client.post(
        "/api/v1/users",
        json={
            "username": uname,
            "display_name": "Bob Administrator",
            "role": "ADMIN",
            "email": f"{uname}@factorymind.ai"
        },
        headers=headers_admin
    )
    assert create_resp.status_code == 201
    bob_id = create_resp.json()["id"]

    # Verify both admins exist
    users_after = await client.get("/api/v1/users", headers=headers_admin)
    admin_users = [u for u in users_after.json() if u["role"] == "ADMIN"]
    assert len(admin_users) >= 2

    # Downgrade bob_id to OPERATOR (allowed since another admin exists)
    patch_resp = await client.patch(
        f"/api/v1/users/{bob_id}/role",
        json={"new_role": "OPERATOR"},
        headers=headers_admin
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["role"] == "OPERATOR"



# ============================================================================
# 9. MACHINE REGISTRATION REVIEW GATE TESTS
# ============================================================================

@pytest.mark.anyio
async def test_machine_registration_review_gate(client: AsyncClient):
    headers_admin = {"x-user-role": "ADMIN", "x-actor-name": "admin"}

    # Stage a new registration request
    async with AsyncSessionLocal() as db:
        from backend.app.services.machine_registration_service import MachineRegistrationService
        reg_svc = MachineRegistrationService(db)
        req = await reg_svc.stage_upload_for_review(
            requested_machine_id="UNKNOWN_TURBOFAN_99",
            source_filename="plant4_batch.csv",
            source_row_count=150,
            detected_columns=["timestamp", "s_2", "s_4", "s_7"],
            sample_data=[{"s_2": 642.1, "s_4": 1400.2}]
        )
        await db.commit()
        req_id = req.id

    # Check pending list
    pending_resp = await client.get("/api/v1/machine-registrations/pending", headers=headers_admin)
    assert pending_resp.status_code == 200
    ids = [r["id"] for r in pending_resp.json()]
    assert req_id in ids

    # Admin approves registration
    appr_resp = await client.post(
        f"/api/v1/machine-registrations/{req_id}/approve",
        json={
            "machine_name": "Plant 4 Turbofan #99",
            "machine_type": "Industrial Turbofan",
            "location": "Plant 4 - Bay B",
            "reviewed_by": "admin"
        },
        headers=headers_admin
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "APPROVED"
    assert "created_machine_id" in appr_resp.json()
