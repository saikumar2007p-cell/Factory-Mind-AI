"""
backend/app/security.py

Enterprise Role-Based Access Control (RBAC), Rate Limiting, and Security Audit Logging for FactoryMind AI.

Authentication modes:
- FIREBASE (production): Verifies Firebase ID token from Authorization: Bearer header.
  Extracts uid, email, role, organizationId from Firebase custom claims.
- DEVELOPMENT (fallback): Uses X-User-Role / X-Actor-Name headers for local dev/testing.

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

from backend.app.config import settings

logger = logging.getLogger("factorymind.security")


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    ENGINEER = "ENGINEER"
    VIEWER = "VIEWER"


class AuthUser(BaseModel):
    user_id: str = "USR-DEV-001"
    db_user_id: Optional[int] = None
    username: str = "Factory Engineer"
    role: UserRole = UserRole.OPERATOR
    permissions: List[str] = Field(default_factory=list)
    authenticated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    organization_id: str = ""
    auth_method: str = "DEVELOPMENT"  # FIREBASE or DEVELOPMENT


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
    status: str  # GRANTED, DENIED, RATE_LIMITED
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
        client_ip: Optional[str] = None,
        organization_id: Optional[str] = None,
        user_id: Optional[str] = None,
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

        # Async write to Firestore audit log (fire-and-forget, non-blocking)
        if organization_id:
            try:
                from backend.app.services.firestore_service import log_audit_event
                log_audit_event({
                    "organizationId": organization_id,
                    "userId": user_id or actor,
                    "role": role,
                    "action": action,
                    "resourceType": "security",
                    "resourceId": endpoint,
                    "details": {"method": method, "status": status, "reason": reason},
                })
            except Exception:
                pass  # Firestore write is best-effort

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
# Firebase Token Verification
# ============================================================================

def _verify_firebase_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies a Firebase ID token and returns decoded claims.
    Returns None if verification fails or Firebase is not initialized.
    """
    try:
        from backend.app.firebase_admin_init import is_firebase_ready, get_auth_client
        if not is_firebase_ready():
            return None
        auth_client = get_auth_client()
        decoded = auth_client.verify_id_token(token)
        return decoded
    except Exception as e:
        logger.warning(f"[Firebase Auth] Token verification failed: {e}")
        return None


def _role_from_claims(claims: Dict[str, Any]) -> UserRole:
    """Extract UserRole from Firebase custom claims."""
    raw_role = (claims.get("role") or "VIEWER").strip().upper()
    if raw_role in ["ADMIN", "ROOT", "SYSTEM_ADMIN"]:
        return UserRole.ADMIN
    elif raw_role in ["OPERATOR", "ENGINEER", "SUPERVISOR", "TECHNICIAN"]:
        return UserRole.OPERATOR
    elif raw_role in ["VIEWER", "READONLY", "AUDITOR"]:
        return UserRole.VIEWER
    return UserRole.VIEWER


def _permissions_for_role(role: UserRole) -> List[str]:
    """Return permissions list for a given role."""
    if role == UserRole.ADMIN:
        return ["read", "write", "manage_work_orders", "verify", "admin_config", "view_security_logs"]
    elif role in [UserRole.OPERATOR, UserRole.ENGINEER]:
        return ["read", "write", "manage_work_orders", "verify"]
    else:
        return ["read"]


# ============================================================================
# FastAPI Authentication & Authorization Dependencies
# ============================================================================

def get_current_user(
    request: Request,
    authorization: Optional[str] = Header(default=None, description="Bearer <Firebase ID Token>"),
    x_user_role: Optional[str] = Header(default=None, description="Active user role header (dev mode)"),
    x_admin_role: Optional[str] = Header(default=None, description="Legacy admin role header fallback"),
    x_actor_name: Optional[str] = Header(default=None, description="Actor identity header (dev mode)")
) -> AuthUser:
    """
    Extracts and validates the current user identity.

    Production mode (FIREBASE_AUTH_MODE=FIREBASE):
        Requires Authorization: Bearer <token> header.
        Verifies Firebase ID token and extracts uid, email, role, organizationId.

    Development mode (FIREBASE_AUTH_MODE=DEVELOPMENT):
        Falls back to X-User-Role / X-Actor-Name headers for local testing.
        Firebase token is still preferred if present.
    """
    # --- Try Firebase token first (always, regardless of mode) ---
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
        if token:
            decoded = _verify_firebase_token(token)
            if decoded:
                role = _role_from_claims(decoded)
                permissions = _permissions_for_role(role)
                org_id = decoded.get("organizationId", decoded.get("organization_id", ""))

                return AuthUser(
                    user_id=decoded.get("uid", ""),
                    username=decoded.get("email", decoded.get("name", "Firebase User")),
                    role=role,
                    permissions=permissions,
                    organization_id=org_id,
                    auth_method="FIREBASE",
                )

            # Token was provided but invalid
            if settings.is_firebase_auth_enabled:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired Firebase authentication token.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    # --- Production mode requires Firebase token ---
    if settings.is_firebase_auth_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase authentication required. Provide Authorization: Bearer <token> header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # --- Development fallback: header-based RBAC ---
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
        permissions=permissions,
        auth_method="DEVELOPMENT",
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
                    client_ip=client_ip,
                    organization_id=user.organization_id,
                    user_id=user.user_id,
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
                client_ip=client_ip,
                organization_id=user.organization_id,
                user_id=user.user_id,
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
            client_ip=client_ip,
            organization_id=user.organization_id,
            user_id=user.user_id,
        )
        return user

    return dependency
