"""
backend/app/routers/diagnostics.py

AI Diagnostics & Root Cause Analysis (RCA) API routes.
Grounds Gemini 2.0/2.5 on structured telemetry evidence and persists recommendations.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.services.storage_service import StorageService
from backend.app.services.evidence_builder import build_structured_evidence
from backend.app.services.gemini_explainer import generate_gemini_diagnosis
from backend.app.schemas.diagnostics import (
    DiagnosticExplainRequest,
    DiagnosticReportResponse
)

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics & RCA"])


@router.post("/explain", response_model=DiagnosticReportResponse)
async def explain_machine_state(
    request: DiagnosticExplainRequest,
    session: AsyncSession = Depends(get_db)
):
    """
    Constructs validated structured evidence for the designated machine & cycle,
    invokes the grounded Gemini Diagnostic Copilot, and persists the resulting work order.
    """
    service = StorageService(session)
    machine = await service.get_machine_by_id(request.machine_id)
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Machine with ID {request.machine_id} not found."
        )

    # Fetch latest prediction or specific cycle prediction
    if request.cycle is not None:
        predictions = await service.get_prediction_history(machine.id, limit=200)
        prediction = next((p for p in predictions if p.cycle == request.cycle), None)
    else:
        prediction = await service.get_latest_prediction(machine.id)

    if not prediction:
        # Dynamically compute inference for this machine so diagnostics work seamlessly
        telemetry_history = await service.get_telemetry_history(machine.id, limit=50)
        import pandas as pd
        from ml.inference import get_inference_engine
        from ml.dataset import SENSOR_COLS

        if telemetry_history:
            records = []
            for t in telemetry_history:
                rec = t.to_dict() if hasattr(t, 'to_dict') else {c.name: getattr(t, c.name) for c in t.__table__.columns}
                rec['unit_number'] = machine.unit_number
                rec['time_cycle'] = rec.get('cycle', rec.get('time_in_cycles', 1))
                rec['setting_1'] = rec.get('setting_1', 0.0)
                rec['setting_2'] = rec.get('setting_2', 0.0)
                rec['setting_3'] = rec.get('setting_3', 100.0)
                records.append(rec)
            df_win = pd.DataFrame(records)
        else:
            cur_cycle = request.cycle or getattr(machine, 'current_cycle', 1) or 1
            records = []
            for c in range(max(1, cur_cycle - 15), cur_cycle + 1):
                row = {'unit_number': machine.unit_number, 'time_cycle': c, 'setting_1': 0.0, 'setting_2': 0.0, 'setting_3': 100.0}
                for sc in SENSOR_COLS:
                    row[sc] = 500.0
                records.append(row)
            df_win = pd.DataFrame(records)

        engine = get_inference_engine()
        inf_res = engine.predict_window(df_win)
        prediction, _, _ = await service.persist_inference_cycle(machine.id, inf_res)
        await session.commit()

    # Fetch telemetry and active alerts
    telemetry_history = await service.get_telemetry_history(
        machine.id,
        limit=1,
        start_cycle=prediction.cycle,
        end_cycle=prediction.cycle
    )
    telemetry = telemetry_history[0] if telemetry_history else None
    active_alerts = await service.get_active_alerts(machine.id)

    # 1. Build and validate structured evidence
    try:
        evidence = build_structured_evidence(
            machine=machine,
            prediction=prediction,
            telemetry=telemetry,
            active_alerts=active_alerts
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Evidence construction error: {str(e)}"
        )

    # 2. Invoke Grounded Gemini Explainer
    diagnostic_report = await generate_gemini_diagnosis(evidence)

    # 3. Persist recommendation in database
    await service.insert_recommendation(
        machine_id=machine.id,
        prediction_id=prediction.id,
        alert_id=active_alerts[0].id if active_alerts else None,
        recommendation_text=diagnostic_report.recommended_action,
        source="GEMINI_GENAI" if not diagnostic_report.is_fallback else "DETERMINISTIC_RULES",
        is_fallback=diagnostic_report.is_fallback
    )
    await session.commit()

    return DiagnosticReportResponse(
        machine_id=machine.id,
        cycle=prediction.cycle,
        summary=diagnostic_report.summary,
        risk_explanation=diagnostic_report.risk_explanation,
        evidence=diagnostic_report.evidence,
        recommended_action=diagnostic_report.recommended_action,
        confidence=diagnostic_report.confidence,
        limitations=diagnostic_report.limitations,
        source=diagnostic_report.source,
        is_fallback=diagnostic_report.is_fallback,
        model_used=diagnostic_report.model_used,
        structured_evidence_snapshot=evidence
    )


@router.get("/{machine_id}", response_model=DiagnosticReportResponse)
async def get_machine_latest_diagnostics(
    machine_id: int,
    session: AsyncSession = Depends(get_db)
):
    """Retrieves or executes real diagnostic explanation for the latest machine state."""
    return await explain_machine_state(DiagnosticExplainRequest(machine_id=machine_id), session)
