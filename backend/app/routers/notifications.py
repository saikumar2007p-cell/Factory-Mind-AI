"""
backend/app/routers/notifications.py

WhatsApp Alert & Notification API endpoints for FactoryMind AI.
Allows configuring Admin WhatsApp phone number, dispatching instant failure alerts,
and generating verified Click-to-Chat links.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends, status

from backend.app.services.whatsapp_service import WhatsAppService
from backend.app.security import AuthUser, require_role

router = APIRouter(prefix="/notifications", tags=["Notifications & Alerts"])


class WhatsAppSettingsUpdate(BaseModel):
    admin_phone_number: Optional[str] = Field(default=None, description="Admin WhatsApp Phone Number with international prefix")
    admin_name: Optional[str] = Field(default=None, description="Admin Full Name")
    whatsapp_enabled: Optional[bool] = Field(default=None, description="Master toggle for WhatsApp notifications")
    notify_on_critical: Optional[bool] = Field(default=None, description="Send WhatsApp on Critical alerts")
    notify_on_warning: Optional[bool] = Field(default=None, description="Send WhatsApp on Warning alerts")
    webhook_url: Optional[str] = Field(default=None, description="Optional custom Webhook/Twilio endpoint")


class WhatsAppAlertRequest(BaseModel):
    machine_id: int = Field(..., description="Target Machine Unit ID")
    machine_type: Optional[str] = Field(default="Industrial Equipment", description="Type of machine")
    severity: Optional[str] = Field(default="CRITICAL", description="CRITICAL | WARNING | NORMAL")
    reason: Optional[str] = Field(default="Severe temperature & vibration deviation detected", description="Diagnosed root cause")
    action: Optional[str] = Field(default="Inspect machine components and replace worn parts", description="Recommended repair plan")
    rul: Optional[float] = Field(default=None, description="Remaining useful life in cycles")
    health: Optional[float] = Field(default=None, description="Current health index percentage")
    phone_override: Optional[str] = Field(default=None, description="Optional phone number override")


class WhatsAppTestRequest(BaseModel):
    phone_number: Optional[str] = Field(default=None, description="Phone number to send test verification message to")


@router.get("/whatsapp/settings")
async def get_whatsapp_settings():
    """Retrieves current Admin WhatsApp notification configuration."""
    service = WhatsAppService()
    return service.get_settings()


@router.post("/whatsapp/settings")
async def update_whatsapp_settings(
    payload: WhatsAppSettingsUpdate,
    user: AuthUser = Depends(require_role(["admin"]))
):
    """Updates Admin WhatsApp phone number and notification triggers."""
    service = WhatsAppService()
    updates = {k: v for k, v in payload.dict().items() if v is not None}
    updated = service.update_settings(updates)
    return {
        "success": True,
        "message": "Admin WhatsApp settings saved successfully.",
        "settings": updated
    }


@router.post("/whatsapp/send")
async def send_whatsapp_alert(
    payload: WhatsAppAlertRequest,
    user: AuthUser = Depends(require_role(["admin", "operator"]))
):
    """Dispatches/formats an immediate WhatsApp failure alert to the Admin's phone."""
    service = WhatsAppService()
    result = service.send_alert(
        machine_id=payload.machine_id,
        machine_type=payload.machine_type,
        severity=payload.severity,
        reason=payload.reason,
        action=payload.action,
        rul=payload.rul,
        health=payload.health,
        phone_override=payload.phone_override
    )
    return result


@router.post("/whatsapp/test")
async def test_whatsapp_connection(
    payload: Optional[WhatsAppTestRequest] = None,
    user: AuthUser = Depends(require_role(["admin"]))
):
    """Sends a verification test WhatsApp alert to the Admin phone number."""
    service = WhatsAppService()
    target_phone = payload.phone_number if payload else None
    result = service.send_test_message(phone=target_phone)
    return result
