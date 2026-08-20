"""
backend/app/services/machine_registration_service.py

Machine Registration Review Service for FactoryMind AI.

When uploaded data references unknown machine IDs, stages them as
PENDING_REVIEW rather than auto-creating ghost machines or discarding data.
"""

import json
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.machine_registration_request import MachineRegistrationRequest
from backend.app.models.machine import Machine
import logging

logger = logging.getLogger("factorymind.machine_registration")

# Directory for staged (quarantined) upload data
QUARANTINE_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "quarantine"


class MachineRegistrationService:
    def __init__(self, session: AsyncSession):
        self.session = session

    # -------------------------------------------------------------------------
    # QUERIES
    # -------------------------------------------------------------------------

    async def get_all_requests(self, status_filter: Optional[str] = None) -> List[MachineRegistrationRequest]:
        stmt = select(MachineRegistrationRequest)
        if status_filter:
            stmt = stmt.where(MachineRegistrationRequest.status == status_filter)
        stmt = stmt.order_by(MachineRegistrationRequest.requested_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_requests(self) -> List[MachineRegistrationRequest]:
        return await self.get_all_requests(status_filter="PENDING_REVIEW")

    async def get_request_by_id(self, request_id: int) -> Optional[MachineRegistrationRequest]:
        stmt = select(MachineRegistrationRequest).where(MachineRegistrationRequest.id == request_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_count(self) -> int:
        """Returns count of pending requests — used for nav badge."""
        reqs = await self.get_pending_requests()
        return len(reqs)

    # -------------------------------------------------------------------------
    # STAGE FOR REVIEW (called from upload endpoint)
    # -------------------------------------------------------------------------

    async def stage_upload_for_review(
        self,
        requested_machine_id: str,
        source_filename: str,
        source_row_count: int,
        detected_columns: List[str],
        sample_data: List[Dict[str, Any]],   # First 5 rows
        full_data: Optional[List[Dict[str, Any]]] = None  # Full parsed rows for later ingestion
    ) -> MachineRegistrationRequest:
        """
        Creates a PENDING_REVIEW registration request and optionally
        quarantines the full data to disk for later ingestion on approval.
        """
        QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)

        quarantine_path = None
        if full_data:
            safe_name = "".join(c if c.isalnum() or c in "-_." else "_" for c in requested_machine_id)
            ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename = f"quarantine_{safe_name}_{ts}.json"
            quarantine_path = str(QUARANTINE_DIR / filename)
            try:
                with open(quarantine_path, "w", encoding="utf-8") as f:
                    json.dump(full_data, f)
            except Exception as e:
                logger.warning(f"Failed to quarantine data for {requested_machine_id}: {e}")
                quarantine_path = None

        req = MachineRegistrationRequest(
            requested_machine_id=requested_machine_id,
            source_filename=source_filename,
            source_row_count=source_row_count,
            detected_columns=detected_columns,
            sample_data=sample_data[:5],
            quarantine_path=quarantine_path,
            status="PENDING_REVIEW"
        )
        self.session.add(req)
        await self.session.flush()
        await self.session.refresh(req)
        logger.info(
            f"Staged machine registration request for ID '{requested_machine_id}' "
            f"from '{source_filename}' ({source_row_count} rows) — PENDING_REVIEW (id={req.id})"
        )
        return req

    # -------------------------------------------------------------------------
    # APPROVE
    # -------------------------------------------------------------------------

    async def approve_registration(
        self,
        request_id: int,
        machine_name: str,
        machine_type: str,
        location: str,
        reviewed_by: str,
        review_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Administrator approves a pending registration:
          1. Creates the Machine record
          2. Marks the request as APPROVED
          3. Returns created machine + ingestion summary
        """
        req = await self.get_request_by_id(request_id)
        if not req:
            raise ValueError(f"Registration request ID {request_id} not found.")
        if req.status != "PENDING_REVIEW":
            raise ValueError(
                f"Request {request_id} is already '{req.status}'. "
                "Only PENDING_REVIEW requests can be approved."
            )

        now = datetime.now(timezone.utc)

        # Create the machine
        # Generate a unique unit_number using max existing + 1
        from sqlalchemy import func as sqlfunc
        max_stmt = select(sqlfunc.max(Machine.unit_number))
        max_result = await self.session.execute(max_stmt)
        max_unit = max_result.scalar() or 0
        new_unit_number = max_unit + 1

        machine = Machine(
            unit_number=new_unit_number,
            name=machine_name,
            machine_type=machine_type,
            location=location,
            status="OPERATIONAL",
            telemetry_state="NO_DATA",
            current_cycle=0
        )
        self.session.add(machine)
        await self.session.flush()
        await self.session.refresh(machine)

        # Update request
        await self.session.execute(
            update(MachineRegistrationRequest)
            .where(MachineRegistrationRequest.id == request_id)
            .values(
                status="APPROVED",
                reviewed_at=now,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
                auto_created_machine_id=machine.id,
                updated_at=now
            )
        )

        logger.info(
            f"Registration request {request_id} APPROVED by {reviewed_by}. "
            f"Created machine '{machine_name}' (id={machine.id}, unit=#{new_unit_number})"
        )

        # Load quarantined data count if available
        staged_rows = 0
        if req.quarantine_path and os.path.exists(req.quarantine_path):
            try:
                with open(req.quarantine_path, "r", encoding="utf-8") as f:
                    staged_data = json.load(f)
                staged_rows = len(staged_data)
            except Exception:
                pass

        return {
            "status": "APPROVED",
            "request_id": request_id,
            "created_machine_id": machine.id,
            "unit_number": new_unit_number,
            "machine_name": machine_name,
            "staged_rows_available": staged_rows,
            "note": (
                f"Machine created. {staged_rows} staged rows available for ingestion."
                if staged_rows > 0
                else "Machine created. No staged data available — upload new data for this machine."
            )
        }

    # -------------------------------------------------------------------------
    # REJECT
    # -------------------------------------------------------------------------

    async def reject_registration(
        self,
        request_id: int,
        reviewed_by: str,
        review_notes: str
    ) -> Dict[str, Any]:
        """
        Administrator rejects a pending registration.
        Quarantined data is removed from disk.
        """
        req = await self.get_request_by_id(request_id)
        if not req:
            raise ValueError(f"Registration request ID {request_id} not found.")
        if req.status != "PENDING_REVIEW":
            raise ValueError(
                f"Request {request_id} is already '{req.status}'. "
                "Only PENDING_REVIEW requests can be rejected."
            )

        now = datetime.now(timezone.utc)

        # Clean up quarantine file
        quarantine_cleaned = False
        if req.quarantine_path and os.path.exists(req.quarantine_path):
            try:
                os.remove(req.quarantine_path)
                quarantine_cleaned = True
            except Exception as e:
                logger.warning(f"Failed to delete quarantine file {req.quarantine_path}: {e}")

        await self.session.execute(
            update(MachineRegistrationRequest)
            .where(MachineRegistrationRequest.id == request_id)
            .values(
                status="REJECTED",
                reviewed_at=now,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
                updated_at=now
            )
        )

        logger.info(
            f"Registration request {request_id} REJECTED by {reviewed_by}. "
            f"Quarantine file removed: {quarantine_cleaned}"
        )

        return {
            "status": "REJECTED",
            "request_id": request_id,
            "reviewed_by": reviewed_by,
            "quarantine_data_removed": quarantine_cleaned
        }
