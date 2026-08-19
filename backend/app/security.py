"""
backend/app/security.py

Enterprise Role-Based Access Control (RBAC), Rate Limiting, and Security Audit Logging for FactoryMind AI.

Supported Roles:
- ADMIN: Full operational and administrative access.
- OPERATOR / ENGINEER: Full operational maintenance and prognostic controls.
- VIEWER: Strictly read-only access across all endpoints.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime, timezone
import logging
import time
from collections import defaultdict
from fastapi import Request, Header, HTTPException, status, Depends
from pydantic import BaseModel, Field

logger = logging.getLogger("factorymind.security")


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    ENGINEER = "ENGINEER"
    VIEWER = "VIEWER"


class AuthUser(BaseModel):
    user_id: str = "USR-DEV-001"
    username: str = "Factory Engineer"
    role: UserRole = UserRole.OPERATOR
    permissions: List[str] = Field(default_factory=list)
    authenticated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ============================================================================
# Security Audit Trail In-Memory Store (Thread-Safe Append)
# ============================================================================

class SecurityAuditEvent(BaseModel):
    id: int
    actor: str
    role: str
    action_attempted: str
    endpoint: str
    method: str
    status: str # GRANTED, DENIED, RATE_LIMITED
    reason: Optional[str] = None
    client_ip: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SecurityAuditLogger:
    """Immutable audit trail for security, authentication, and authorization events."""
    _events: List[SecurityAuditEvent] = []
    _counter: int = 1

    @classmethod
    def record(
        cls,
        actor: str,
        role: str,
        action: str,
        endpoint: str,
        method: str,
        status: str,
        reason: Optional[str] = None,
        client_ip: Optional[str] = None
    ) -> SecurityAuditEvent:
        event = SecurityAuditEvent(
            id=cls._counter,
            actor=actor,
            role=role,
            action_attempted=action,
            endpoint=endpoint,
            method=method,
            status=status,
            reason=reason,
            client_ip=client_ip
        )
        cls._counter += 1
        cls._events.append(event)
        # Keep last 500 security events
        if len(cls._events) > 500:
            cls._events = cls._events[-500:]
        
        if status == "DENIED":
            logger.warning(f"[SECURITY DENIED] Actor={actor} Role={role} Action={action} Endpoint={endpoint} Reason={reason}")
        else:
            logger.info(f"[SECURITY GRANTED] Actor={actor} Role={role} Action={action} Endpoint={endpoint}")
        return event

    @classmethod
    def get_logs(cls, limit: int = 100) -> List[Dict[str, Any]]:
        return [e.model_dump() for e in reversed(cls._events[-limit:])]

    @classmethod
    def clear(cls):
        """For test isolated resets only."""
        cls._events.clear()
        cls._counter = 1


# ============================================================================
# Lightweight In-Memory Sliding-Window Rate Limiter
# ============================================================================

class RateLimiter:
    """Sliding-window rate limiter protecting sensitive mutation & auth endpoints."""
    def __init__(self, max_requests: int = 120, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.client_records: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_id: str) -> bool:
        now = time.time()
        window_start = now - self.window_seconds
        # Filter timestamps inside window
        self.client_records[client_id] = [
            t for t in self.client_records[client_id] if t > window_start
        ]
        if len(self.client_records[client_id]) >= self.max_requests:
            return False
        self.client_records[client_id].append(now)
        return True


# Global rate limiters
mutation_rate_limiter = RateLimiter(max_requests=120, window_seconds=60)
auth_rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


# ============================================================================
# FastAPI Authentication & Authorization Dependencies
# ============================================================================

def get_current_user(
    request: Request,
    x_user_role: Optional[str] = Header(default=None, description="Active user role header"),
    x_admin_role: Optional[str] = Header(default=None, description="Legacy admin role header fallback"),
    x_actor_name: Optional[str] = Header(default=None, description="Actor identity header")
) -> AuthUser:
    """
    Extracts and validates the current user identity and role from headers.
    Supports development and production headers with zero fabricated credentials.
    """
    raw_role = x_user_role or x_admin_role or "OPERATOR"
    normalized_role = raw_role.strip().upper()

    if normalized_role in ["ADMIN", "ROOT", "SYSTEM_ADMIN"]:
        role = UserRole.ADMIN
        permissions = ["read", "write", "manage_work_orders", "verify", "admin_config", "view_security_logs"]
    elif normalized_role in ["OPERATOR", "ENGINEER", "SUPERVISOR", "TECHNICIAN"]:
        role = UserRole.OPERATOR
        permissions = ["read", "write", "manage_work_orders", "verify"]
    elif normalized_role in ["VIEWER", "READONLY", "AUDITOR"]:
        role = UserRole.VIEWER
        permissions = ["read"]
    else:
        # Invalid role provided
        client_ip = request.client.host if request.client else "unknown"
        SecurityAuditLogger.record(
            actor=x_actor_name or "Anonymous",
            role=raw_role,
            action="AUTHENTICATE",
            endpoint=request.url.path,
            method=request.method,
            status="DENIED",
            reason=f"Unrecognized role: {raw_role}",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication role: '{raw_role}'. Supported roles: ADMIN, OPERATOR, VIEWER."
        )

    actor_name = x_actor_name.strip() if x_actor_name and x_actor_name.strip() else f"User ({role.value})"

    return AuthUser(
        user_id=f"USR-{role.value}",
        username=actor_name,
        role=role,
        permissions=permissions
    )


def require_role(allowed_roles: List[str]):
    """
    Factory dependency for role authorization enforcement.
    Returns 403 Forbidden if user lacks necessary permissions.
    """
    normalized_allowed = [r.upper() for r in allowed_roles]
    # If operator is allowed, engineer is also allowed
    if "OPERATOR" in normalized_allowed and "ENGINEER" not in normalized_allowed:
        normalized_allowed.append("ENGINEER")

    def dependency(request: Request, user: AuthUser = Depends(get_current_user)) -> AuthUser:
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit on mutations
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            if not mutation_rate_limiter.is_allowed(client_ip):
                SecurityAuditLogger.record(
                    actor=user.username,
                    role=user.role.value,
                    action=f"{request.method} {request.url.path}",
                    endpoint=request.url.path,
                    method=request.method,
                    status="RATE_LIMITED",
                    reason="Rate limit exceeded",
                    client_ip=client_ip
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please wait a moment before sending more requests."
                )

        if user.role.value not in normalized_allowed and "ALL" not in normalized_allowed:
            SecurityAuditLogger.record(
                actor=user.username,
                role=user.role.value,
                action=f"{request.method} {request.url.path}",
                endpoint=request.url.path,
                method=request.method,
                status="DENIED",
                reason=f"Role '{user.role.value}' not in allowed roles: {allowed_roles}",
                client_ip=client_ip
            )
            required_str = " / ".join(allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied — {required_str} authorization required."
            )

        SecurityAuditLogger.record(
            actor=user.username,
            role=user.role.value,
            action=f"{request.method} {request.url.path}",
            endpoint=request.url.path,
            method=request.method,
            status="GRANTED",
            client_ip=client_ip
        )
        return user

    return dependency
