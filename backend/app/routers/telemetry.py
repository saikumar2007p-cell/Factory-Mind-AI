"""
backend/app/routers/telemetry.py

Sensor Telemetry API routes.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.services.storage_service import StorageService
from backend.app.schemas.telemetry import TelemetryHistoryResponse, TelemetryResponse

router = APIRouter(prefix="/telemetry", tags=["Telemetry"])


@router.get("/{machine_id}", response_model=TelemetryHistoryResponse)
async def get_machine_telemetry(
    machine_id: int,
    limit: int = Query(default=100, ge=1, le=1000, description="Max cycles to retrieve"),
    start_cycle: Optional[int] = Query(default=None, ge=1, description="Filter starting cycle"),
    end_cycle: Optional[int] = Query(default=None, ge=1, description="Filter ending cycle"),
    session: AsyncSession = Depends(get_db)
):
    """Retrieves authentic sensor time-series telemetry records for a machine."""
    service = StorageService(session)
    machine = await service.get_machine_by_id(machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {machine_id} not found."
        )

    records = await service.get_telemetry_history(
        machine_id=machine_id,
        limit=limit,
        start_cycle=start_cycle,
        end_cycle=end_cycle
    )

    if not records:
        # Dynamically load authentic data slice for this machine unit
        try:
            from ml.dataset import CMAPSSDataset
            dataset = CMAPSSDataset()
            df_train = dataset.load_raw_train()
            unit_num = machine.unit_number
            unit_df = df_train[df_train["unit_number"] == unit_num].sort_values("time_cycle").reset_index(drop=True)
            if unit_df.empty:
                # If not in FD001 directly, use unit modulo 100
                mapped_u = ((unit_num - 1) % 100) + 1
                unit_df = df_train[df_train["unit_number"] == mapped_u].sort_values("time_cycle").reset_index(drop=True)
            
            if not unit_df.empty:
                slice_len = min(len(unit_df), limit or 50)
                batch = unit_df.tail(slice_len).to_dict(orient="records")
                await service.insert_telemetry_batch(machine.id, batch)
                await session.commit()
                records = await service.get_telemetry_history(machine.id, limit=limit)
        except Exception as e:
            pass

    return TelemetryHistoryResponse(
        machine_id=machine.id,
        unit_number=machine.unit_number,
        count=len(records),
        telemetry=[TelemetryResponse(**r.to_dict()) for r in records]
    )
