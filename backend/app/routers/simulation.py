"""
backend/app/routers/simulation.py

Deterministic C-MAPSS Replay Simulation Control API routes.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from backend.app.schemas.simulation import (
    SimulationConfig,
    SimulationStatusResponse,
    SimulationStepResponse
)
from backend.app.services.simulation import get_simulation_engine
from backend.app.security import AuthUser, require_role

router = APIRouter(prefix="/simulation", tags=["Simulation Controls"])

verify_sim_access = require_role(["admin", "operator", "engineer"])


@router.post("/start", response_model=SimulationStatusResponse)
async def start_simulation(
    config: SimulationConfig = SimulationConfig(),
    user: AuthUser = Depends(verify_sim_access)
):
    """Starts or configures the real-time C-MAPSS trajectory replay engine."""
    sim = get_simulation_engine()
    try:
        await sim.start(
            unit_number=config.unit_number,
            start_cycle=config.start_cycle,
            speed_multiplier=config.speed_multiplier
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start simulation: {str(e)}"
        )
    return SimulationStatusResponse(**sim.get_status())


@router.post("/pause", response_model=SimulationStatusResponse)
async def pause_simulation(user: AuthUser = Depends(verify_sim_access)):
    """Pauses active replay playback."""
    sim = get_simulation_engine()
    sim.pause()
    return SimulationStatusResponse(**sim.get_status())


@router.post("/resume", response_model=SimulationStatusResponse)
async def resume_simulation(user: AuthUser = Depends(verify_sim_access)):
    """Resumes paused replay playback."""
    sim = get_simulation_engine()
    sim.resume()
    return SimulationStatusResponse(**sim.get_status())


@router.post("/stop", response_model=SimulationStatusResponse)
async def stop_simulation(user: AuthUser = Depends(verify_sim_access)):
    """Stops replay and terminates the background playback loop."""
    sim = get_simulation_engine()
    await sim.stop()
    return SimulationStatusResponse(**sim.get_status())


@router.post("/reset", response_model=SimulationStatusResponse)
async def reset_simulation(
    config: SimulationConfig = SimulationConfig(),
    user: AuthUser = Depends(verify_sim_access)
):
    """Resets the simulation buffer back to cycle 1 for the designated unit."""
    sim = get_simulation_engine()
    await sim.reset(unit_number=config.unit_number, start_cycle=config.start_cycle)
    return SimulationStatusResponse(**sim.get_status())


@router.post("/step", response_model=SimulationStepResponse)
async def step_simulation(user: AuthUser = Depends(verify_sim_access)):
    """Manually advances the replay by exactly ONE authentic C-MAPSS cycle."""
    sim = get_simulation_engine()
    is_completed, telemetry, prediction, alert = await sim.step()

    return SimulationStepResponse(
        unit_number=sim.unit_number,
        cycle=sim.current_cycle,
        is_completed=is_completed,
        telemetry=telemetry,
        prediction=prediction,
        alert_triggered=alert is not None,
        alert=alert
    )


@router.get("/status", response_model=SimulationStatusResponse)
async def get_simulation_status():
    """Returns the current state, unit number, speed, and latest prognostic metrics."""
    sim = get_simulation_engine()
    return SimulationStatusResponse(**sim.get_status())


@router.get("/current-cycle")
async def get_current_cycle():
    """Short-polling endpoint returning current cycle and latest telemetry/prediction frame."""
    sim = get_simulation_engine()
    return {
        "unit_number": sim.unit_number,
        "current_cycle": sim.current_cycle,
        "max_cycle": sim.max_cycle,
        "is_running": sim.is_running,
        "is_paused": sim.is_paused,
        "latest_telemetry": sim._last_telemetry,
        "latest_prediction": sim._last_result,
    }
