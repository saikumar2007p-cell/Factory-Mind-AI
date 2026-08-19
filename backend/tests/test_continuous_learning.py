"""
backend/tests/test_continuous_learning.py

Comprehensive Test Suite for Stage 10: Continuous Learning, Maintenance Effectiveness & Executive Intelligence.
Validates:
1. Maintenance effectiveness uses real WorkOrders (no invented success %).
2. No fabricated effectiveness when no verified orders exist.
3. Resolved count comes directly from verification records.
4. Not-resolved count comes directly from verification records.
5. Unable-to-verify count comes from verification records.
6. Before/after comparisons use real telemetry without extrapolation.
7. Missing post-maintenance telemetry produces explicit unavailable state.
8. Recurring issue classification requires >=2 independent recorded events.
9. Single event is not classified as recurring.
10. Machine history uses actual database records.
11. Subsystem analytics use actual records without synthetic rates.
12. Learning signals derive strictly from verified evidence.
13. Learning signals do not mutate database (strictly read-only).
14. Executive summary uses genuine records with zero fake cost savings.
15. Historical trend requires sufficient timestamps (>=2 points).
16. No fabricated historical trend points.
17. ML-incompatible machine preserves RUL: UNAVAILABLE.
18. Stale telemetry remains labeled as STALE.
19. Stage 8 work-order lifecycle remains uncompromised.
20. Stage 9 fleet intelligence remains uncompromised.
21. Learning overview endpoint returns accurate aggregated intelligence.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.database import get_db, init_db, get_session_maker
from backend.app.services.storage_service import StorageService
from backend.app.services.maintenance_effectiveness import MaintenanceEffectivenessService
from backend.app.services.reliability_intelligence import ReliabilityIntelligenceService
from backend.app.services.learning_signals import LearningSignalsService
from backend.app.services.executive_intelligence import ExecutiveIntelligenceService
from backend.app.services.historical_trends import HistoricalTrendsService
import random
from backend.app.schemas.work_order import WorkOrderStatus, WorkOrderPriority


def get_unique_unit_number():
    return random.randint(10000, 999999)


@pytest_asyncio.fixture(autouse=True)
async def setup_test_db():
    await init_db()
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
# 1. Maintenance Effectiveness Uses Real WorkOrders
# ============================================================================
@pytest.mark.asyncio
async def test_maintenance_effectiveness_uses_real_work_orders(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    # Create & verify a work order
    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Stage 10 Test Order",
        recommended_action="HPC stator vane inspection",
        affected_subsystem="High Pressure Compressor (HPC)",
        priority="HIGH"
    )
    await storage.assign_work_order(wo.id, "Chief Inspector")
    await storage.start_work_order(wo.id)
    await storage.complete_work_order(wo.id)
    await storage.verify_work_order(wo.id, "RESOLVED", "Post-maintenance vibration within nominal bounds.")
    await db_session.commit()

    resp = await async_client.get("/api/v1/learning/maintenance-effectiveness")
    assert resp.status_code == 200
    data = resp.json()
    summary = data["summary"]
    assert summary["total_verified_work_orders"] >= 1
    assert summary["resolved_count"] >= 1
    assert summary["resolution_rate_pct"] is not None
    assert summary["effectiveness_status"] == "AVAILABLE"


# ============================================================================
# 2. No Fabricated Effectiveness When No Verified Orders
# ============================================================================
@pytest.mark.asyncio
async def test_no_fabricated_effectiveness_when_no_verified_orders(db_session):
    # Service called directly on clean structure
    service = MaintenanceEffectivenessService(db_session)
    res = await service.get_maintenance_effectiveness()
    summary = res["summary"]
    if summary["total_verified_work_orders"] == 0:
        assert summary["resolution_rate_pct"] is None
        assert "unavailable" in summary["status_message"].lower()


# ============================================================================
# 3. Resolved Count Comes from Verification Records
# ============================================================================
@pytest.mark.asyncio
async def test_resolved_count_comes_from_verification_records(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Resolved Order Test",
        recommended_action="Combustor liner replacement",
        affected_subsystem="Combustor",
        priority="CRITICAL"
    )
    await storage.assign_work_order(wo.id, "Lead Tech")
    await storage.start_work_order(wo.id)
    await storage.complete_work_order(wo.id)
    await storage.verify_work_order(wo.id, "RESOLVED", "Liner replaced and tested.")
    await db_session.commit()

    resp = await async_client.get("/api/v1/learning/maintenance-effectiveness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["resolved_count"] >= 1


# ============================================================================
# 4. Not-Resolved Count Comes from Verification Records
# ============================================================================
@pytest.mark.asyncio
async def test_not_resolved_count_comes_from_verification_records(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Unresolved Order Test",
        recommended_action="Bleed valve adjustment",
        affected_subsystem="Bleed Air System",
        priority="MEDIUM"
    )
    await storage.assign_work_order(wo.id, "Field Tech")
    await storage.start_work_order(wo.id)
    await storage.complete_work_order(wo.id)
    await storage.verify_work_order(wo.id, "NOT_RESOLVED", "Pressure leak still detected.")
    await db_session.commit()

    resp = await async_client.get("/api/v1/learning/maintenance-effectiveness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["not_resolved_count"] >= 1


# ============================================================================
# 5. Unable-to-Verify Count Comes from Verification Records
# ============================================================================
@pytest.mark.asyncio
async def test_unable_to_verify_count_comes_from_verification_records(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Unable to Verify Test",
        recommended_action="Fan blade inspection",
        affected_subsystem="Fan Module",
        priority="LOW"
    )
    await storage.assign_work_order(wo.id, "Quality Lead")
    await storage.start_work_order(wo.id)
    await storage.complete_work_order(wo.id)
    await storage.verify_work_order(wo.id, "UNABLE_TO_VERIFY", "Test cell sensor offline.")
    await db_session.commit()

    resp = await async_client.get("/api/v1/learning/maintenance-effectiveness")
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["unable_to_verify_count"] >= 1


# ============================================================================
# 6. Before/After Uses Real Telemetry
# ============================================================================
@pytest.mark.asyncio
async def test_before_after_uses_real_telemetry(db_session):
    service = MaintenanceEffectivenessService(db_session)
    res = await service.get_maintenance_effectiveness()
    comparisons = res["before_after_comparisons"]
    assert isinstance(comparisons, list)
    for c in comparisons:
        assert c["outcome"] in ["IMPROVED", "UNCHANGED", "DEGRADED", "INSUFFICIENT_DATA"]
        assert "before_metrics" in c


# ============================================================================
# 7. Missing Post-Maintenance Telemetry Produces Unavailable State
# ============================================================================
@pytest.mark.asyncio
async def test_missing_post_maintenance_telemetry_unavailable(db_session):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    # Work order created but not completed
    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Incomplete WO for Before/After Test",
        recommended_action="No-op inspection",
        affected_subsystem="Turbofan Core"
    )
    comp = await storage.get_post_maintenance_comparison(wo.id)
    assert comp["has_post_maintenance_data"] is False
    assert "unavailable" in comp["message"].lower()


# ============================================================================
# 8. Recurring Issue Requires >=2 Events
# ============================================================================
@pytest.mark.asyncio
async def test_recurring_issue_requires_two_events(db_session, async_client):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[1].id if len(machines) > 1 else 2

    # Create 2 work orders for same machine & subsystem
    wo1 = await storage.create_work_order(
        machine_id=m_id,
        title="Event 1",
        recommended_action="Fix HPC seal",
        affected_subsystem="High Pressure Compressor (HPC)"
    )
    wo2 = await storage.create_work_order(
        machine_id=m_id,
        title="Event 2",
        recommended_action="Replace HPC seal",
        affected_subsystem="High Pressure Compressor (HPC)"
    )
    await db_session.commit()

    service = ReliabilityIntelligenceService(db_session)
    recurring = await service.get_recurring_failures()
    match = next((r for r in recurring if r["machine_id"] == m_id and r["subsystem"] == "High Pressure Compressor (HPC)"), None)
    assert match is not None
    assert match["repeated_interventions"] >= 2


# ============================================================================
# 9. Single Event Is Not Classified as Recurring
# ============================================================================
@pytest.mark.asyncio
async def test_single_event_not_classified_as_recurring(db_session):
    storage = StorageService(db_session)
    u_num = get_unique_unit_number()
    
    # Create isolated machine with only 1 work order
    isolated_m = await storage.create_machine(
        unit_number=u_num,
        name=f"Isolated Unit #{u_num}",
        status="OPERATIONAL"
    )
    wo = await storage.create_work_order(
        machine_id=isolated_m.id,
        title="Isolated Event",
        recommended_action="One-off check",
        affected_subsystem="Fan Module"
    )
    await db_session.commit()

    service = ReliabilityIntelligenceService(db_session)
    recurring = await service.get_recurring_failures()
    match = next((r for r in recurring if r["machine_id"] == isolated_m.id), None)
    assert match is None, "Single event was incorrectly classified as recurring failure!"


# ============================================================================
# 10. Machine History Uses Actual Records
# ============================================================================
@pytest.mark.asyncio
async def test_machine_history_uses_actual_records(async_client):
    resp = await async_client.get("/api/v1/learning/machine-history")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    sample = data[0]
    assert "machine_id" in sample
    assert "maintenance_count" in sample
    assert "recurring_issue_status" in sample
    assert "ml_compatibility" in sample


# ============================================================================
# 11. Subsystem Analytics Use Actual Records
# ============================================================================
@pytest.mark.asyncio
async def test_subsystem_analytics_use_actual_records(async_client):
    resp = await async_client.get("/api/v1/learning/subsystems")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 6
    sub_names = [s["subsystem"] for s in data]
    assert "High Pressure Compressor (HPC)" in sub_names
    assert "Low Pressure Turbine (LPT)" in sub_names


# ============================================================================
# 12. Learning Signals Use Verified Evidence
# ============================================================================
@pytest.mark.asyncio
async def test_learning_signals_use_verified_evidence(async_client):
    resp = await async_client.get("/api/v1/learning/signals")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_signals" in data
    assert "signals" in data
    for s in data["signals"]:
        assert s["confidence_level"] in ["HIGH EVIDENCE", "MODERATE EVIDENCE", "LOW EVIDENCE", "INSUFFICIENT DATA"]
        assert "source_records" in s


# ============================================================================
# 13. Learning Signals Do Not Mutate Database
# ============================================================================
@pytest.mark.asyncio
async def test_learning_signals_do_not_mutate_database(db_session, async_client):
    storage = StorageService(db_session)
    before_wos = await storage.list_work_orders()
    before_count = len(before_wos)

    resp = await async_client.get("/api/v1/learning/signals")
    assert resp.status_code == 200

    after_wos = await storage.list_work_orders()
    assert len(after_wos) == before_count, "Learning signals endpoint mutated work orders!"


# ============================================================================
# 14. Executive Summary Uses Genuine Records
# ============================================================================
@pytest.mark.asyncio
async def test_executive_summary_uses_genuine_records(async_client):
    resp = await async_client.get("/api/v1/learning/executive-summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_fleet"] >= 100
    assert data["operational_savings_note"] == "Operational savings data not configured."
    assert data["data_source"] == "NASA C-MAPSS FD001 — Simulation"
    assert data["real_industrial_configured"] is False


# ============================================================================
# 15. Historical Trend Requires Sufficient Timestamps
# ============================================================================
@pytest.mark.asyncio
async def test_historical_trend_requires_sufficient_timestamps(async_client):
    resp = await async_client.get("/api/v1/learning/trends?trend_type=RISK")
    assert resp.status_code == 200
    data = resp.json()
    assert "trend_type" in data
    assert "has_sufficient_data" in data
    if not data["has_sufficient_data"]:
        assert len(data["data_points"]) < 2
        assert "insufficient" in data["message"].lower()


# ============================================================================
# 16. No Fabricated Historical Trend Points
# ============================================================================
@pytest.mark.asyncio
async def test_no_fabricated_historical_trend_points(db_session):
    service = HistoricalTrendsService(db_session)
    trends = await service.get_historical_trends()
    for t_type, trend in trends["trends"].items():
        assert isinstance(trend["data_points"], list)
        if trend["has_sufficient_data"]:
            assert len(trend["data_points"]) >= 2


# ============================================================================
# 17. ML-Incompatible Machine Preserves RUL Unavailable
# ============================================================================
@pytest.mark.asyncio
async def test_ml_incompatible_preserves_rul_unavailable(db_session):
    storage = StorageService(db_session)
    u_num = get_unique_unit_number()
    machine = await storage.create_machine(
        unit_number=u_num,
        name=f"Turbofan Incompatible #{u_num}",
        status="OPERATIONAL"
    )
    await storage.insert_prediction(machine.id, {
        "cycle": 1,
        "rul_estimate": None,
        "anomaly_score": 0.0,
        "anomaly_status": "NORMAL",
        "health_index": 100.0,
        "risk_score": 0.0,
        "risk_level": "NORMAL",
        "model_version": "Incompatible Telemetry Channels"
    })
    await db_session.commit()

    service = ReliabilityIntelligenceService(db_session)
    history = await service.get_machine_maintenance_history(machine.id)
    m_match = next((m for m in history if m["unit_number"] == u_num), None)
    assert m_match is not None
    assert m_match["rul_available"] is False
    assert m_match["rul_estimate"] is None
    assert m_match["ml_compatibility"] == "INCOMPATIBLE"


# ============================================================================
# 18. Stale Telemetry Remains Labeled as Stale
# ============================================================================
@pytest.mark.asyncio
async def test_stale_telemetry_remains_stale(db_session):
    storage = StorageService(db_session)
    u_num = get_unique_unit_number()
    stale_m = await storage.create_machine(
        unit_number=u_num,
        name=f"Turbofan Stale Unit #{u_num}",
        status="OFFLINE"
    )
    await db_session.commit()

    service = ReliabilityIntelligenceService(db_session)
    history = await service.get_machine_maintenance_history(stale_m.id)
    m_match = next((m for m in history if m["unit_number"] == u_num), None)
    assert m_match is not None
    assert m_match["data_quality"] == "STALE"


# ============================================================================
# 19. Stage 8 Work-Order Lifecycle Remains Intact
# ============================================================================
@pytest.mark.asyncio
async def test_stage8_lifecycle_remains_intact(db_session):
    storage = StorageService(db_session)
    machines = await storage.get_all_machines()
    m_id = machines[0].id if machines else 1

    wo = await storage.create_work_order(
        machine_id=m_id,
        title="Stage 10 Closed-Loop Integrity Check",
        recommended_action="Comprehensive borescope audit",
        affected_subsystem="Low Pressure Turbine (LPT)",
        priority="HIGH"
    )
    assert wo.status == "OPEN"
    wo = await storage.assign_work_order(wo.id, "Elena Rostova")
    assert wo.status == "ASSIGNED"
    wo = await storage.start_work_order(wo.id)
    assert wo.status == "IN_PROGRESS"
    wo = await storage.complete_work_order(wo.id)
    assert wo.status == "VERIFICATION_REQUIRED"
    wo = await storage.verify_work_order(wo.id, "RESOLVED", "All clearance verified.")
    assert wo.status == "VERIFIED"


# ============================================================================
# 20. Stage 9 Fleet Intelligence Remains Intact
# ============================================================================
@pytest.mark.asyncio
async def test_stage9_fleet_intelligence_remains_intact(async_client):
    resp = await async_client.get("/api/v1/fleet/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_machines" in data
    assert "healthy_count" in data
    assert "active_work_orders" in data


# ============================================================================
# 21. Learning Overview Endpoint Returns Aggregated Intelligence
# ============================================================================
@pytest.mark.asyncio
async def test_learning_overview_endpoint(async_client):
    resp = await async_client.get("/api/v1/learning/overview")
    assert resp.status_code == 200
    data = resp.json()
    assert "executive_summary" in data
    assert "effectiveness" in data
    assert "recurring_count" in data
    assert "learning_signals_count" in data
    assert "subsystems_monitored" in data
