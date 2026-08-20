"""
backend/app/schemas/model_version.py

Pydantic schemas for Model Version Registry API.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class ModelVersionResponse(BaseModel):
    id: int
    machine_id: int
    version: str
    model_type: str
    model_artifact_path: Optional[str] = None
    training_dataset_id: Optional[str] = None
    training_date: Optional[datetime] = None
    training_sample_count: Optional[int] = None
    feature_count: Optional[int] = None
    validation_metrics: Optional[Dict[str, Any]] = None
    status: str
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    deployed_at: Optional[datetime] = None
    retired_at: Optional[datetime] = None
    rollback_reason: Optional[str] = None
    parent_version_id: Optional[int] = None
    deployment_prediction_count: Optional[int] = None
    post_deploy_false_alarm_rate: Optional[float] = None
    post_deploy_accuracy_estimate: Optional[float] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class RegisterCandidateRequest(BaseModel):
    machine_id: int = Field(description="Target machine ID")
    version: str = Field(description="Version string e.g. v2.0.0", example="v2.0.0")
    model_type: str = Field(default="LightGBM+IsolationForest")
    model_artifact_path: Optional[str] = Field(default=None, description="Absolute path to serialized model artefacts")
    training_dataset_id: Optional[str] = Field(default=None, description="Dataset filename or identifier used for training")
    training_date: Optional[datetime] = None
    training_sample_count: Optional[int] = None
    feature_count: Optional[int] = None
    validation_metrics: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Validation results: rul_rmse, rul_mae, anomaly_f1, anomaly_precision, anomaly_recall"
    )
    parent_version_id: Optional[int] = Field(default=None, description="ID of the version this was trained from")


class ApproveVersionRequest(BaseModel):
    approved_by: str = Field(description="Administrator username approving this version")
    notes: Optional[str] = Field(default=None, description="Optional approval notes")


class RollbackRequest(BaseModel):
    rollback_reason: str = Field(description="Mandatory reason for rolling back to previous version")
    rolled_back_by: str = Field(description="Administrator username initiating the rollback")
