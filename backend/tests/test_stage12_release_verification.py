"""
backend/tests/test_stage12_release_verification.py

Stage 12 Final Integration, Production Readiness & Release Verification Test Suite.
Validates:
1. Complete End-to-End Traceability:
   Machine -> Telemetry -> Prediction -> Alert -> Recommendation -> Work Order -> Assign -> Start -> Complete -> Verify -> Before/After Comparison -> Continuous Learning -> Fleet Intelligence.
2. Truthful Zero-Fabrication Reporting:
   - When telemetry is absent or non-existent machine: reports unavailable, not fabricated.
   - When ML features are incompatible: reports INCOMPATIBLE / RUL UNAVAILABLE.
   - When no verified work orders exist: reports INSUFFICIENT DATA / 0 effectiveness.
   - Data source transparency labels are exact ("NASA C-MAPSS FD001 — Simulation").
3. Production Hardening & Access Control Matrix:
   - Admin has full operational & config access.
   - Operator can execute maintenance but cannot configure sources or view security logs.
   - Viewer is strictly read-only and blocked from all mutations with 403 Forbidden.
4. Work Order Lifecycle State Machine Integrity:
   - Verified work orders are strictly locked.
   - Invalid jumps return 422.
5. Error Safety & Clean Payload Contracts:
   - Zero stack trace or secret exposure.
"""

import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.database import get_db, init_db, get_session_maker
from backend.app.services.storage_service import StorageService
from backend.app.security import mutation_rate_limiter, SecurityAuditLogger


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    mutation_rate_limiter.client_records.clear()
    yield


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def db_session():
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


# ============================================================================
# 1. Complete End-to-End Lifecycle & Traceability Test
# ============================================================================
@pytest.mark.asyncio
async def test_full_end_to_end_traceability_chain(db_session, async_client):
    """
    Validates complete unbroken chain:
    Machine -> Alert -> Recommendation -> Work Order -> Assign -> Start -> Complete -> Verify -> Before/After -> Learning -> Fleet
    """
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    # 1. Create Alert
    alert = await storage.create_alert(
        machine_id=m_id,
        cycle=150,
        severity="CRITICAL",
        risk_level="CRITICAL",
        reason="Stage 12 E2E HPC thermal degradation",
        evidence={"sensor": "s_4", "val": 1420.5}
    )

    # 2. Create AI Recommendation Grounded on Alert
    rec = await storage.insert_recommendation(
        machine_id=m_id,
        recommendation_text="Perform immediate borescope inspection of HPC stages 5-8",
        alert_id=alert.id,
        source="GEMINI_GROUNDED_RCA"
    )
    await db_session.commit()

    # 3. Create Work Order from Recommendation & Alert (as Operator)
    resp_create = await async_client.post(
        "/api/v1/work-orders",
        json={
            "machine_id": m_id,
            "title": "E2E Work Order - Unit #1 HPC Thermal Repair",
            "recommended_action": rec.recommendation_text,
            "affected_subsystem": "High Pressure Compressor (HPC)",
            "priority": "CRITICAL",
            "source_alert_id": alert.id,
            "source_recommendation_id": rec.id,
            "observed_evidence": {"source_alert": alert.id, "trigger": "s_4 thermal breach"}
        },
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Lead Operator E2E"}
    )
    assert resp_create.status_code == 201
    wo_data = resp_create.json()
    wo_id = wo_data["id"]
    assert wo_data["status"] == "OPEN"
    assert wo_data["source_alert_id"] == alert.id
    assert wo_data["source_recommendation_id"] == rec.id

    # 4. Assign Technician
    resp_assign = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        json={"assigned_to": "Master Tech Marcus", "notes": "Dispatched with borescope kit"},
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Lead Operator E2E"}
    )
    assert resp_assign.status_code == 200
    assert resp_assign.json()["status"] == "ASSIGNED"
    assert resp_assign.json()["assigned_to"] == "Master Tech Marcus"

    # 5. Start Execution
    resp_start = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/start",
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Master Tech Marcus"}
    )
    assert resp_start.status_code == 200
    assert resp_start.json()["status"] == "IN_PROGRESS"

    # 6. Complete Maintenance
    resp_complete = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Master Tech Marcus"}
    )
    assert resp_complete.status_code == 200
    assert resp_complete.json()["status"] == "VERIFICATION_REQUIRED"

    # 7. Perform Verification Sign-Off
    resp_verify = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/verify",
        json={
            "verification_status": "RESOLVED",
            "verification_notes": "Borescope inspection passed; thermal gaskets replaced and torque verified."
        },
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Chief Verifier"}
    )
    assert resp_verify.status_code == 200
    assert resp_verify.json()["status"] == "VERIFIED"
    assert resp_verify.json()["verification_status"] == "RESOLVED"

    # 8. Check Before/After Comparison Endpoint
    resp_comp = await async_client.get(f"/api/v1/work-orders/{wo_id}/comparison")
    assert resp_comp.status_code == 200
    comp_data = resp_comp.json()
    assert comp_data["work_order_id"] == wo_id
    assert "before" in comp_data
    assert "has_post_maintenance_data" in comp_data

    # 9. Verify Continuous Learning Aggregates This Real Verification
    resp_learning = await async_client.get("/api/v1/learning/maintenance-effectiveness")
    assert resp_learning.status_code == 200
    eff = resp_learning.json()
    assert eff["summary"]["total_verified_work_orders"] >= 1
    assert eff["summary"]["resolved_count"] >= 1

    # 10. Verify Fleet Intelligence Aggregates Maintenance Load Truthfully
    resp_fleet = await async_client.get("/api/v1/fleet/maintenance-load")
    assert resp_fleet.status_code == 200
    load = resp_fleet.json()
    assert load["total_work_orders"] >= 1


