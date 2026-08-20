"""
backend/app/routers/datasets.py

Multi-Dataset REST API for FactoryMind AI.
Provides endpoints for dataset registry, status, sensors, and ML capabilities.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.security import AuthUser, get_current_user, require_role

logger = logging.getLogger("factorymind.datasets")

router = APIRouter(prefix="/datasets", tags=["Datasets & Equipment"])


@router.get("/", response_model=List[Dict[str, Any]])
async def list_datasets(user: AuthUser = Depends(get_current_user)):
    """List all registered datasets with their metadata and availability status."""
    from ml.dataset_registry import get_all_datasets
    return [ds.to_dict() for ds in get_all_datasets()]


@router.get("/status", response_model=List[Dict[str, Any]])
async def get_dataset_statuses(user: AuthUser = Depends(get_current_user)):
    """Get download/processing status of all dataset adapters."""
    from ml.dataset_adapters import get_all_adapter_statuses
    return get_all_adapter_statuses()


@router.get("/equipment-types", response_model=List[Dict[str, Any]])
async def list_equipment_types(user: AuthUser = Depends(get_current_user)):
    """List all available equipment types with their dataset counts."""
    from ml.dataset_registry import get_available_equipment_types
    return get_available_equipment_types()


@router.get("/{dataset_id}")
async def get_dataset_detail(dataset_id: str, user: AuthUser = Depends(get_current_user)):
    """Get detailed metadata for a specific dataset."""
    from ml.dataset_registry import get_dataset
    ds = get_dataset(dataset_id)
    if not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")
    return ds.to_dict()


@router.get("/{dataset_id}/sensors", response_model=List[Dict[str, str]])
async def get_dataset_sensors(dataset_id: str, user: AuthUser = Depends(get_current_user)):
    """Get the actual sensors available in a specific dataset. No fabricated sensors."""
    from ml.dataset_adapters import get_adapter
    adapter = get_adapter(dataset_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"No adapter for dataset '{dataset_id}'.")
    sensors = adapter.get_sensors()
    if not sensors:
        return [{"id": "unavailable", "name": "Unavailable", "unit": "N/A", "type": "unavailable"}]
    return sensors


@router.get("/{dataset_id}/tasks", response_model=List[str])
async def get_supported_tasks(dataset_id: str, user: AuthUser = Depends(get_current_user)):
    """Get the ML tasks supported by a specific dataset."""
    from ml.dataset_adapters import get_adapter
    adapter = get_adapter(dataset_id)
    if not adapter:
        raise HTTPException(status_code=404, detail=f"No adapter for dataset '{dataset_id}'.")
    return adapter.get_supported_tasks()


@router.get("/{dataset_id}/availability")
async def check_dataset_availability(dataset_id: str, user: AuthUser = Depends(get_current_user)):
    """Check if dataset files are downloaded and ready."""
    from ml.dataset_adapters import get_adapter
    from ml.dataset_registry import get_dataset
    adapter = get_adapter(dataset_id)
    ds = get_dataset(dataset_id)
    if not adapter or not ds:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_id}' not found.")

    available = adapter.is_available()
    return {
        "datasetId": dataset_id,
        "datasetName": ds.datasetName,
        "equipmentType": ds.equipmentType.value,
        "available": available,
        "downloadStatus": "READY" if available else "NOT_DOWNLOADED",
        "sourceUrl": ds.sourceUrl,
        "license": ds.license,
        "machineCount": adapter.get_machine_count() if available else 0,
        "message": (
            "Dataset is loaded and ready."
            if available
            else f"Dataset not yet downloaded. Download from: {ds.sourceUrl}"
        ),
    }
