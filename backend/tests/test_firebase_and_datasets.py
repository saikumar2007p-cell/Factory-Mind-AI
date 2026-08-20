"""
backend/tests/test_firebase_and_datasets.py

Tests for Firebase auth endpoints, Firestore service layer, and Multi-Dataset Registry.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from ml.dataset_registry import get_all_datasets, get_dataset, get_available_equipment_types
from ml.dataset_adapters import get_all_adapter_statuses, get_adapter


@pytest.mark.asyncio
async def test_dataset_registry_metadata():
    datasets = get_all_datasets()
    assert len(datasets) >= 3

    cmapss = get_dataset("NASA_CMAPSS_FD001")
    assert cmapss is not None
    assert cmapss.equipmentType.value == "TURBOFAN_ENGINE"
    assert cmapss.sourceType.value == "PUBLIC_DATASET"
    assert cmapss.dataMode.value == "DEMO"
    assert "s_2" in str(cmapss.availableSensors)
    assert cmapss.targetType == "RUL"

    gearbox = get_dataset("PHM_2009_GEARBOX")
    assert gearbox is not None
    assert gearbox.equipmentType.value == "INDUSTRIAL_GEARBOX"
    assert gearbox.targetType == "FAULT_LABEL"

    valve = get_dataset("PHMAP_2023_VALVE")
    assert valve is not None
    assert valve.equipmentType.value == "VALVE_PRESSURE_SYSTEM"
    assert valve.targetType == "ANOMALY_LABEL"


@pytest.mark.asyncio
async def test_dataset_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/v1/datasets/
        res = await client.get("/api/v1/datasets/", headers={"X-User-Role": "ADMIN"})
        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 3
        ids = [d["datasetId"] for d in data]
        assert "NASA_CMAPSS_FD001" in ids
        assert "PHM_2009_GEARBOX" in ids
        assert "PHMAP_2023_VALVE" in ids

        # GET /api/v1/datasets/equipment-types
        res_eq = await client.get("/api/v1/datasets/equipment-types", headers={"X-User-Role": "ADMIN"})
        assert res_eq.status_code == 200
        eq_data = res_eq.json()
        assert any(e["equipmentType"] == "TURBOFAN_ENGINE" for e in eq_data)

        # GET /api/v1/datasets/NASA_CMAPSS_FD001/sensors
        res_sensors = await client.get("/api/v1/datasets/NASA_CMAPSS_FD001/sensors", headers={"X-User-Role": "ADMIN"})
        assert res_sensors.status_code == 200
        sensors = res_sensors.json()
        assert len(sensors) > 0
        assert any(s["id"] == "s_2" for s in sensors)

        # GET /api/v1/datasets/NASA_CMAPSS_FD001/tasks
        res_tasks = await client.get("/api/v1/datasets/NASA_CMAPSS_FD001/tasks", headers={"X-User-Role": "ADMIN"})
        assert res_tasks.status_code == 200
        tasks = res_tasks.json()
        assert "RUL_PREDICTION" in tasks


@pytest.mark.asyncio
async def test_firebase_auth_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/v1/firebase/verify with dev fallback header
        res = await client.get("/api/v1/firebase/verify", headers={"X-User-Role": "ADMIN", "X-Actor-Name": "Test Admin"})
        assert res.status_code == 200
        data = res.json()
        assert data["role"] == "ADMIN"

        # POST /api/v1/firebase/sync-user
        res_sync = await client.post(
            "/api/v1/firebase/sync-user",
            json={"uid": "test_uid_123", "email": "admin@test.com", "name": "Admin Test", "role": "ADMIN"},
            headers={"X-User-Role": "ADMIN"}
        )
        assert res_sync.status_code == 200
        assert res_sync.json()["uid"] == "test_uid_123"
