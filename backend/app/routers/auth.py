"""
backend/app/routers/auth.py

Authentication, Session Identity, Role Management & Security Audit Logs Router.
"""

from typing import List, Dict, Any, Optional
import hashlib
import secrets
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field, EmailStr

from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.security import (
    AuthUser,
    UserRole,
    SecurityAuditLogger,
    mutation_rate_limiter,
    get_current_user,
    require_role
)

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])


def hash_password(password: str) -> str:
    """PBKDF2-SHA256 password hash with unique random salt."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"pbkdf2_sha256${salt}${key.hex()}"


def verify_password(password: str, hashed: Optional[str]) -> bool:
    """Verifies password against PBKDF2 hash."""
    if not hashed:
        return False
    parts = hashed.split('$')
    if len(parts) != 3 or parts[0] != 'pbkdf2_sha256':
        return False
    salt = parts[1]
    expected_hex = parts[2]
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return secrets.compare_digest(key.hex(), expected_hex)


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255, description="User email address")
    password: str = Field(min_length=6, max_length=128, description="User password")
    display_name: Optional[str] = Field(default=None, max_length=200)
    role: Optional[str] = Field(default="ADMIN", description="ADMIN | OPERATOR")


class LoginRequest(BaseModel):
    email: str = Field(description="User email address or username")
    password: str = Field(description="User password")


class AuthResponse(BaseModel):
    user_id: str
    db_user_id: int
    username: str
    display_name: str
    email: str
    role: str
    permissions: List[str]
    message: str


class RoleSwitchRequest(BaseModel):
    role: str = Field(description="Desired role: ADMIN, OPERATOR")
    actor_name: Optional[str] = Field(default=None, max_length=100)


class RoleInfo(BaseModel):
    role: str
    display_name: str
    description: str
    permissions: List[str]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Registers a new account in the persistent database with hashed password credentials.
    """
    email_clean = payload.email.strip().lower()
    raw_role = (payload.role or "ADMIN").strip().upper()
    if raw_role not in [r.value for r in UserRole]:
        raw_role = "ADMIN"
    target_role = UserRole(raw_role)

    # Check if user already exists
    stmt = select(User).where((User.email == email_clean) | (User.username == email_clean))
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    
    base_username = email_clean.split('@')[0]
    display = payload.display_name.strip() if payload.display_name else base_username.replace('.', ' ').title()

    if existing:
        # Update existing user with new credentials and role seamlessly
        existing.password_hash = hash_password(payload.password)
        if payload.display_name and payload.display_name.strip():
            existing.display_name = payload.display_name.strip()
        existing.role = target_role.value
        existing.is_active = True
        existing.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(existing)
        target_user = existing
    else:
        new_user = User(
            username=email_clean,
            display_name=display,
            email=email_clean,
            password_hash=hash_password(payload.password),
            role=target_role.value,
            is_active=True,
            last_login_at=datetime.now(timezone.utc)
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        target_user = new_user

    if target_role == UserRole.ADMIN:
        permissions = ["read", "write", "manage_work_orders", "verify", "admin_config", "view_security_logs"]
    else:
        permissions = ["read", "write", "manage_work_orders", "verify"]

    client_ip = request.client.host if request.client else "unknown"
    SecurityAuditLogger.record(
        actor=target_user.display_name,
        role=target_role.value,
        action=f"USER_REGISTER({email_clean})",
        endpoint="/api/v1/auth/register",
        method="POST",
        status="GRANTED",
        client_ip=client_ip
    )

    return AuthResponse(
        user_id=f"USR-{target_user.id}",
        db_user_id=target_user.id,
        username=target_user.username,
        display_name=target_user.display_name,
        email=target_user.email or email_clean,
        role=target_user.role,
        permissions=permissions,
        message="Registration successful"
    )


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticates a user against persistent database records.
    """
    ident = payload.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"

    stmt = select(User).where((User.email == ident) | (User.username == ident))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        SecurityAuditLogger.record(
            actor=ident,
            role="UNKNOWN",
            action="LOGIN_FAILED_NOT_FOUND",
            endpoint="/api/v1/auth/login",
            method="POST",
            status="DENIED",
            reason="User not found",
            client_ip=client_ip
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Contact an administrator."
        )

    # Verify password if user has password_hash
    if user.password_hash:
        if not verify_password(payload.password, user.password_hash):
            SecurityAuditLogger.record(
                actor=user.display_name,
                role=user.role,
                action="LOGIN_FAILED_BAD_PASSWORD",
                endpoint="/api/v1/auth/login",
                method="POST",
                status="DENIED",
                reason="Password mismatch",
                client_ip=client_ip
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password."
            )
    else:
        # Legacy user created without password: set their password now on successful initial login
        user.password_hash = hash_password(payload.password)

    user.last_login_at = datetime.now(timezone.utc)
    await db.commit()

    role_enum = UserRole(user.role) if user.role in [r.value for r in UserRole] else UserRole.OPERATOR
    if role_enum == UserRole.ADMIN:
        permissions = ["read", "write", "manage_work_orders", "verify", "admin_config", "view_security_logs"]
    elif role_enum in (UserRole.OPERATOR, UserRole.ENGINEER):
        permissions = ["read", "write", "manage_work_orders", "verify"]
    else:
        permissions = ["read"]

    SecurityAuditLogger.record(
        actor=user.display_name,
        role=user.role,
        action="USER_LOGIN_SUCCESS",
        endpoint="/api/v1/auth/login",
        method="POST",
        status="GRANTED",
        client_ip=client_ip
    )

    return AuthResponse(
        user_id=f"USR-{user.id}",
        db_user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        email=user.email or ident,
        role=user.role,
        permissions=permissions,
        message="Login successful"
    )


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
            description="Full authorized access across all operations, data source configurations, work orders, system settings, user management, and security audit logs.",
            permissions=["read", "write", "manage_work_orders", "verify", "admin_config", "view_security_logs"]
        ),
        RoleInfo(
            role=UserRole.OPERATOR.value,
            display_name="Operations Engineer",
            description="Full operational authority to investigate machine changes, create, assign, execute, and verify maintenance work orders, and acknowledge alerts.",
            permissions=["read", "write", "manage_work_orders", "verify"]
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
            detail=f"Invalid role '{payload.role}'. Supported roles: ADMIN, OPERATOR."
        )

    target_role = UserRole(raw_role)
    actor_name = payload.actor_name.strip() if payload.actor_name and payload.actor_name.strip() else f"User ({target_role.value})"

    if target_role == UserRole.ADMIN:
        permissions = ["read", "write", "manage_work_orders", "verify", "admin_config", "view_security_logs"]
    else:
        permissions = ["read", "write", "manage_work_orders", "verify"]

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
