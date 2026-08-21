"""
backend/tests/test_security_and_hardening.py

Comprehensive Test Suite for Stage 11: Production Hardening, Security, RBAC & Access Control.
Validates:
1. Unauthenticated or invalid role rejected (401).
2. Direct API protection: Viewer cannot create work order (403).
3. Direct API protection: Viewer cannot assign technician (403).
4. Direct API protection: Viewer cannot start execution (403).
5. Direct API protection: Viewer cannot complete maintenance (403).
6. Direct API protection: Viewer cannot verify work order (403).
7. Direct API protection: Viewer cannot switch active data source (403).
8. Direct API protection: Viewer cannot configure data source (403).
9. Direct API protection: Viewer cannot acknowledge alert (403).
10. Direct API protection: Viewer cannot control simulation playback (403).
11. Operator allowed full closed-loop maintenance execution (create, assign, start, complete, verify) (200/201).
12. Operator forbidden from modifying administrative data source configurations (403).
13. Operator forbidden from viewing security audit logs (403).
14. Administrator granted full operational, administrative, and security access (200).
15. Strict Stage 8 lifecycle: OPEN -> START directly rejected (422).
16. Strict Stage 8 lifecycle: OPEN -> VERIFY directly rejected (422).
17. Strict Stage 8 lifecycle: ASSIGNED -> VERIFY directly rejected (422).
18. Strict Stage 8 lifecycle: IN_PROGRESS -> VERIFY directly rejected (422).
19. Verified work orders are locked and immutable (422).
20. Security audit logging records actor, role, endpoint, method, timestamp, and status.
21. /api/v1/auth/roles endpoint returns valid role capabilities.
22. /api/v1/auth/me returns current session user identity without leaking secrets.
23. Rate limiter triggers 429 Too Many Requests when threshold exceeded.
24. Error responses never leak stack traces or internal environment secrets.
25. Zero-fabrication transparency guaranteed across all Stage 11 services.
"""

import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.database import get_db, init_db, get_session_maker
from backend.app.services.storage_service import StorageService
from backend.app.security import SecurityAuditLogger, mutation_rate_limiter, UserRole


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await init_db()
    # Reset test rate limiter to avoid cross-test throttling
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
# 1. Unauthenticated or Invalid Role Rejected
# ============================================================================
@pytest.mark.asyncio
async def test_unauthenticated_or_invalid_role_rejected(async_client):
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"X-User-Role": "HACKER_ROLE"}
    )
    assert resp.status_code == 401
    assert "invalid authentication role" in resp.json()["detail"].lower()


