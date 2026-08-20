"""
backend/app/routers/users.py

Named User Management Router for FactoryMind AI.

Provides CRUD operations on the persistent user identity registry.
All mutating operations require ADMIN authorization.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.app.database import get_db
from backend.app.security import AuthUser, require_role, get_current_user
from backend.app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["User Management"])

require_admin = require_role(["admin"])
require_viewer = require_role(["admin", "operator", "viewer"])


class CreateUserRequest(BaseModel):
    username: str = Field(min_length=2, max_length=100, description="Unique username")
    display_name: str = Field(min_length=2, max_length=200)
    role: str = Field(description="ADMIN | OPERATOR | ENGINEER | VIEWER")
    email: Optional[str] = Field(default=None, max_length=255)
    notes: Optional[str] = None


class UpdateUserRoleRequest(BaseModel):
    new_role: str = Field(description="ADMIN | OPERATOR | ENGINEER | VIEWER")
    updated_by: Optional[str] = None


@router.get("", response_model=List[dict])
async def list_users(
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Returns all registered users. Administrator access required."""
    svc = UserService(db)
    users = await svc.get_all_users()
    return [u.to_dict() for u in users]


@router.get("/me", response_model=dict)
async def get_my_user_record(
    user: AuthUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Resolves the current actor's database user record.
    Auto-creates a record on first encounter if x_actor_name was provided.
    """
    svc = UserService(db)
    db_user = await svc.get_or_create_user(
        username=user.username,
        role=user.role.value,
        display_name=user.username
    )
    await db.commit()
    return db_user.to_dict()


@router.get("/{user_id}", response_model=dict)
async def get_user(
    user_id: int,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Returns a specific user by ID. Administrator access required."""
    svc = UserService(db)
    db_user = await svc.get_user_by_id(user_id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User {user_id} not found.")
    return db_user.to_dict()


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: CreateUserRequest,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new user in the registry.
    Administrator authorization required.
    No passwords stored — auth remains header-based.
    """
    svc = UserService(db)
    try:
        new_user = await svc.create_user(
            username=payload.username,
            display_name=payload.display_name,
            role=payload.role,
            email=payload.email,
            created_by=user.username,
            notes=payload.notes
        )
        await db.commit()
        return new_user.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.patch("/{user_id}/role", response_model=dict)
async def update_user_role(
    user_id: int,
    payload: UpdateUserRoleRequest,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Changes a user's role.
    Prevents downgrading the last active Administrator.
    Administrator authorization required.
    """
    svc = UserService(db)
    try:
        updated = await svc.update_user_role(
            user_id=user_id,
            new_role=payload.new_role,
            updated_by=payload.updated_by or user.username
        )
        await db.commit()
        return updated.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{user_id}", response_model=dict)
async def deactivate_user(
    user_id: int,
    user: AuthUser = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Deactivates a user (soft delete — not permanently removed).
    Prevents deactivating the last active Administrator.
    Administrator authorization required.
    """
    svc = UserService(db)
    try:
        deactivated = await svc.deactivate_user(
            user_id=user_id,
            deactivated_by=user.username
        )
        await db.commit()
        return {
            **deactivated.to_dict(),
            "message": f"User '{deactivated.username}' has been deactivated."
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
