"""
backend/app/routers/auth.py

Authentication, Session Identity, Role Management & Security Audit Logs Router.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from pydantic import BaseModel, Field

from backend.app.security import (
    AuthUser,
    UserRole,
    SecurityAuditLogger,
    mutation_rate_limiter,
    get_current_user,
    require_role
)

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])


class RoleSwitchRequest(BaseModel):
    role: str = Field(description="Desired role: ADMIN, OPERATOR, VIEWER")
    actor_name: Optional[str] = Field(default=None, max_length=100)


class RoleInfo(BaseModel):
    role: str
    display_name: str
    description: str
    permissions: List[str]


@router.get("/me", response_model=AuthUser)
async def get_me(user: AuthUser = Depends(get_current_user)):
    """Returns the current authenticated session identity, role, and granted permissions."""
    return user


@router.get("/roles", response_model=List[RoleInfo])
async def list_roles():
    """Returns all supported system roles, permission sets, and capabilities."""
    return [
        RoleInfo(
            role=UserRole.ADMIN.value,
            display_name="System Administrator",
            description="Full authorized access across all operations, data source configurations, work orders, and security audit logs.",
            permissions=["read", "write", "manage_work_orders", "verify", "admin_config", "view_security_logs"]
        ),
        RoleInfo(
            role=UserRole.OPERATOR.value,
            display_name="Operations Engineer",
            description="Full operational authority to create, assign, execute, and verify closed-loop maintenance work orders and acknowledge alerts.",
            permissions=["read", "write", "manage_work_orders", "verify"]
        ),
        RoleInfo(
            role=UserRole.VIEWER.value,
            display_name="Read-Only Viewer",
            description="Strictly read-only visibility into fleet telemetry, diagnostics, predictions, alarms, maintenance histories, and learning analytics.",
            permissions=["read"]
        )
    ]


@router.post("/switch-role", response_model=AuthUser)
async def switch_role(
    payload: RoleSwitchRequest,
    request: Request,
    user: AuthUser = Depends(get_current_user)
):
    """
    Validates and switches the active session role.
    Records a structured security audit event.
    """
    client_ip = request.client.host if request.client else "unknown"
    if not mutation_rate_limiter.is_allowed(client_ip):
        SecurityAuditLogger.record(
            actor=payload.actor_name or user.username,
            role=user.role.value,
            action="RATE_LIMIT_EXCEEDED",
            endpoint="/api/v1/auth/switch-role",
            method="POST",
            status="DENIED",
            reason="Abuse protection rate limit exceeded",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit reached. Please wait a moment before sending more requests."
        )
    raw_role = payload.role.strip().upper()
    if raw_role not in [r.value for r in UserRole]:
        SecurityAuditLogger.record(
            actor=payload.actor_name or user.username,
            role=user.role.value,
            action=f"SWITCH_ROLE_FAILED({raw_role})",
            endpoint="/api/v1/auth/switch-role",
            method="POST",
            status="DENIED",
            reason=f"Invalid target role: {raw_role}",
            client_ip=request.client.host if request.client else "unknown"
        )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{payload.role}'. Supported roles: ADMIN, OPERATOR, VIEWER."
        )

    target_role = UserRole(raw_role)
    actor_name = payload.actor_name.strip() if payload.actor_name and payload.actor_name.strip() else f"User ({target_role.value})"

    if target_role == UserRole.ADMIN:
        permissions = ["read", "write", "manage_work_orders", "verify", "admin_config", "view_security_logs"]
    elif target_role == UserRole.OPERATOR or target_role == UserRole.ENGINEER:
        permissions = ["read", "write", "manage_work_orders", "verify"]
    else:
        permissions = ["read"]

    SecurityAuditLogger.record(
        actor=actor_name,
        role=target_role.value,
        action=f"SWITCH_ROLE({user.role.value} -> {target_role.value})",
        endpoint="/api/v1/auth/switch-role",
        method="POST",
        status="GRANTED",
        client_ip=request.client.host if request.client else "unknown"
    )

    return AuthUser(
        user_id=f"USR-{target_role.value}",
        username=actor_name,
        role=target_role,
        permissions=permissions
    )


@router.get("/security-audit-logs")
async def get_security_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    user: AuthUser = Depends(require_role(["admin"]))
):
    """
    Returns the immutable security event audit trail.
    Strictly protected: Administrator authorization required.
    """
    return {
        "total_records": len(SecurityAuditLogger._events),
        "logs": SecurityAuditLogger.get_logs(limit=limit)
    }


@router.post("/clear-session")
async def clear_session(
    request: Request,
    user: AuthUser = Depends(get_current_user)
):
    """Clears session and records logout event."""
    SecurityAuditLogger.record(
        actor=user.username,
        role=user.role.value,
        action="SESSION_LOGOUT",
        endpoint="/api/v1/auth/clear-session",
        method="POST",
        status="GRANTED",
        client_ip=request.client.host if request.client else "unknown"
    )
    return {
        "status": "LOGGED_OUT",
        "message": "Session cleared successfully. Role reset to default."
    }
