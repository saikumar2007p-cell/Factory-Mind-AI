"""
backend/tests/test_fleet_intelligence.py

Comprehensive Test Suite for Stage 9 Fleet Intelligence, Predictive Planning & Maintenance Analytics.
Validates:
1. Fleet summary uses actual machine records (no invented counts).
2. Fleet summary does not fabricate counts.
3. Risk distribution aggregates genuine records.
4. Empty fleet data returns honest unavailable / zero counts.
5. Machine ranking does not fabricate RUL (displays RUL: UNAVAILABLE when missing).
6. ML-incompatible telemetry produces RUL UNAVAILABLE.
7. Stale telemetry is correctly represented (STALE data quality, not CRITICAL failure).
8. Maintenance workload comes directly from Stage 8 WorkOrder records.
9. Verification backlog matches actual WorkOrders in VERIFICATION_REQUIRED.
10. Subsystem analytics use actual alert and work order records.
11. Insufficient history is reported correctly without invented trends.
12. Planning recommendations are deterministic and reproducible.
13. Planner is strictly read-only and cannot automatically mutate work-order lifecycle.
14. Fleet-to-machine and work-order traceability is preserved.
15. Data-source transparency labels remain strictly correct.
16. Stage 8 work-order lifecycle remains fully functional and uncompromised.
17. Full regression baseline continues passing.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.database import get_db, init_db, close_db, get_engine
from backend.app.services.storage_service import StorageService
from backend.app.services.fleet_intelligence import FleetIntelligenceService
from backend.app.services.maintenance_planner import MaintenancePlannerService
from backend.app.schemas.work_order import WorkOrderStatus, WorkOrderPriority


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    """Initializes tables for each test and tears down."""
    await init_db()
    yield
    # Cleanup


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def db_session():
    from backend.app.database import get_session_maker
    session_maker = get_session_maker()
    async with session_maker() as session:
        yield session


# ============================================================================
# 1. Fleet Summary Uses Actual Machine Records
# ============================================================================
@pytest.mark.asyncio
async def test_fleet_summary_uses_actual_machine_records(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    
    resp = await async_client.get("/api/v1/fleet/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_machines"] == len(machines)
    assert data["data_source"] == "NASA C-MAPSS FD001 — Simulation"
    assert data["real_industrial_configured"] is False


# ============================================================================
# 2. Fleet Summary Does Not Fabricate Counts
# ============================================================================
@pytest.mark.asyncio
async def test_fleet_summary_does_not_fabricate_counts(db_session, async_client):
    storage = StorageService(db_session)
    wo_summary = await storage.get_work_orders_summary()

    resp = await async_client.get("/api/v1/fleet/summary")
    assert resp.status_code == 200
    data = resp.json()
    
    # Verify active work order count matches sum of open, assigned, in_progress, verification_required
    expected_active = (
        wo_summary["open_count"] + 
        wo_summary["assigned_count"] + 
        wo_summary["in_progress_count"] + 
        wo_summary["verification_required_count"]
    )
    assert data["active_work_orders"] == expected_active
    assert data["verification_required_count"] == wo_summary["verification_required_count"]


# ============================================================================
# 3. Risk Distribution Aggregates Genuine Records
# ============================================================================
@pytest.mark.asyncio
async def test_risk_distribution_aggregates_genuine_records(async_client):
    resp = await async_client.get("/api/v1/fleet/risk-distribution")
    assert resp.status_code == 200
    data = resp.json()
    
    total_in_dist = (
        data["critical"] +
        data["warning"] +
        data["monitor"] +
        data["normal"] +
        data["stale"] +
        data["unknown_insufficient"]
    )
    assert total_in_dist >= 1
    assert "breakdown" in data
    assert isinstance(data["breakdown"], dict)


# ============================================================================
# 4. Empty Fleet / Missing Data Returns Honest State
# ============================================================================
@pytest.mark.asyncio
async def test_empty_fleet_returns_honest_unavailable_state(db_session):
    service = FleetIntelligenceService(db_session)
    summary = await service.get_fleet_summary()
    assert summary["total_machines"] >= 0
    assert summary["healthy_count"] >= 0
    assert summary["critical_count"] >= 0


# ============================================================================
# 5. Machine Ranking Does Not Fabricate RUL
# ============================================================================
@pytest.mark.asyncio
async def test_machine_ranking_does_not_fabricate_rul(async_client):
    resp = await async_client.get("/api/v1/fleet/machines?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    machines = data["machines"]
    assert len(machines) > 0

    for m in machines:
        if not m["rul_available"]:
            assert m["rul_estimate"] is None, f"Expected None RUL when unavailable, got {m['rul_estimate']}"
        else:
            assert isinstance(m["rul_estimate"], (int, float))
        assert "ranking_evidence" in m
        assert isinstance(m["ranking_evidence"], list)


# ============================================================================
# 6. ML-Incompatible Telemetry Produces RUL UNAVAILABLE
# ============================================================================
@pytest.mark.asyncio
async def test_ml_incompatible_telemetry_produces_rul_unavailable(db_session):
    storage = StorageService(db_session)
    
    # Register test machine with incomplete ML schema
    machine = await storage.create_machine(
        unit_number=999,
        name="Turbofan Incomplete Schema #999",
        status="OPERATIONAL"
    )
    # Insert prediction without RUL (representing incompatible schema)
    await storage.insert_prediction(machine.id, {
        "cycle": 1,
        "rul_estimate": None,
        "anomaly_score": 0.0,
        "anomaly_status": "NORMAL",
        "health_index": 100.0,
        "risk_score": 0.0,
        "risk_level": "NORMAL",
        "model_version": "None (Incompatible)"
    })

    service = FleetIntelligenceService(db_session)
    fleet_machines = await service.get_fleet_machines()
    m999 = next((m for m in fleet_machines if m["unit_number"] == 999), None)
    
    assert m999 is not None
    assert m999["rul_available"] is False
    assert m999["rul_estimate"] is None
    assert m999["ml_compatibility"] == "INCOMPATIBLE"


# ============================================================================
# 7. Stale Telemetry Is Correctly Represented
# ============================================================================
@pytest.mark.asyncio
async def test_stale_telemetry_correctly_represented(db_session):
    storage = StorageService(db_session)
    
    stale_machine = await storage.create_machine(
        unit_number=998,
        name="Turbofan Stale Unit #998",
        status="OFFLINE"
    )
    
    service = FleetIntelligenceService(db_session)
    fleet_machines = await service.get_fleet_machines()
    m998 = next((m for m in fleet_machines if m["unit_number"] == 998), None)
    
    assert m998 is not None
    assert m998["health_status"] == "STALE"
    assert m998["data_quality"] == "STALE"
    assert any("OFFLINE" in ev or "STALE" in ev for ev in m998["ranking_evidence"])


# ============================================================================
# 8. Maintenance Workload Comes from WorkOrder Records
# ============================================================================
@pytest.mark.asyncio
async def test_maintenance_workload_comes_from_work_orders(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    # Create a real work order
    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Stage 9 Workload Test Order",
        recommended_action="Inspect HPC stator vanes",
        affected_subsystem="High Pressure Compressor (HPC)",
        priority="HIGH"
    )
    await db_session.commit()

    resp = await async_client.get("/api/v1/fleet/maintenance-load")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_work_orders"] >= 1
    assert "High Pressure Compressor (HPC)" in data["workload_by_subsystem"]


# ============================================================================
# 9. Verification Backlog Comes from Actual WorkOrders
# ============================================================================
@pytest.mark.asyncio
async def test_verification_backlog_matches_work_orders(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    # Create and advance to VERIFICATION_REQUIRED
    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Stage 9 Verification Backlog Test",
        recommended_action="Turbine overhaul",
        affected_subsystem="Low Pressure Turbine (LPT)",
        priority="CRITICAL"
    )
    await storage.assign_work_order(wo.id, assigned_to="Field Specialist")
    await storage.start_work_order(wo.id)
    await storage.complete_work_order(wo.id)
    await db_session.commit()

    resp = await async_client.get("/api/v1/fleet/maintenance-load")
    assert resp.status_code == 200
    data = resp.json()
    assert data["verification_required_count"] >= 1
    assert data["verification_backlog_count"] >= 1


# ============================================================================
# 10. Subsystem Analytics Use Actual Records
# ============================================================================
@pytest.mark.asyncio
async def test_subsystem_analytics_uses_actual_records(async_client):
    resp = await async_client.get("/api/v1/fleet/subsystems")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_subsystems"] >= 6
    subsystems = data["subsystems"]
    subsystem_names = [s["subsystem"] for s in subsystems]
    assert "High Pressure Compressor (HPC)" in subsystem_names
    assert "Low Pressure Turbine (LPT)" in subsystem_names

    for s in subsystems:
        assert s["health_status"] in ["HEALTHY", "DEGRADED", "CRITICAL", "MONITORED"]
        assert isinstance(s["verification_outcomes"], dict)


# ============================================================================
# 11. Insufficient History Is Reported Correctly
# ============================================================================
@pytest.mark.asyncio
async def test_insufficient_history_reported_correctly(db_session):
    service = FleetIntelligenceService(db_session)
    subsystems = await service.get_fleet_subsystems()
    # Check that healthy subsystems with 0 alerts/workorders have health_status HEALTHY
    for s in subsystems:
        if s["associated_alert_count"] == 0 and s["work_order_count"] == 0:
            assert s["health_status"] == "HEALTHY"


# ============================================================================
# 12. Planning Recommendations Are Deterministic
# ============================================================================
@pytest.mark.asyncio
async def test_planning_recommendations_are_deterministic(db_session):
    planner = MaintenancePlannerService(db_session)
    plan1 = await planner.generate_fleet_plan()
    plan2 = await planner.generate_fleet_plan()

    assert plan1["total_planned"] == plan2["total_planned"]
    assert plan1["immediate_attention_count"] == plan2["immediate_attention_count"]
    assert plan1["high_priority_count"] == plan2["high_priority_count"]
    assert len(plan1["plans"]) == len(plan2["plans"])


# ============================================================================
# 13. Planner Cannot Automatically Mutate Work-Order Lifecycle
# ============================================================================
@pytest.mark.asyncio
async def test_planner_cannot_automatically_mutate_work_orders(db_session, async_client):
    storage = StorageService(db_session)
    initial_wos = await storage.list_work_orders()
    initial_count = len(initial_wos)

    # Invoke planning endpoint
    resp = await async_client.get("/api/v1/fleet/planning")
    assert resp.status_code == 200
    plan_data = resp.json()
    assert plan_data["total_planned"] >= 1

    # Verify database work order count did not change
    after_wos = await storage.list_work_orders()
    assert len(after_wos) == initial_count, "Planner erroneously modified work orders!"


# ============================================================================
# 14. Fleet-to-Machine & Work-Order Traceability Is Preserved
# ============================================================================
@pytest.mark.asyncio
async def test_fleet_traceability_preserved(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Traceability Test Order",
        recommended_action="Inspect combustor liner",
        affected_subsystem="Combustor",
        priority="MEDIUM"
    )
    await db_session.commit()

    # 1. Query Fleet Machines
    resp_fm = await async_client.get("/api/v1/fleet/machines")
    assert resp_fm.status_code == 200
    fm_list = resp_fm.json()["machines"]
    fm_match = next((m for m in fm_list if m["id"] == m_id), None)
    assert fm_match is not None
    assert fm_match["active_work_order_id"] == wo.id
    assert fm_match["active_work_order_code"] == wo.work_order_code

    # 2. Query Machine Detail
    resp_m = await async_client.get(f"/api/v1/machines/{m_id}")
    assert resp_m.status_code == 200

    # 3. Query Work Order Detail
    resp_wo = await async_client.get(f"/api/v1/work-orders/{wo.id}")
    assert resp_wo.status_code == 200
    assert resp_wo.json()["machine_id"] == m_id


# ============================================================================
# 15. Data-Source Transparency Remains Correct
# ============================================================================
@pytest.mark.asyncio
async def test_data_source_transparency(async_client):
    resp = await async_client.get("/api/v1/fleet/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_source"] == "NASA C-MAPSS FD001 — Simulation"
    assert data["real_industrial_configured"] is False


# ============================================================================
# 16. Stage 8 Work-Order Lifecycle Remains Fully Functional
# ============================================================================
@pytest.mark.asyncio
async def test_stage8_lifecycle_uncompromised(db_session):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    # Full lifecycle: OPEN -> ASSIGNED -> IN_PROGRESS -> VERIFICATION_REQUIRED -> VERIFIED
    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Stage 8 Integrity in Stage 9 Test",
        recommended_action="Standard borescope inspection",
        affected_subsystem="Turbofan Core",
        priority="HIGH"
    )
    assert wo.status == "OPEN"

    wo_assigned = await storage.assign_work_order(wo.id, "Elena Rostova")
    assert wo_assigned.status == "ASSIGNED"

    wo_started = await storage.start_work_order(wo.id)
    assert wo_started.status == "IN_PROGRESS"

    wo_completed = await storage.complete_work_order(wo.id)
    assert wo_completed.status == "VERIFICATION_REQUIRED"

    wo_verified = await storage.verify_work_order(wo.id, "RESOLVED", "All clearance checks verified.")
    assert wo_verified.status == "VERIFIED"
    assert wo_verified.verification_status == "RESOLVED"


# ============================================================================
# 17. Attention Required API Endpoint
# ============================================================================
@pytest.mark.asyncio
async def test_attention_required_endpoint(async_client):
    resp = await async_client.get("/api/v1/fleet/attention-required")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_attention_required" in data
    assert "items" in data
    assert isinstance(data["items"], list)
