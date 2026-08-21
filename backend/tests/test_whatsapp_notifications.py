"""
backend/tests/test_whatsapp_notifications.py

Tests for WhatsApp Alert Notifications, Click-to-Chat deep links,
admin phone persistence, and trigger validations.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.services.whatsapp_service import WhatsAppService


@pytest.mark.asyncio
async def test_whatsapp_service_formatting_and_click_url():
    service = WhatsAppService()
    phone = "+1 (555) 987-6543"
    clean = service.clean_phone_number(phone)
    assert clean == "15559876543"

    msg = service.format_alert_message(
        machine_id=1,
        machine_type="Industrial Turbofan Engine",
        severity="CRITICAL",
        reason="Severe LPT blade degradation",
        action="Perform immediate borescope inspection",
        rul=28.5,
        health=58.2
    )

    assert "FactoryMind AI" in msg
    assert "URGENT CRITICAL ALERT" in msg
    assert "Unit #001" in msg
    assert "28.5 cycles" in msg
    assert "58.2%" in msg

    click_url = service.generate_click_url(phone, msg)
    assert click_url.startswith("https://wa.me/15559876543?text=")


@pytest.mark.asyncio
async def test_whatsapp_settings_api_and_update():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get settings
        res = await client.get("/api/v1/notifications/whatsapp/settings")
        assert res.status_code == 200
        data = res.json()
        assert "admin_phone_number" in data

        # Update settings as Admin
        headers = {"X-User-Role": "ADMIN", "X-Actor-Name": "Admin User"}
        update_payload = {
            "admin_phone_number": "+919876543210",
            "admin_name": "Chief Plant Officer",
            "notify_on_critical": True,
            "notify_on_warning": True
        }
        update_res = await client.post(
            "/api/v1/notifications/whatsapp/settings",
            json=update_payload,
            headers=headers
        )
        assert update_res.status_code == 200
        assert update_res.json()["success"] is True
        assert update_res.json()["settings"]["admin_phone_number"] == "+919876543210"


@pytest.mark.asyncio
async def test_send_whatsapp_alert_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "OPERATOR", "X-Actor-Name": "Bob Engineer"}
        alert_payload = {
            "machine_id": 5,
            "machine_type": "Industrial Gearbox",
            "severity": "CRITICAL",
            "reason": "Shaft vibration harmonic spike detected",
            "action": "Grease bearings and check gear teeth clearance",
            "rul": 19.4,
            "health": 48.0
        }
        res = await client.post(
            "/api/v1/notifications/whatsapp/send",
            json=alert_payload,
            headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "click_url" in data
        assert "wa.me" in data["click_url"]
        assert data["severity"] == "CRITICAL"
        assert data["machine_id"] == 5


@pytest.mark.asyncio
async def test_test_whatsapp_verification():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"X-User-Role": "ADMIN", "X-Actor-Name": "Alice Admin"}
        res = await client.post(
            "/api/v1/notifications/whatsapp/test",
            json={"phone_number": "+15550001122"},
            headers=headers
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "wa.me/15550001122" in data["click_url"]


@pytest.mark.asyncio
async def test_whatsapp_logs_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/notifications/whatsapp/logs")
        assert res.status_code == 200
        data = res.json()
        assert "logs" in data
        assert isinstance(data["logs"], list)
