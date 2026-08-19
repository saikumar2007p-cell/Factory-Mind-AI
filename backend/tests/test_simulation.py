"""
backend/tests/test_simulation.py

Integration tests for C-MAPSS Replay Simulation Engine and WebSocket streaming.
Validates playback controls, step-by-step deterministic progression,
real inference execution, database persistence, and WebSocket frame emission.
"""

import pytest
import pytest_asyncio
from starlette.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.services.simulation import get_simulation_engine


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def sim_engine():
    return get_simulation_engine()


@pytest.mark.asyncio
async def test_simulation_status_endpoint(async_client):
    """Test /api/v1/simulation/status returns current playback state."""
    resp = await async_client.get("/api/v1/simulation/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_running" in data
    assert "unit_number" in data
    assert "current_cycle" in data
    assert data["max_cycle"] == 192  # Unit 1 lasts 192 cycles


@pytest.mark.asyncio
async def test_simulation_reset_and_step(async_client, sim_engine):
    """Test simulation reset and manual cycle advancement."""
    # Reset to cycle 1
    reset_resp = await async_client.post("/api/v1/simulation/reset", json={"unit_number": 1, "start_cycle": 1})
    assert reset_resp.status_code == 200
    assert reset_resp.json()["current_cycle"] == 0

    # Step 1
    step1_resp = await async_client.post("/api/v1/simulation/step")
    assert step1_resp.status_code == 200
    data1 = step1_resp.json()
    assert data1["cycle"] == 1
    assert data1["telemetry"] is not None
    assert data1["prediction"] is not None
    assert data1["prediction"]["rul_estimate"] > 100.0

    # Step 2
    step2_resp = await async_client.post("/api/v1/simulation/step")
    assert step2_resp.status_code == 200
    data2 = step2_resp.json()
    assert data2["cycle"] == 2
    assert data2["telemetry"]["time_cycle"] == 2


@pytest.mark.asyncio
async def test_simulation_start_pause_resume_stop(async_client):
    """Test playback lifecycle endpoints."""
    # Start simulation
    start_resp = await async_client.post(
        "/api/v1/simulation/start",
        json={"unit_number": 1, "start_cycle": 10, "speed_multiplier": 2.0}
    )
    assert start_resp.status_code == 200
    assert start_resp.json()["is_running"] is True
    assert start_resp.json()["current_cycle"] == 9

    # Pause
    pause_resp = await async_client.post("/api/v1/simulation/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["is_paused"] is True

    # Resume
    resume_resp = await async_client.post("/api/v1/simulation/resume")
    assert resume_resp.status_code == 200
    assert resume_resp.json()["is_paused"] is False

    # Stop
    stop_resp = await async_client.post("/api/v1/simulation/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["is_running"] is False


@pytest.mark.asyncio
async def test_simulation_current_cycle_endpoint(async_client):
    """Test short-polling /api/v1/simulation/current-cycle endpoint."""
    resp = await async_client.get("/api/v1/simulation/current-cycle")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_cycle" in data
    assert "unit_number" in data


def test_websocket_stream_connection():
    """Verify WebSocket client connection and initial frame delivery."""
    client = TestClient(app)
    with client.websocket_connect("/api/v1/stream") as websocket:
        initial_msg = websocket.receive_json()
        assert initial_msg["type"] == "INITIAL_STATE"
        assert "unit_number" in initial_msg
        assert "current_cycle" in initial_msg

        # Test ping/pong
        websocket.send_text("ping")
        pong = websocket.receive_text()
        assert pong == "pong"
