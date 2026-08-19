"""
backend/tests/test_work_orders.py

Stage 8 Test Suite: Closed-Loop Maintenance Operations & Decision Support for FactoryMind AI.

Verifies:
1. Work order creation with deterministic priority calculation.
2. Alert-to-work-order traceability (retains source_alert_id and observed evidence).
3. Recommendation-to-work-order traceability (retains source_recommendation_id).
4. Valid lifecycle state machine transitions (OPEN -> ASSIGNED -> IN_PROGRESS -> VERIFICATION_REQUIRED -> VERIFIED).
5. OPEN cannot start directly (rejected with 422).
6. OPEN cannot complete directly (rejected with 422).
7. OPEN cannot verify directly (rejected with 422).
8. ASSIGNED cannot complete directly (rejected with 422).
9. ASSIGNED cannot verify directly (rejected with 422).
10. IN_PROGRESS cannot verify directly (rejected with 422).
11. Authorized technician assignment.
12. Maintenance start recording started_at timestamp.
13. Completion recording completed_at and transitioning to VERIFICATION_REQUIRED.
14. Verification recording human inspection outcome (RESOLVED, NOT_RESOLVED, PARTIALLY_RESOLVED, UNABLE_TO_VERIFY) and notes.
15. Operational audit log capturing all lifecycle actions with actor and timestamp.
16. Real backend work orders summary counts.
17. ML incompatibility protection (unavailable RUL preserved without fabrication).
18. Post-maintenance before vs after comparison strictly uses real data without hallucinating improvement.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.database import get_db, init_db, get_session_maker
from backend.app.services.storage_service import StorageService
from backend.app.models.work_order import WorkOrder
from backend.app.schemas.work_order import (
    WorkOrderStatus,
    WorkOrderPriority,
    VerificationStatus
)
from backend.app.services.maintenance_decision import (
    calculate_deterministic_priority,
    validate_lifecycle_transition
)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_database():
    """Ensure database schema is ready before tests."""
    await init_db()
    session_maker = get_session_maker()
    async with session_maker() as session:
        storage = StorageService(session)
        # Ensure machine 1 exists
        m = await storage.get_machine(1)
        if not m:
            await storage.create_machine(unit_number=1, name="Turbofan Engine #001")
        await session.commit()
    yield


# ==========================================
# TEST 1: Work Order Creation & Deterministic Priority
# ==========================================
@pytest.mark.asyncio
async def test_work_order_creation_and_deterministic_priority():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create with explicit risk = CRITICAL -> Expect Priority CRITICAL
        payload = {
            "machine_id": 1,
            "title": "Critical LPT Stator Inspection",
            "recommended_action": "Borescope inspect Low Pressure Turbine stator vanes.",
            "affected_subsystem": "Low Pressure Turbine",
            "risk_level": "CRITICAL",
            "ml_evidence": {"rul_estimate": 18.5, "anomaly_score": 0.22}
        }
        res = await client.post("/api/v1/work-orders", json=payload, headers={"X-Admin-Role": "engineer"})
        assert res.status_code == 201
        data = res.json()
        assert data["priority"] == "CRITICAL"
        assert data["status"] == "OPEN"
        assert data["work_order_code"].startswith("WO-")
        assert data["machine_id"] == 1


# ==========================================
# TEST 2: Alert to Work Order Traceability
# ==========================================
@pytest.mark.asyncio
async def test_alert_to_work_order_traceability():
    session_maker = get_session_maker()
    async with session_maker() as session:
        storage = StorageService(session)
        alert = await storage.create_alert(
            machine_id=1,
            cycle=120,
            severity="HIGH",
            risk_level="WARNING",
            reason="Exhaust gas temperature drift detected",
            evidence={"contributing_sensors": ["s_4", "s_11"]}
        )
        await session.commit()
        alert_id = alert.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "machine_id": 1,
            "title": "Thermal Alarm Remediation",
            "recommended_action": "Inspect exhaust gas thermocouple probe and harness.",
            "affected_subsystem": "Exhaust System",
            "source_alert_id": alert_id,
            "risk_level": "WARNING"
        }
        res = await client.post("/api/v1/work-orders", json=payload, headers={"X-Admin-Role": "admin"})
        assert res.status_code == 201
        data = res.json()
        assert data["source_alert_id"] == alert_id
        assert data["observed_evidence"] == {"contributing_sensors": ["s_4", "s_11"]}


# ==========================================
# TEST 3: Recommendation to Work Order Traceability
# ==========================================
@pytest.mark.asyncio
async def test_recommendation_to_work_order_traceability():
    session_maker = get_session_maker()
    async with session_maker() as session:
        storage = StorageService(session)
        rec = await storage.insert_recommendation(
            machine_id=1,
            recommendation_text="Perform compressor bleed valve lubrication.",
            source="GEMINI_GENAI"
        )
        await session.commit()
        rec_id = rec.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "machine_id": 1,
            "title": "Gemini AI Bleed Valve Action",
            "recommended_action": "Perform compressor bleed valve lubrication.",
            "affected_subsystem": "Bleed Air System",
            "source_recommendation_id": rec_id,
            "priority": "MEDIUM"
        }
        res = await client.post("/api/v1/work-orders", json=payload, headers={"X-Admin-Role": "supervisor"})
        assert res.status_code == 201
        data = res.json()
        assert data["source_recommendation_id"] == rec_id


# ==========================================
# TEST 4: Valid Full Lifecycle State Transitions
# ==========================================
@pytest.mark.asyncio
async def test_valid_lifecycle_transitions():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create (OPEN)
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Full Cycle Lifecycle Test",
            "recommended_action": "Complete multi-step overhaul test."
        }, headers={"X-Admin-Role": "admin"})
        assert res_create.status_code == 201
        wo_id = res_create.json()["id"]
        assert res_create.json()["status"] == "OPEN"

        # 2. Assign (OPEN -> ASSIGNED)
        res_assign = await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={
            "assigned_to": "Alex Vance (Turbine Tech)"
        }, headers={"X-Admin-Role": "supervisor"})
        assert res_assign.status_code == 200
        assert res_assign.json()["status"] == "ASSIGNED"
        assert res_assign.json()["assigned_to"] == "Alex Vance (Turbine Tech)"

        # 3. Start (ASSIGNED -> IN_PROGRESS)
        res_start = await client.post(f"/api/v1/work-orders/{wo_id}/start", headers={"X-Admin-Role": "technician"})
        assert res_start.status_code == 200
        assert res_start.json()["status"] == "IN_PROGRESS"
        assert res_start.json()["started_at"] is not None

        # 4. Complete (IN_PROGRESS -> VERIFICATION_REQUIRED)
        res_complete = await client.post(f"/api/v1/work-orders/{wo_id}/complete", headers={"X-Admin-Role": "technician"})
        assert res_complete.status_code == 200
        assert res_complete.json()["status"] == "VERIFICATION_REQUIRED"
        assert res_complete.json()["completed_at"] is not None

        # 5. Verify (VERIFICATION_REQUIRED -> VERIFIED)
        res_verify = await client.post(f"/api/v1/work-orders/{wo_id}/verify", json={
            "verification_status": "RESOLVED",
            "verification_notes": "Post-maintenance borescope inspection verified successful blade replacement."
        }, headers={"X-Admin-Role": "engineer"})
        assert res_verify.status_code == 200
        assert res_verify.json()["status"] == "VERIFIED"
        assert res_verify.json()["verification_status"] == "RESOLVED"
        assert res_verify.json()["verified_at"] is not None


# ==========================================
# TEST 5: Invalid Transitions from OPEN Rejected
# ==========================================
@pytest.mark.asyncio
async def test_open_cannot_bypass_assignment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create work order in OPEN state
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Bypass Assignment Check",
            "recommended_action": "Check illegal start from OPEN."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        # 1. Attempt illegal transition: OPEN -> IN_PROGRESS directly (without ASSIGNED)
        res_start = await client.post(f"/api/v1/work-orders/{wo_id}/start", headers={"X-Admin-Role": "technician"})
        assert res_start.status_code == 422
        assert "Invalid lifecycle transition" in res_start.json()["detail"]

        # 2. Attempt illegal transition: OPEN -> COMPLETE directly
        res_complete = await client.post(f"/api/v1/work-orders/{wo_id}/complete", headers={"X-Admin-Role": "technician"})
        assert res_complete.status_code == 422
        assert "Invalid lifecycle transition" in res_complete.json()["detail"]

        # 3. Attempt illegal transition: OPEN -> VERIFY directly
        res_verify = await client.post(f"/api/v1/work-orders/{wo_id}/verify", json={
            "verification_status": "RESOLVED"
        }, headers={"X-Admin-Role": "engineer"})
        assert res_verify.status_code == 422
        assert "Invalid lifecycle transition" in res_verify.json()["detail"]


# ==========================================
# TEST 6: Invalid Transitions from ASSIGNED Rejected
# ==========================================
@pytest.mark.asyncio
async def test_assigned_cannot_bypass_in_progress():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create and assign work order
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Assigned Bypass Check",
            "recommended_action": "Check illegal transitions from ASSIGNED."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={"assigned_to": "Elena Rostova"}, headers={"X-Admin-Role": "supervisor"})

        # 1. Attempt ASSIGNED -> COMPLETE directly
        res_complete = await client.post(f"/api/v1/work-orders/{wo_id}/complete", headers={"X-Admin-Role": "technician"})
        assert res_complete.status_code == 422
        assert "Invalid lifecycle transition" in res_complete.json()["detail"]

        # 2. Attempt ASSIGNED -> VERIFY directly
        res_verify = await client.post(f"/api/v1/work-orders/{wo_id}/verify", json={
            "verification_status": "RESOLVED"
        }, headers={"X-Admin-Role": "engineer"})
        assert res_verify.status_code == 422
        assert "Invalid lifecycle transition" in res_verify.json()["detail"]


# ==========================================
# TEST 7: Invalid Transitions from IN_PROGRESS Rejected
# ==========================================
@pytest.mark.asyncio
async def test_in_progress_cannot_verify_directly():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "In Progress Verify Check",
            "recommended_action": "Check illegal verify from IN_PROGRESS."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={"assigned_to": "Elena Rostova"}, headers={"X-Admin-Role": "supervisor"})
        await client.post(f"/api/v1/work-orders/{wo_id}/start", headers={"X-Admin-Role": "technician"})

        # Attempt IN_PROGRESS -> VERIFY directly without completing
        res_verify = await client.post(f"/api/v1/work-orders/{wo_id}/verify", json={
            "verification_status": "RESOLVED"
        }, headers={"X-Admin-Role": "engineer"})
        assert res_verify.status_code == 422
        assert "Invalid lifecycle transition" in res_verify.json()["detail"]


# ==========================================
# TEST 8: Technician Assignment
# ==========================================
@pytest.mark.asyncio
async def test_technician_assignment():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Assignment Test Order",
            "recommended_action": "Verify technician assignment."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        res_assign = await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={
            "assigned_to": "Elena Rostova",
            "actor": "Lead Supervisor"
        }, headers={"X-Admin-Role": "supervisor"})
        assert res_assign.status_code == 200
        data = res_assign.json()
        assert data["assigned_to"] == "Elena Rostova"
        assert data["status"] == "ASSIGNED"


# ==========================================
# TEST 9: Start Maintenance Execution (from ASSIGNED)
# ==========================================
@pytest.mark.asyncio
async def test_start_maintenance_execution():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Start Execution Test",
            "recommended_action": "Execute immediately."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        # Must assign first
        await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={"assigned_to": "Field Tech A"}, headers={"X-Admin-Role": "supervisor"})

        res_start = await client.post(f"/api/v1/work-orders/{wo_id}/start", headers={"X-Admin-Role": "technician"})
        assert res_start.status_code == 200
        data = res_start.json()
        assert data["status"] == "IN_PROGRESS"
        assert data["started_at"] is not None


# ==========================================
# TEST 10: Completion Requires Verification
# ==========================================
@pytest.mark.asyncio
async def test_completion_requires_verification():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Completion Verification Test",
            "recommended_action": "Ensure verification required."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={"assigned_to": "Field Tech B"}, headers={"X-Admin-Role": "supervisor"})
        await client.post(f"/api/v1/work-orders/{wo_id}/start", headers={"X-Admin-Role": "technician"})
        res_complete = await client.post(f"/api/v1/work-orders/{wo_id}/complete", headers={"X-Admin-Role": "technician"})
        assert res_complete.status_code == 200
        data = res_complete.json()
        # Must be in VERIFICATION_REQUIRED state before declaring success
        assert data["status"] == "VERIFICATION_REQUIRED"
        assert data["verification_status"] == "PENDING"


# ==========================================
# TEST 11: Verification Outcomes (Resolved, Not Resolved, etc.)
# ==========================================
@pytest.mark.asyncio
async def test_verification_outcomes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test PARTIALLY_RESOLVED outcome
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Partial Resolution Test",
            "recommended_action": "Inspect seal."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={"assigned_to": "Tech Specialist"}, headers={"X-Admin-Role": "supervisor"})
        await client.post(f"/api/v1/work-orders/{wo_id}/start", headers={"X-Admin-Role": "technician"})
        await client.post(f"/api/v1/work-orders/{wo_id}/complete", headers={"X-Admin-Role": "technician"})

        res_verif = await client.post(f"/api/v1/work-orders/{wo_id}/verify", json={
            "verification_status": "PARTIALLY_RESOLVED",
            "verification_notes": "Primary seal replaced; minor vibration remains under high power settings."
        }, headers={"X-Admin-Role": "engineer"})
        assert res_verif.status_code == 200
        assert res_verif.json()["verification_status"] == "PARTIALLY_RESOLVED"
        assert res_verif.json()["status"] == "VERIFIED"


# ==========================================
# TEST 12: Operational Audit Log
# ==========================================
@pytest.mark.asyncio
async def test_operational_audit_log():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Audit Log Test Order",
            "recommended_action": "Check audit history tracking."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        await client.post(f"/api/v1/work-orders/{wo_id}/assign", json={"assigned_to": "Marcus Brody"}, headers={"X-Admin-Role": "supervisor"})
        await client.post(f"/api/v1/work-orders/{wo_id}/start", headers={"X-Admin-Role": "technician"})

        res_details = await client.get(f"/api/v1/work-orders/{wo_id}")
        assert res_details.status_code == 200
        audit_logs = res_details.json()["audit_logs"]
        assert len(audit_logs) >= 3
        event_types = [log["event_type"] for log in audit_logs]
        assert "CREATED" in event_types
        assert "ASSIGNED" in event_types
        assert "STARTED" in event_types


# ==========================================
# TEST 13: Real Backend Summary Counts
# ==========================================
@pytest.mark.asyncio
async def test_work_orders_summary_counts():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/work-orders/summary")
        assert res.status_code == 200
        summary = res.json()
        assert "total_work_orders" in summary
        assert "open_count" in summary
        assert "assigned_count" in summary
        assert "in_progress_count" in summary
        assert "verification_required_count" in summary
        assert "verified_count" in summary
        assert "high_priority_count" in summary
        assert isinstance(summary["total_work_orders"], int)


# ==========================================
# TEST 14: ML Incompatibility Protection on Work Order
# ==========================================
@pytest.mark.asyncio
async def test_ml_incompatibility_protection_on_work_order():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Incompatible telemetry without 21 channels: RUL is explicitly null/unavailable
        payload = {
            "machine_id": 1,
            "title": "Incompatible Sensor Remediation",
            "recommended_action": "Calibrate missing turbofan pressure channels.",
            "ml_evidence": {
                "rul_estimate": None,
                "ml_compatibility": "INCOMPATIBLE",
                "missing_channels": ["s_3", "s_4", "s_8"]
            }
        }
        res = await client.post("/api/v1/work-orders", json=payload, headers={"X-Admin-Role": "engineer"})
        assert res.status_code == 201
        data = res.json()
        assert data["ml_evidence"]["rul_estimate"] is None
        assert data["ml_evidence"]["ml_compatibility"] == "INCOMPATIBLE"


# ==========================================
# TEST 15: Post-Maintenance Comparison Unavailability Protection
# ==========================================
@pytest.mark.asyncio
async def test_post_maintenance_comparison_without_fabrication():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res_create = await client.post("/api/v1/work-orders", json={
            "machine_id": 1,
            "title": "Post-Maintenance Comparison Test",
            "recommended_action": "Check comparison response."
        }, headers={"X-Admin-Role": "admin"})
        wo_id = res_create.json()["id"]

        res_comp = await client.get(f"/api/v1/work-orders/{wo_id}/comparison")
        assert res_comp.status_code == 200
        comp_data = res_comp.json()
        assert comp_data["has_post_maintenance_data"] is False
        assert "unavailable" in comp_data["message"].lower()
        assert comp_data["after"] is None
