"""
backend/tests/test_database.py

Comprehensive test suite for Stage 3 Database & Storage Layer.
Tests connection, schema initialization, CRUD operations, foreign key integrity,
and seamless persistence of real Stage 2 inference outputs.
"""

import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
import os
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.app.database import Base, init_db
from backend.app.models.machine import Machine
from backend.app.models.telemetry import Telemetry
from backend.app.models.prediction import Prediction
from backend.app.models.anomaly import Anomaly
from backend.app.models.alert import Alert
from backend.app.models.recommendation import Recommendation
from backend.app.services.storage_service import StorageService
from ml.dataset import CMAPSSDataset
from ml.inference import get_inference_engine

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_session():
    """Provides an isolated in-memory SQLite database session for tests."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.mark.asyncio
async def test_machine_crud(test_session):
    """Test machine creation, retrieval by ID, unit, and listing."""
    service = StorageService(test_session)

    m1 = await service.create_machine(unit_number=101, name="Test Turbofan 101")
    assert m1.id is not None
    assert m1.unit_number == 101
    assert m1.status == "OPERATIONAL"

    # Retrieve by ID
    retrieved = await service.get_machine_by_id(m1.id)
    assert retrieved is not None
    assert retrieved.name == "Test Turbofan 101"

    # Retrieve by Unit
    by_unit = await service.get_machine_by_unit(101)
    assert by_unit is not None
    assert by_unit.id == m1.id

    # Update cycle and status
    updated = await service.update_machine_status_and_cycle(m1.id, current_cycle=45, status="MONITORING")
    assert updated.current_cycle == 45
    assert updated.status == "MONITORING"


@pytest.mark.asyncio
async def test_real_telemetry_insertion_and_querying(test_session):
    """Test inserting and querying authentic C-MAPSS telemetry."""
    service = StorageService(test_session)
    dataset = CMAPSSDataset()
    df_raw = dataset.load_raw_train()
    unit_1_records = df_raw[df_raw["unit_number"] == 1].head(15).to_dict(orient="records")

    m = await service.create_machine(unit_number=1, name="Engine #1")
    
    # Batch insertion
    count = await service.insert_telemetry_batch(m.id, unit_1_records)
    assert count == 15

    # Query history
    history = await service.get_telemetry_history(m.id, start_cycle=5, end_cycle=10)
    assert len(history) == 6
    assert history[0].cycle == 5
    assert history[-1].cycle == 10
    assert history[0].s_2 > 600.0  # Real T24 temperature


@pytest.mark.asyncio
async def test_real_stage2_prediction_persistence(test_session):
    """Test persisting real inference result produced by Stage 2 InferenceEngine."""
    service = StorageService(test_session)
    dataset = CMAPSSDataset()
    df_raw = dataset.load_raw_train()
    window = df_raw[df_raw["unit_number"] == 1].iloc[:30].copy()

    m = await service.create_machine(unit_number=1, name="Engine #1")
    
    # Run real Stage 2 inference
    engine = get_inference_engine()
    inference_result = engine.predict_window(window)

    # Persist prediction
    pred = await service.insert_prediction(m.id, inference_result)
    assert pred.id is not None
    assert pred.machine_id == m.id
    assert pred.cycle == 30
    assert pred.rul_estimate == inference_result["rul_estimate"]
    assert pred.health_index == inference_result["health_index"]
    assert pred.risk_level == "NORMAL"
    assert len(pred.contributing_signals) == 5


@pytest.mark.asyncio
async def test_anomaly_and_alert_lifecycle(test_session):
    """Test logging anomalies, alerts, and acknowledging alerts."""
    service = StorageService(test_session)
    m = await service.create_machine(unit_number=2, name="Engine #2")

    # Record anomaly
    anomaly = await service.insert_anomaly(
        machine_id=m.id,
        cycle=120,
        anomaly_score=0.85,
        anomaly_status="ANOMALOUS",
        raw_decision=-0.08,
        evidence={"sensor": "s_11", "z_score": 4.5}
    )
    assert anomaly.id is not None
    assert anomaly.anomaly_status == "ANOMALOUS"

    # Create active alert
    alert = await service.create_alert(
        machine_id=m.id,
        cycle=120,
        severity="HIGH",
        risk_level="WARNING",
        reason="Elevated HPC outlet pressure deviation",
        evidence={"anomaly_id": anomaly.id}
    )
    assert alert.status == "ACTIVE"

    # Query active alerts
    active_alerts = await service.get_active_alerts(m.id)
    assert len(active_alerts) == 1
    assert active_alerts[0].id == alert.id

    # Acknowledge alert
    ack_alert = await service.acknowledge_alert(alert.id)
    assert ack_alert.status == "ACKNOWLEDGED"
    assert ack_alert.acknowledged_at is not None

    # Should no longer be active
    active_after = await service.get_active_alerts(m.id)
    assert len(active_after) == 0


@pytest.mark.asyncio
async def test_recommendation_persistence(test_session):
    """Test storing maintenance recommendations linked to machine and alerts."""
    service = StorageService(test_session)
    m = await service.create_machine(unit_number=3, name="Engine #3")

    rec = await service.insert_recommendation(
        machine_id=m.id,
        recommendation_text="Perform borescope inspection on HPC 4th stage stator blades.",
        source="DETERMINISTIC_RULES",
        is_fallback=False
    )
    assert rec.id is not None
    assert rec.machine_id == m.id

    recs = await service.get_recommendations(m.id)
    assert len(recs) == 1
    assert "borescope" in recs[0].recommendation_text


@pytest.mark.asyncio
async def test_persist_inference_cycle_full_pipeline(test_session):
    """Test end-to-end integration: Real C-MAPSS window -> Stage 2 -> Database."""
    service = StorageService(test_session)
    dataset = CMAPSSDataset()
    df_raw = dataset.load_raw_train()
    
    # Degraded window for Unit 1 (Cycle 185, near failure)
    degraded_window = df_raw[df_raw["unit_number"] == 1].iloc[:185].copy()
    m = await service.create_machine(unit_number=1, name="Engine #1")

    engine = get_inference_engine()
    engine.reset_tracker(1)

    # Prime tracker to trigger state change
    for c in [175, 180, 185]:
        w = df_raw[df_raw["unit_number"] == 1].iloc[:c].copy()
        res = engine.predict_window(w)
        pred, anomaly, alert = await service.persist_inference_cycle(m.id, res)

    assert pred.cycle == 185
    assert pred.rul_estimate < 25.0
    
    # Machine status should be updated
    m_updated = await service.get_machine_by_id(m.id)
    assert m_updated.current_cycle == 185
    assert m_updated.status in ["DEGRADED", "CRITICAL"]
