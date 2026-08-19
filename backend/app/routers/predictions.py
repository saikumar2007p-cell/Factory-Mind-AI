"""
backend/app/routers/predictions.py

ML Prognostics & Inference API routes.
"""

from typing import List, Optional
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.services.storage_service import StorageService
from backend.app.schemas.prediction import (
    PredictionResponse,
    InferenceRequest
)
from ml.inference import get_inference_engine

router = APIRouter(prefix="/predictions", tags=["Predictions & Inference"])


@router.post("/infer", response_model=PredictionResponse)
async def run_inference_on_window(
    request: InferenceRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Executes real Stage 2 feature engineering & ML inference on a submitted observation window,
    persisting the resulting prognostics directly into the database.
    """
    service = StorageService(session)
    machine = await service.get_machine_by_id(request.machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {request.machine_id} not found."
        )

    if not request.observations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Observation window cannot be empty."
        )

    # Convert observations to DataFrame
    df_window = pd.DataFrame(request.observations)
    if "unit_number" not in df_window.columns:
        df_window["unit_number"] = machine.unit_number

    engine = get_inference_engine()
    try:
        inference_result = engine.predict_window(df_window, apply_hysteresis=request.apply_hysteresis)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Inference error: {str(e)}"
        )

    # Persist via Stage 3 StorageService
    pred, _, _ = await service.persist_inference_cycle(machine.id, inference_result)
    await session.commit()

    return PredictionResponse(**pred.to_dict())


@router.get("/{machine_id}/latest", response_model=PredictionResponse)
async def get_latest_machine_prediction(
    machine_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Retrieves the most recent prognostic state for a machine."""
    service = StorageService(session)
    pred = await service.get_latest_prediction(machine_id)
    if not pred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No predictions found for machine ID {machine_id}."
        )
    return PredictionResponse(**pred.to_dict())


@router.get("/{machine_id}/history", response_model=List[PredictionResponse])
async def get_machine_prediction_history(
    machine_id: int,
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_db)
):
    """Retrieves chronological prognostic history for degradation charting."""
    service = StorageService(session)
    preds = await service.get_prediction_history(machine_id, limit=limit)
    return [PredictionResponse(**p.to_dict()) for p in preds]