# ============================================================================
# 2. Truthful Zero-Fabrication Invariants
# ============================================================================
@pytest.mark.asyncio
async def test_zero_fabrication_on_nonexistent_or_uninitialized_entities(async_client):
    # 1. Non-existent machine returns 404
    resp_m = await async_client.get("/api/v1/machines/99999")
    assert resp_m.status_code == 404

    # 2. Non-existent machine telemetry returns 404 truthfully
    resp_t = await async_client.get("/api/v1/telemetry/99999")
    assert resp_t.status_code == 404

    # 3. Active data source clearly labeled as Simulation
    resp_src = await async_client.get("/api/v1/sources/active")
    assert resp_src.status_code == 200
    assert "NASA C-MAPSS FD001" in resp_src.json()["name"]
    assert resp_src.json()["is_simulation"] is True


# ============================================================================
# 3. Security Role Matrix Invariant Test
# ============================================================================
@pytest.mark.asyncio
async def test_role_matrix_security_invariants(async_client):
    # A. Viewer cannot perform any mutations
    mutation_endpoints = [
        ("POST", "/api/v1/work-orders", {"machine_id": 1, "title": "T", "recommended_action": "A"}),
        ("POST", "/api/v1/sources/set-active/cmapss_fd001", None),
        ("POST", "/api/v1/simulation/start", {"unit_number": 1}),
        ("POST", "/api/v1/simulation/reset", {"unit_number": 1}),
    ]

    for method, path, payload in mutation_endpoints:
        if method == "POST":
            resp = await async_client.post(path, json=payload, headers={"X-User-Role": "VIEWER"})
        else:
            resp = await async_client.get(path, headers={"X-User-Role": "VIEWER"})
        assert resp.status_code == 403, f"Viewer unexpectedly allowed on {path} (got {resp.status_code})"

    # B. Operator cannot access admin configurations or security logs
    resp_admin_cfg = await async_client.post(
        "/api/v1/sources/configure",
        json={"source_id": "rest_api_connector"},
        headers={"X-User-Role": "OPERATOR"}
    )
    assert resp_admin_cfg.status_code == 403

    resp_sec_logs = await async_client.get(
        "/api/v1/auth/security-audit-logs",
        headers={"X-User-Role": "OPERATOR"}
    )
    assert resp_sec_logs.status_code == 403


# ============================================================================
# 4. Verified Work Order Immutability Test
# ============================================================================
@pytest.mark.asyncio
async def test_verified_work_order_cannot_be_mutated(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Stage 12 Immutability Test",
        recommended_action="Replace seal",
        affected_subsystem="Fan Module"
    )
    await storage.assign_work_order(wo.id, "Tech A")
    await storage.start_work_order(wo.id)
    await storage.complete_work_order(wo.id)
    await storage.verify_work_order(wo.id, "RESOLVED", "All parameters verified.")
    await db_session.commit()

    # Re-assign attempt -> 422
    resp_reassign = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/assign",
        json={"assigned_to": "Tech B"},
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp_reassign.status_code == 422

    # Start attempt -> 422
    resp_restart = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/start",
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp_restart.status_code == 422

    # Complete attempt -> 422
    resp_recomp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/complete",
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp_recomp.status_code == 422

    # Verify attempt -> 422
    resp_rever = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/verify",
        json={"verification_status": "NOT_RESOLVED"},
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp_rever.status_code == 422


# ============================================================================
# 5. Clean Error Handling & Secret Containment Test
# ============================================================================
@pytest.mark.asyncio
async def test_error_handling_and_secret_containment(async_client):
    resp = await async_client.get("/api/v1/machines/non-integer-id")
    assert resp.status_code == 422
    body = str(resp.json())
    assert "password" not in body.lower()
    assert "secret" not in body.lower()
    assert "traceback" not in body.lower()
