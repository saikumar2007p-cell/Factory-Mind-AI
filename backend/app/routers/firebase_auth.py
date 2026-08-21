"""
backend/app/routers/firebase_auth.py

Firebase Authentication endpoints for FactoryMind AI.
Handles token verification, user sync to Firestore, and admin role assignment.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from pydantic import BaseModel, Field
import logging

from backend.app.security import AuthUser, require_role, get_current_user
from backend.app.firebase_admin_init import is_firebase_ready, get_auth_client
from backend.app.services import firestore_service

logger = logging.getLogger("factorymind.firebase_auth")

router = APIRouter(prefix="/firebase", tags=["Firebase Authentication"])


class SetRoleRequest(BaseModel):
    uid: str = Field(description="Firebase UID of the target user")
    role: str = Field(description="Role to assign: ADMIN or OPERATOR")
    organization_id: str = Field(description="Organization ID for tenant isolation")


class SyncUserRequest(BaseModel):
    uid: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    role: Optional[str] = None
    organization_id: Optional[str] = None


class VerifyResponse(BaseModel):
    uid: str
    email: str
    role: str
    organization_id: str
    email_verified: bool


# ============================================================================
# POST /firebase/set-role — Admin-only: assign custom claims
# ============================================================================

@router.post("/set-role", response_model=Dict[str, Any])
async def set_user_role(
    payload: SetRoleRequest,
    user: AuthUser = Depends(require_role(["ADMIN"])),
):
    """
    Set Firebase custom claims (role + organizationId) on a user.
    Admin-only endpoint. The target user must sign out and back in to pick up new claims.
    """
    if not is_firebase_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Firebase Admin SDK not initialized. Check FIREBASE_SERVICE_ACCOUNT_PATH.",
        )

    valid_roles = ["ADMIN", "OPERATOR"]
    normalized_role = payload.role.strip().upper()
    if normalized_role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{payload.role}'. Must be one of: {valid_roles}",
        )

    try:
        auth_client = get_auth_client()
        # Set custom claims
        auth_client.set_custom_user_claims(payload.uid, {
            "role": normalized_role,
            "organizationId": payload.organization_id,
        })

        # Sync to Firestore users collection
        firebase_user = auth_client.get_user(payload.uid)
        firestore_service.upsert_user(payload.uid, {
            "email": firebase_user.email or "",
            "name": firebase_user.display_name or firebase_user.email or "",
            "role": normalized_role,
            "organizationId": payload.organization_id,
            "active": not firebase_user.disabled,
        })

        # Audit log
        firestore_service.log_audit_event({
            "organizationId": payload.organization_id,
            "userId": user.user_id,
            "role": user.role.value,
            "action": "SET_USER_ROLE",
            "resourceType": "user",
            "resourceId": payload.uid,
            "details": {"newRole": normalized_role, "targetUid": payload.uid},
        })

        logger.info(f"[Firebase Auth] Set role={normalized_role} org={payload.organization_id} for uid={payload.uid}")

        return {
            "status": "SUCCESS",
            "uid": payload.uid,
            "role": normalized_role,
            "organizationId": payload.organization_id,
            "message": "Custom claims updated. User must re-login to pick up new role.",
        }

    except Exception as e:
        logger.error(f"[Firebase Auth] set_user_role failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set role: {str(e)}",
        )


# ============================================================================
# GET /firebase/verify — Verify a Firebase ID token
# ============================================================================

@router.get("/verify", response_model=VerifyResponse)
async def verify_token(user: AuthUser = Depends(get_current_user)):
    """
    Returns the decoded Firebase identity of the current user.
    Useful for frontend to confirm token validity and role assignment.
    """
    return VerifyResponse(
        uid=user.user_id,
        email=user.username,
        role=user.role.value,
        organization_id=getattr(user, "organization_id", ""),
        email_verified=True,
    )


# ============================================================================
# POST /firebase/sync-user — Sync Firebase user profile to Firestore
# ============================================================================

@router.post("/sync-user", response_model=Dict[str, Any])
async def sync_user(
    payload: SyncUserRequest,
    user: AuthUser = Depends(get_current_user),
):
    """
    Syncs the current authenticated user's profile to Firestore users/{uid}.
    Called after login to ensure Firestore has up-to-date user data.
    """
    uid = payload.uid or user.user_id
    data = {
        "email": payload.email or user.username,
        "name": payload.name or user.username,
        "role": payload.role or user.role.value,
        "organizationId": payload.organization_id or getattr(user, "organization_id", ""),
        "active": True,
    }

    success = firestore_service.upsert_user(uid, data)

    if success:
        firestore_service.log_audit_event({
            "organizationId": data["organizationId"],
            "userId": uid,
            "role": data["role"],
            "action": "USER_LOGIN_SYNC",
            "resourceType": "user",
            "resourceId": uid,
        })

    return {
        "status": "SYNCED" if success else "SKIPPED",
        "uid": uid,
        "firestore_available": success,
    }
