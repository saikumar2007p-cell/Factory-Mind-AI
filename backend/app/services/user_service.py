"""
backend/app/services/user_service.py

Named User Identity Registry Service for FactoryMind AI.

Provides CRUD operations on the users table, enforcing:
  - At least one active ADMIN must always exist
  - Cannot downgrade the last active ADMIN
  - Upsert semantics for header-based auth: auto-creates a user record
    on first encounter when x_actor_name header is present
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.user import User
import logging

logger = logging.getLogger("factorymind.user_service")

VALID_ROLES = {"ADMIN", "OPERATOR"}


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def get_all_users(self) -> List[User]:
        """Returns all users ordered by role priority then username."""
        stmt = select(User).order_by(User.role, User.username)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        stmt = select(User).where(User.username == username)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_admin_count(self) -> int:
        """Returns the number of currently active ADMIN users."""
        stmt = select(func.count()).where(
            User.role == "ADMIN",
            User.is_active == True
        )
        result = await self.session.execute(stmt)
        return result.scalar() or 0

    # -------------------------------------------------------------------------
    # MUTATIONS
    # -------------------------------------------------------------------------

    async def create_user(
        self,
        username: str,
        display_name: str,
        role: str,
        email: Optional[str] = None,
        created_by: Optional[str] = None,
        notes: Optional[str] = None
    ) -> User:
        """
        Creates a new named user in the registry.
        Raises ValueError for invalid role or duplicate username.
        """
        role = role.upper()
        if role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{role}'. Must be one of: {', '.join(VALID_ROLES)}")

        existing = await self.get_user_by_username(username)
        if existing:
            raise ValueError(f"Username '{username}' is already registered.")

        user = User(
            username=username.strip(),
            display_name=display_name.strip(),
            email=email.strip() if email else None,
            role=role,
            is_active=True,
            created_by=created_by,
            notes=notes
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        logger.info(f"Created user '{username}' with role {role} (created by: {created_by})")
        return user

    async def update_user_role(
        self,
        user_id: int,
        new_role: str,
        updated_by: str
    ) -> User:
        """
        Changes a user's role.
        Prevents downgrading the last active ADMIN.
        """
        new_role = new_role.upper()
        if new_role not in VALID_ROLES:
            raise ValueError(f"Invalid role '{new_role}'.")

        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User ID {user_id} not found.")

        # Safety: cannot downgrade last active admin
        if user.role == "ADMIN" and new_role != "ADMIN":
            admin_count = await self.get_active_admin_count()
            if admin_count <= 1:
                raise ValueError(
                    "Cannot change role: this is the last active Administrator. "
                    "Promote another user to ADMIN first."
                )

        old_role = user.role
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(role=new_role, updated_at=datetime.now(timezone.utc))
        )
        logger.info(f"User '{user.username}' role changed {old_role} → {new_role} by {updated_by}")
        return await self.get_user_by_id(user_id)

    async def deactivate_user(self, user_id: int, deactivated_by: str) -> User:
        """
        Deactivates a user (soft delete).
        Prevents deactivating the last active ADMIN.
        """
        user = await self.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User ID {user_id} not found.")

        if user.role == "ADMIN":
            admin_count = await self.get_active_admin_count()
            if admin_count <= 1:
                raise ValueError(
                    "Cannot deactivate: this is the last active Administrator."
                )

        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )
        logger.info(f"User '{user.username}' deactivated by {deactivated_by}")
        return await self.get_user_by_id(user_id)

    async def record_login(self, username: str) -> None:
        """Updates last_login_at for audit purposes."""
        await self.session.execute(
            update(User)
            .where(User.username == username)
            .values(last_login_at=datetime.now(timezone.utc))
        )

    async def get_or_create_user(
        self,
        username: str,
        role: str,
        display_name: Optional[str] = None
    ) -> User:
        """
        Upsert semantics for header-based auth.
        Creates a user record on first encounter; returns existing on subsequent calls.
        """
        user = await self.get_user_by_username(username)
        if user:
            # Update last_login_at and role if it changed externally
            await self.session.execute(
                update(User)
                .where(User.username == username)
                .values(last_login_at=datetime.now(timezone.utc))
            )
            return user

        # Auto-create
        return await self.create_user(
            username=username,
            display_name=display_name or username,
            role=role.upper(),
            created_by="SYSTEM_AUTO"
        )
