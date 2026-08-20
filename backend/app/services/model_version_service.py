"""
backend/app/services/model_version_service.py

Model Version Registry Service for FactoryMind AI.

Manages the full lifecycle: CANDIDATE → ACTIVE → RETIRED / ROLLBACK_CANDIDATE.
All state transitions are atomic and audit-logged.
Administrator approval is mandatory before any CANDIDATE can become ACTIVE.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.model_version import ModelVersion
from backend.app.models.machine import Machine
import logging

logger = logging.getLogger("factorymind.model_versions")


class ModelVersionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def get_version_history(self, machine_id: int) -> List[ModelVersion]:
        """Returns full version history for a machine, newest first."""
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.machine_id == machine_id)
            .order_by(ModelVersion.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_version(self, machine_id: int) -> Optional[ModelVersion]:
        """Returns the currently ACTIVE model version for a machine."""
        stmt = select(ModelVersion).where(
            ModelVersion.machine_id == machine_id,
            ModelVersion.status == "ACTIVE"
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_version_by_id(self, version_id: int) -> Optional[ModelVersion]:
        stmt = select(ModelVersion).where(ModelVersion.id == version_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_versions(self) -> List[ModelVersion]:
        """Returns all model versions across the fleet, newest first."""
        stmt = select(ModelVersion).order_by(ModelVersion.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_rollback_candidates(self, machine_id: int) -> List[ModelVersion]:
        """Returns all RETIRED/ROLLBACK_CANDIDATE versions available for rollback."""
        stmt = select(ModelVersion).where(
            ModelVersion.machine_id == machine_id,
            ModelVersion.status.in_(["RETIRED", "ROLLBACK_CANDIDATE"])
        ).order_by(ModelVersion.deployed_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # MUTATIONS
    # -------------------------------------------------------------------------

    async def register_candidate(
        self,
        machine_id: int,
        version: str,
        model_type: str = "LightGBM+IsolationForest",
        model_artifact_path: Optional[str] = None,
        training_dataset_id: Optional[str] = None,
        training_date: Optional[datetime] = None,
        training_sample_count: Optional[int] = None,
        feature_count: Optional[int] = None,
        validation_metrics: Optional[Dict[str, Any]] = None,
        parent_version_id: Optional[int] = None
    ) -> ModelVersion:
        """
        Registers a new CANDIDATE model version.
        Does not affect any currently ACTIVE version.
        """
        # Check machine exists
        machine_stmt = select(Machine).where(Machine.id == machine_id)
        machine_result = await self.session.execute(machine_stmt)
        machine = machine_result.scalar_one_or_none()
        if not machine:
            raise ValueError(f"Machine ID {machine_id} not found.")

        # Check no duplicate version string for this machine
        dup_stmt = select(ModelVersion).where(
            ModelVersion.machine_id == machine_id,
            ModelVersion.version == version
        )
        dup_result = await self.session.execute(dup_stmt)
        if dup_result.scalar_one_or_none():
            raise ValueError(f"Version '{version}' already exists for machine {machine_id}.")

        mv = ModelVersion(
            machine_id=machine_id,
            version=version,
            model_type=model_type,
            model_artifact_path=model_artifact_path,
            training_dataset_id=training_dataset_id,
            training_date=training_date,
            training_sample_count=training_sample_count,
            feature_count=feature_count,
            validation_metrics=validation_metrics,
            status="CANDIDATE",
            parent_version_id=parent_version_id
        )
        self.session.add(mv)
        await self.session.flush()
        await self.session.refresh(mv)
        logger.info(f"Registered CANDIDATE model version {version} for machine {machine_id} (id={mv.id})")
        return mv

    async def approve_and_deploy(
        self,
        version_id: int,
        approved_by: str,
        notes: Optional[str] = None
    ) -> ModelVersion:
        """
        Atomically:
          1. Retires the currently ACTIVE version (→ RETIRED)
          2. Promotes the CANDIDATE (→ ACTIVE)
        Requires ADMIN authorization (enforced at router level).
        """
        candidate = await self.get_version_by_id(version_id)
        if not candidate:
            raise ValueError(f"Model version ID {version_id} not found.")
        if candidate.status != "CANDIDATE":
            raise ValueError(
                f"Only CANDIDATE versions can be approved. "
                f"Version {version_id} has status '{candidate.status}'."
            )

        now = datetime.now(timezone.utc)

        # Retire current ACTIVE version
        current_active = await self.get_active_version(candidate.machine_id)
        if current_active:
            await self.session.execute(
                update(ModelVersion)
                .where(ModelVersion.id == current_active.id)
                .values(status="ROLLBACK_CANDIDATE", retired_at=now)
            )
            logger.info(
                f"Retired model version {current_active.version} "
                f"(id={current_active.id}) for machine {candidate.machine_id}"
            )

        # Promote candidate to ACTIVE
        await self.session.execute(
            update(ModelVersion)
            .where(ModelVersion.id == version_id)
            .values(
                status="ACTIVE",
                approved_by=approved_by,
                approved_at=now,
                deployed_at=now
            )
        )
        logger.info(
            f"Approved and deployed model version {candidate.version} "
            f"(id={version_id}) by {approved_by}"
        )
        return await self.get_version_by_id(version_id)

    async def rollback(
        self,
        machine_id: int,
        rollback_reason: str,
        rolled_back_by: str
    ) -> ModelVersion:
        """
        Rolls back to the most recent ROLLBACK_CANDIDATE / RETIRED version.
        Marks the current ACTIVE as RETIRED with rollback_reason.
        Requires ADMIN authorization (enforced at router level).
        """
        now = datetime.now(timezone.utc)

        current_active = await self.get_active_version(machine_id)
        candidates = await self.get_rollback_candidates(machine_id)

        if not candidates:
            raise ValueError(
                f"No rollback candidates available for machine {machine_id}. "
                "Cannot roll back — no previous version in registry."
            )

        rollback_target = candidates[0]  # Most recently retired

        # Retire current active
        if current_active:
            await self.session.execute(
                update(ModelVersion)
                .where(ModelVersion.id == current_active.id)
                .values(
                    status="RETIRED",
                    retired_at=now,
                    rollback_reason=rollback_reason
                )
            )

        # Restore rollback target to ACTIVE
        await self.session.execute(
            update(ModelVersion)
            .where(ModelVersion.id == rollback_target.id)
            .values(
                status="ACTIVE",
                deployed_at=now,
                approved_by=rolled_back_by,
                approved_at=now
            )
        )
        logger.warning(
            f"ROLLBACK executed for machine {machine_id}: "
            f"restored to version {rollback_target.version} by {rolled_back_by}. "
            f"Reason: {rollback_reason}"
        )
        return await self.get_version_by_id(rollback_target.id)