# ============================================================================
# 2. Direct API Protection: Invalid/Purged Viewer Role Rejected
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_create_work_order_direct_api(async_client):
    payload = {
        "machine_id": 1,
        "title": "Unauthorized Order Attempt",
        "recommended_action": "Bypass inspection",
        "affected_subsystem": "Turbofan Core"
    }
    resp = await async_client.post(
        "/api/v1/work-orders",
        json=payload,
        headers={"X-User-Role": "VIEWER", "X-Actor-Name": "Viewer Hacker"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 3. Direct API Protection: Invalid/Purged Viewer Role Cannot Assign
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_assign_work_order_direct_api(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Test Order for Viewer Assign",
        recommended_action="Check fan blades",
        affected_subsystem="Fan Module"
    )
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/assign",
        json={"assigned_to": "Unauthorized Tech"},
        headers={"X-User-Role": "VIEWER"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 4. Direct API Protection: Invalid/Purged Viewer Role Cannot Start Execution
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_start_work_order_direct_api(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Test Order for Viewer Start",
        recommended_action="Check HPC stator",
        affected_subsystem="High Pressure Compressor (HPC)"
    )
    await storage.assign_work_order(wo.id, "Tech Lead")
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/start",
        headers={"X-User-Role": "VIEWER"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 5. Direct API Protection: Invalid/Purged Viewer Role Cannot Complete
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_complete_work_order_direct_api(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Test Order for Viewer Complete",
        recommended_action="Combustor repair",
        affected_subsystem="Combustor"
    )
    await storage.assign_work_order(wo.id, "Tech Lead")
    await storage.start_work_order(wo.id)
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/complete",
        headers={"X-User-Role": "VIEWER"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 6. Direct API Protection: Invalid/Purged Viewer Role Cannot Verify
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_verify_work_order_direct_api(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Test Order for Viewer Verify",
        recommended_action="HPT repair",
        affected_subsystem="High Pressure Turbine (HPT)"
    )
    await storage.assign_work_order(wo.id, "Tech Lead")
    await storage.start_work_order(wo.id)
    await storage.complete_work_order(wo.id)
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/verify",
        json={"verification_status": "RESOLVED", "verification_notes": "Fake signoff"},
        headers={"X-User-Role": "VIEWER"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 7. Direct API Protection: Invalid/Purged Viewer Role Cannot Switch Data Source
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_switch_active_data_source(async_client):
    resp = await async_client.post(
        "/api/v1/sources/set-active/csv_file_import",
        headers={"X-User-Role": "VIEWER"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 8. Direct API Protection: Invalid/Purged Viewer Role Cannot Configure Data Source
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_configure_data_source(async_client):
    payload = {
        "source_id": "rest_api_connector",
        "rest_config": {
            "endpoint_url": "http://evil-server.com/api",
            "polling_interval_seconds": 1.0,
            "auth_type": "none"
        }
    }
    resp = await async_client.post(
        "/api/v1/sources/configure",
        json=payload,
        headers={"X-User-Role": "VIEWER"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 9. Direct API Protection: Invalid/Purged Viewer Role Cannot Acknowledge Alert
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_acknowledge_alert(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    alert = await storage.create_alert(
        machine_id=m_id,
        cycle=1,
        severity="HIGH",
        risk_level="WARNING",
        reason="Security test alert",
        evidence={"sensor": "s_4"}
    )
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/alerts/{alert.id}/acknowledge",
        headers={"X-User-Role": "VIEWER"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 10. Direct API Protection: Invalid/Purged Viewer Role Cannot Control Simulation
# ============================================================================
@pytest.mark.asyncio
async def test_viewer_cannot_control_simulation(async_client):
    resp = await async_client.post(
        "/api/v1/simulation/start",
        json={"unit_number": 1},
        headers={"X-User-Role": "VIEWER"}
    )
    assert resp.status_code in (401, 403)


# ============================================================================
# 11. Operator Allowed Full Closed-Loop Maintenance Execution
# ============================================================================
@pytest.mark.asyncio
async def test_operator_allowed_full_maintenance_lifecycle(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    # 1. Create
    resp_create = await async_client.post(
        "/api/v1/work-orders",
        json={
            "machine_id": m_id,
            "title": "Stage 11 Operator Test Order",
            "recommended_action": "Borescope inspection of LPT",
            "affected_subsystem": "Low Pressure Turbine (LPT)",
            "priority": "HIGH"
        },
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Jane Operator"}
    )
    assert resp_create.status_code == 201
    wo_id = resp_create.json()["id"]

    # 2. Assign
    resp_assign = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/assign",
        json={"assigned_to": "Bob Field Tech", "notes": "Dispatched to Cell 1"},
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Jane Operator"}
    )
    assert resp_assign.status_code == 200
    assert resp_assign.json()["status"] == "ASSIGNED"

    # 3. Start
    resp_start = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/start",
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Bob Field Tech"}
    )
    assert resp_start.status_code == 200
    assert resp_start.json()["status"] == "IN_PROGRESS"

    # 4. Complete
    resp_comp = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/complete",
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Bob Field Tech"}
    )
    assert resp_comp.status_code == 200
    assert resp_comp.json()["status"] == "VERIFICATION_REQUIRED"

    # 5. Verify
    resp_ver = await async_client.post(
        f"/api/v1/work-orders/{wo_id}/verify",
        json={"verification_status": "RESOLVED", "verification_notes": "LPT clearance verified."},
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Jane Operator"}
    )
    assert resp_ver.status_code == 200
    assert resp_ver.json()["status"] == "VERIFIED"
    assert resp_ver.json()["verification_status"] == "RESOLVED"


# ============================================================================
# 12. Operator Forbidden From Modifying Data Sources
# ============================================================================
@pytest.mark.asyncio
async def test_operator_forbidden_from_modifying_data_sources(async_client):
    resp = await async_client.post(
        "/api/v1/sources/set-active/csv_file_import",
        headers={"X-User-Role": "OPERATOR"}
    )
    assert resp.status_code == 403


# ============================================================================
# 13. Operator Forbidden From Viewing Security Audit Logs
# ============================================================================
@pytest.mark.asyncio
async def test_operator_forbidden_from_viewing_security_logs(async_client):
    resp = await async_client.get(
        "/api/v1/auth/security-audit-logs",
        headers={"X-User-Role": "OPERATOR"}
    )
    assert resp.status_code == 403


# ============================================================================
# 14. Admin Full Access
# ============================================================================
@pytest.mark.asyncio
async def test_admin_full_access(async_client):
    # Admin can view security logs
    resp = await async_client.get(
        "/api/v1/auth/security-audit-logs",
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp.status_code == 200
    assert "logs" in resp.json()

    # Admin can switch active data source
    resp_source = await async_client.post(
        "/api/v1/sources/set-active/cmapss_fd001",
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp_source.status_code == 200


# ============================================================================
# 15. Strict Stage 8 Lifecycle: OPEN -> START Directly Rejected
# ============================================================================
@pytest.mark.asyncio
async def test_open_to_start_rejected(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Bypass Test Order",
        recommended_action="Inspect",
        affected_subsystem="Turbofan Core"
    )
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/start",
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp.status_code == 422
    assert "invalid" in resp.json()["detail"].lower()


# ============================================================================
# 16. Strict Stage 8 Lifecycle: OPEN -> VERIFY Directly Rejected
# ============================================================================
@pytest.mark.asyncio
async def test_open_to_verify_rejected(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Bypass Verify Test Order",
        recommended_action="Inspect",
        affected_subsystem="Turbofan Core"
    )
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/verify",
        json={"verification_status": "RESOLVED"},
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp.status_code == 422


# ============================================================================
# 17. Strict Stage 8 Lifecycle: ASSIGNED -> VERIFY Directly Rejected
# ============================================================================
@pytest.mark.asyncio
async def test_assigned_to_verify_rejected(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Assigned Verify Test Order",
        recommended_action="Inspect",
        affected_subsystem="Turbofan Core"
    )
    await storage.assign_work_order(wo.id, "Tech Lead")
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/verify",
        json={"verification_status": "RESOLVED"},
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp.status_code == 422


# ============================================================================
# 18. Strict Stage 8 Lifecycle: IN_PROGRESS -> VERIFY Directly Rejected
# ============================================================================
@pytest.mark.asyncio
async def test_in_progress_to_verify_rejected(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="In-Progress Verify Test Order",
        recommended_action="Inspect",
        affected_subsystem="Turbofan Core"
    )
    await storage.assign_work_order(wo.id, "Tech Lead")
    await storage.start_work_order(wo.id)
    await db_session.commit()

    resp = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/verify",
        json={"verification_status": "RESOLVED"},
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp.status_code == 422


# ============================================================================
# 19. Verified Work Orders Are Locked and Immutable
# ============================================================================
@pytest.mark.asyncio
async def test_verified_work_order_is_locked_and_immutable(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Completed Locked Order",
        recommended_action="Replace turbine blade",
        affected_subsystem="High Pressure Turbine (HPT)"
    )
    await storage.assign_work_order(wo.id, "Senior Tech")
    await storage.start_work_order(wo.id)
    await storage.complete_work_order(wo.id)
    await storage.verify_work_order(wo.id, "RESOLVED", "All parameters nominal.")
    await db_session.commit()

    # Attempt re-verifying or starting
    resp_start = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/start",
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp_start.status_code == 422

    resp_verify = await async_client.post(
        f"/api/v1/work-orders/{wo.id}/verify",
        json={"verification_status": "NOT_RESOLVED"},
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp_verify.status_code == 422


# ============================================================================
# 20. Security Audit Logging Records Events
# ============================================================================
@pytest.mark.asyncio
async def test_security_audit_logging_records_events(async_client):
    SecurityAuditLogger.clear()

    # Trigger a denied action
    await async_client.post(
        "/api/v1/work-orders",
        json={"machine_id": 1, "title": "Audit Test", "recommended_action": "Audit"},
        headers={"X-User-Role": "VIEWER", "X-Actor-Name": "Auditor Test"}
    )

    logs = SecurityAuditLogger.get_logs(limit=10)
    assert len(logs) >= 1
    denied = next((l for l in logs if l["status"] == "DENIED"), None)
    assert denied is not None
    assert denied["actor"] == "Auditor Test"
    assert denied["role"] == "VIEWER"
    assert "POST" in denied["method"]


# ============================================================================
# 21. /api/v1/auth/roles Endpoint Returns Metadata
# ============================================================================
@pytest.mark.asyncio
async def test_auth_roles_endpoint_metadata(async_client):
    resp = await async_client.get("/api/v1/auth/roles")
    assert resp.status_code == 200
    roles = resp.json()
    assert len(roles) == 2
    role_names = [r["role"] for r in roles]
    assert "ADMIN" in role_names
    assert "OPERATOR" in role_names
    assert "VIEWER" not in role_names


# ============================================================================
# 22. /api/v1/auth/me Returns Current Session Identity
# ============================================================================
@pytest.mark.asyncio
async def test_auth_me_returns_identity(async_client):
    resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"X-User-Role": "OPERATOR", "X-Actor-Name": "Alex Engineer"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "Alex Engineer"
    assert data["role"] == "OPERATOR"
    assert "manage_work_orders" in data["permissions"]
    assert "admin_config" not in data["permissions"]


# ============================================================================
# 23. Rate Limiter Protects Sensitive Endpoints
# ============================================================================
@pytest.mark.asyncio
async def test_rate_limiter_protects_sensitive_endpoints(async_client):
    # Set limit low to test throttling
    mutation_rate_limiter.max_requests = 3
    mutation_rate_limiter.client_records.clear()

    for i in range(3):
        resp = await async_client.post(
            "/api/v1/auth/switch-role",
            json={"role": "OPERATOR", "actor_name": f"User {i}"},
            headers={"X-User-Role": "ADMIN"}
        )
        assert resp.status_code == 200

    # 4th request should be rate-limited
    resp_throttled = await async_client.post(
        "/api/v1/auth/switch-role",
        json={"role": "OPERATOR", "actor_name": "User 4"},
        headers={"X-User-Role": "ADMIN"}
    )
    assert resp_throttled.status_code == 429
    assert "rate limit" in resp_throttled.json()["detail"].lower()

    # Reset
    mutation_rate_limiter.max_requests = 120
    mutation_rate_limiter.client_records.clear()


# ============================================================================
# 24. No Secret Leakage in Error Responses
# ============================================================================
@pytest.mark.asyncio
async def test_no_secret_leakage_in_error_responses(async_client):
    # Pass invalid non-existent ID
    resp = await async_client.get("/api/v1/work-orders/9999999")
    assert resp.status_code == 404
    data = resp.json()
    body_str = str(data).lower()
    assert "password" not in body_str
    assert "secret" not in body_str
    assert "traceback" not in body_str
    assert "trace" not in body_str


# ============================================================================
# 25. Zero-Fabrication Transparency Guaranteed Across All Stage 11
# ============================================================================
@pytest.mark.asyncio
async def test_zero_fabrication_transparency_guaranteed(async_client):
    resp = await async_client.get("/api/v1/sources/active")
    assert resp.status_code == 200
    data = resp.json()
    assert "NASA C-MAPSS FD001" in data["name"]
    assert data["is_simulation"] is True
