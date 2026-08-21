"""
backend/tests/test_email_notifications.py

Unit and integration tests for Gmail & Email notification system.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.services.email_service import EmailService


@pytest.mark.asyncio
async def test_email_service_formatting():
    service = EmailService()
    plain = service.format_email_plain(
        machine_id=1,
        machine_type="Industrial Turbofan Engine",
        severity="CRITICAL",
        reason="Severe thermal drift detected",
        action="Immediate bore-scope inspection",
        rul=24.5,
        health=52.4
    )
    assert "Unit #001" in plain
    assert "CRITICAL" in plain
    assert "24.5 cycles" in plain
    assert "Immediate bore-scope inspection" in plain

    html = service.format_email_html(
        machine_id=1,
        machine_type="Industrial Turbofan Engine",
        severity="CRITICAL",
        reason="Severe thermal drift detected",
        action="Immediate bore-scope inspection",
        rul=24.5,
        health=52.4
    )
    assert "<!DOCTYPE html>" in html
    assert "CRITICAL ALERT" in html
    assert "24.5 cycles" in html


@pytest.mark.asyncio
async def test_email_settings_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get settings
        res = await client.get("/api/v1/notifications/email/settings")
        assert res.status_code == 200
        data = res.json()
        assert "admin_email" in data
        assert "smtp_host" in data

        # Update settings (with operator/admin mock auth)
        headers = {"X-User-Role": "ADMIN", "X-User-Email": "admin@factorymind.ai"}
        up_res = await client.post(
            "/api/v1/notifications/email/settings",
            json={"admin_email": "admin@factorymind.ai", "smtp_host": "smtp.gmail.com"},
            headers=headers
        )
        assert up_res.status_code == 200
        assert up_res.json()["success"] is True


@pytest.mark.asyncio
async def test_send_email_alert_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "ADMIN", "X-User-Email": "admin@factorymind.ai"}
        payload = {
            "machine_id": 1,
            "machine_type": "Turbofan Engine CF6-80C2",
            "severity": "CRITICAL",
            "reason": "High thermal degradation observed across turbine blades",
            "action": "Immediate bore-scope inspection",
            "rul": 24.5,
            "health": 52.4,
            "email_override": "admin@factorymind.ai"
        }
        res = await client.post("/api/v1/notifications/email/send", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["dest_email"] == "admin@factorymind.ai"
        assert "mailto_url" in data


@pytest.mark.asyncio
async def test_test_email_verification():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "ADMIN", "X-User-Email": "admin@factorymind.ai"}
        res = await client.post("/api/v1/notifications/email/test", json={"email": "admin@factorymind.ai"}, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "verified_at" in data


@pytest.mark.asyncio
async def test_email_logs_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/notifications/email/logs?limit=10")
        assert res.status_code == 200
        data = res.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
