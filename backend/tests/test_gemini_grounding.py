"""
backend/tests/test_gemini_grounding.py

Unit and integration tests for Stage 5 — Grounded Gemini AI Diagnostics & Evidence Layer.
Tests evidence construction, grounding rules, JSON response parsing, deterministic fallback,
recommendation persistence, and zero secret leakage.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.database import get_session_maker
from backend.app.services.storage_service import StorageService
from backend.app.services.evidence_builder import build_structured_evidence, validate_evidence_payload
from backend.app.services.gemini_explainer import (
    generate_deterministic_fallback,
    extract_json_from_text,
    generate_gemini_diagnosis,
    GeminiDiagnosticReport
)
from backend.app.models.machine import Machine
from backend.app.models.prediction import Prediction
from backend.app.models.telemetry import Telemetry
from backend.app.models.alert import Alert


@pytest_asyncio.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def mock_evidence():
    return {
        "machine_id": 1,
        "unit_number": 1,
        "machine_name": "Turbofan Engine #001",
        "machine_type": "Turbofan CF6-80C2",
        "location": "Test Cell 2",
        "current_cycle": 180,
        "rul_prediction_cycles": 18.28,
        "anomaly_score": 0.3125,
        "anomaly_status": "NORMAL",
        "health_index_percent": 30.86,
        "risk_score": 69.14,
        "risk_level": "WARNING",
        "model_version": "LightGBM Regressor",
        "contributing_signals": [
            {
                "sensor_id": "s_21",
                "name": "W32",
                "subsystem": "Low Pressure Turbine",
                "units": "lbm/s",
                "current_value": 23.007,
                "baseline_value": 23.393,
                "delta": -0.386,
                "percent_change": -1.65,
                "z_score": -12.88,
                "trend_direction": "decreasing",
                "trend_slope": -0.008,
                "importance_rank": 1
            },
            {
                "sensor_id": "s_4",
                "name": "T50",
                "subsystem": "Low Pressure Turbine",
                "units": "°R",
                "current_value": 1417.14,
                "baseline_value": 1403.206,
                "delta": 13.934,
                "percent_change": 0.99,
                "z_score": 7.21,
                "trend_direction": "increasing",
                "trend_slope": 0.572,
                "importance_rank": 2
            }
        ],
        "sensor_trends": [],
        "sensor_snapshot": {"s_4": 1417.14, "s_21": 23.007},
        "active_alerts": [
            {
                "alert_id": 1,
                "severity": "HIGH",
                "risk_level": "WARNING",
                "reason": "Degradation threshold reached: WARNING"
            }
        ]
    }


def test_evidence_validation_success(mock_evidence):
    """Ensure valid evidence payload passes validation."""
    assert validate_evidence_payload(mock_evidence) is True


def test_evidence_validation_rejects_nans(mock_evidence):
    """Ensure evidence validator rejects NaNs and Infs."""
    corrupted = mock_evidence.copy()
    corrupted["rul_prediction_cycles"] = float("nan")
    with pytest.raises(ValueError, match="contains non-finite value"):
        validate_evidence_payload(corrupted)


def test_evidence_validation_rejects_missing_keys(mock_evidence):
    """Ensure evidence validator rejects missing required metadata."""
    corrupted = mock_evidence.copy()
    del corrupted["risk_level"]
    with pytest.raises(ValueError, match="missing required key"):
        validate_evidence_payload(corrupted)


def test_deterministic_fallback_generation(mock_evidence):
    """Test deterministic fallback produces grounded report matching real evidence."""
    report = generate_deterministic_fallback(mock_evidence, reason="Unit test evaluation")

    assert isinstance(report, GeminiDiagnosticReport)
    assert report.is_fallback is True
    assert report.source == "fallback"
    assert "Unit #001" in report.summary
    assert "18.2" in report.summary or "18.3" in report.summary
    assert "WARNING" in report.summary
    assert len(report.evidence) >= 1
    assert "Low Pressure Turbine" in report.evidence[0] or "W32" in report.evidence[0]
    assert report.confidence in ["High", "Medium", "Low"]
    assert "borescope" in report.recommended_action.lower() or "inspection" in report.recommended_action.lower()


def test_json_extraction_from_markdown():
    """Test parsing JSON from raw LLM responses wrapped in markdown fences."""
    raw_markdown = """```json
{
  "summary": "Engine 1 is experiencing thermal degradation.",
  "risk_explanation": "T50 temperature is elevated.",
  "evidence": ["T50 +13.9R"],
  "recommended_action": "Inspect turbine.",
  "confidence": "High",
  "limitations": "None"
}
```"""
    parsed = extract_json_from_text(raw_markdown)
    assert parsed["summary"] == "Engine 1 is experiencing thermal degradation."
    assert len(parsed["evidence"]) == 1


@pytest.mark.asyncio
async def test_diagnostics_explain_api_endpoint(async_client):
    """Test /api/v1/diagnostics/explain returns grounded report and persists work order."""
    payload = {"machine_id": 1}
    resp = await async_client.post("/api/v1/diagnostics/explain", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["machine_id"] == 1
    assert "summary" in data
    assert "risk_explanation" in data
    assert "evidence" in data
    assert "recommended_action" in data
    assert "confidence" in data
    assert "source" in data
    assert data["source"] in ["gemini", "fallback"]
    assert len(data["evidence"]) >= 1

    # Ensure no API keys or secrets in response
    resp_text = resp.text
    assert "AIza" not in resp_text
    assert "eyJ" not in resp_text


@pytest.mark.asyncio
async def test_diagnostics_get_endpoint(async_client):
    """Test GET /api/v1/diagnostics/1 returns the latest diagnostic state."""
    resp = await async_client.get("/api/v1/diagnostics/1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["machine_id"] == 1
    assert "recommended_action" in data
