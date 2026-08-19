"""
backend/app/schemas/diagnostics.py

Pydantic schemas for AI Root Cause Analysis (RCA) and diagnostics.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class DiagnosticExplainRequest(BaseModel):
    machine_id: int = Field(description="Engine unit ID")
    cycle: Optional[int] = Field(default=None, description="Optional target cycle; defaults to latest available")


class DiagnosticReportResponse(BaseModel):
    machine_id: int
    cycle: int
    summary: str
    risk_explanation: str
    evidence: List[str]
    recommended_action: str
    confidence: str
    limitations: str
    source: str  # "gemini" or "fallback"
    is_fallback: bool
    model_used: str
    structured_evidence_snapshot: Optional[Dict[str, Any]] = None
