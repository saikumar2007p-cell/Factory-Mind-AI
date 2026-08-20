"""
backend/tests/test_api_endpoints.py

Integration tests for FastAPI REST API endpoints.
Validates machine registry, telemetry retrieval, live inference execution,
alert management, and diagnostic contracts using real database records.
"""

import pytest
# pyrefly: ignore [missing-import]
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database import get_session_maker
from backend.app.services.storage_service import StorageService
from ml.dataset import CMAPSSDataset


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.mark.asyncio
async def test_healthcheck_endpoint(async_client):
    """Test healthcheck endpoint returns 200 and valid metadata."""
    resp = await async_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"
    assert data["ml_inference_ready"] is True
    assert "NASA C-MAPSS" in data["dataset"]


@pytest.mark.asyncio
async def test_list_machines_endpoint(async_client):
    """Test /api/v1/machines returns the registered fleet."""
    resp = await async_client.get("/api/v1/machines")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_machines" in data
    assert "machines" in data
    assert data["total_machines"] >= 1
    assert data["machines"][0]["unit_number"] == 1


@pytest.mark.asyncio
async def test_get_single_machine_endpoint(async_client):
    """Test /api/v1/machines/{id} returns details for a specific machine."""
    # Machine 1 was seeded
    resp = await async_client.get("/api/v1/machines/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == 1
    assert data["unit_number"] == 1
    assert "Turbofan" in data["name"]


@pytest.mark.asyncio
async def test_get_telemetry_endpoint(async_client):
    """Test /api/v1/telemetry/{id} returns real C-MAPSS time-series."""
    resp = await async_client.get("/api/v1/telemetry/1?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["machine_id"] == 1
    assert data["count"] > 0
    assert len(data["telemetry"]) > 0
    assert "s_2" in data["telemetry"][0]
    assert data["telemetry"][0]["s_2"] > 600.0


@pytest.mark.asyncio
async def test_prediction_inference_post_endpoint(async_client):
    """Test /api/v1/predictions/infer accepts observation window and executes real Stage 2 inference."""
    dataset = CMAPSSDataset()
    df_raw = dataset.load_raw_train()
    sample_window = df_raw[df_raw["unit_number"] == 1].head(25).to_dict(orient="records")

    payload = {
        "machine_id": 1,
        "observations": sample_window,
        "apply_hysteresis": True
    }

    resp = await async_client.post("/api/v1/predictions/infer", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["machine_id"] == 1
    assert data["cycle"] == 25
    assert data["rul_estimate"] > 80.0
    assert 0.0 <= data["anomaly_score"] <= 1.0
    assert data["health_index"] >= 60.0
    assert data["risk_level"] == "NORMAL"
    assert len(data["contributing_signals"]) == 5


@pytest.mark.asyncio
async def test_latest_prediction_endpoint(async_client):
    """Test /api/v1/predictions/{id}/latest returns the most recent prediction."""
    resp = await async_client.get("/api/v1/predictions/1/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["machine_id"] == 1
    assert "rul_estimate" in data
    assert "health_index" in data


@pytest.mark.asyncio
async def test_alerts_endpoint(async_client):
    """Test /api/v1/alerts returns active alerts list."""
    resp = await async_client.get("/api/v1/alerts")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "alerts" in data


@pytest.mark.asyncio
async def test_diagnostics_contract_endpoint(async_client):
    """Test /api/v1/diagnostics/{id} returns grounded DiagnosticReportResponse."""
    resp = await async_client.get("/api/v1/diagnostics/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["machine_id"] == 1
    assert "summary" in data
    assert "risk_explanation" in data
    assert "evidence" in data
    assert "recommended_action" in data
    assert "confidence" in data
    assert data["source"] in ["gemini", "fallback"]
