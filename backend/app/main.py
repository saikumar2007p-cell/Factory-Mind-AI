"""
backend/app/main.py

FastAPI Application Entrypoint for FactoryMind AI.

Industrial Prognostics, Sensor Telemetry, AI Root-Cause Diagnostics, and Real-Time C-MAPSS Simulation.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any
import logging
import sys
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings
from backend.app.database import init_db, close_db
from backend.app.services.simulation import get_simulation_engine
from backend.app.websockets.stream import ws_manager
from backend.app.routers import (
    machines,
    telemetry,
    predictions,
    simulation,
    alerts,
    diagnostics,
    sources,
    work_orders,
    fleet,
    continuous_learning,
    auth,
    model_versions,
    drift,
    outcomes,
    users,
    machine_registrations,
    notifications
)
from backend.app.routers import firebase_auth
from backend.app.routers import datasets

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("factorymind.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown event handler."""
    logger.info("Starting FactoryMind AI Backend...")
    logger.info(f"Active Database Backend: {'Local SQLite Fallback' if settings.is_sqlite_fallback else 'PostgreSQL / Supabase'}")
    logger.info(f"Firebase Auth Mode: {settings.FIREBASE_AUTH_MODE}")

    # Initialize Firebase Admin SDK
    try:
        from backend.app.firebase_admin_init import init_firebase_admin, is_firebase_ready
        firebase_app = init_firebase_admin()
        if firebase_app:
            logger.info("Firebase Admin SDK initialized successfully.")
        else:
            logger.warning("Firebase Admin SDK not initialized — check FIREBASE_SERVICE_ACCOUNT_PATH.")
    except Exception as e:
        logger.warning(f"Firebase Admin SDK initialization skipped: {e}")

    # Initialize database tables (SQL — kept for ML pipeline compatibility)
    try:
        await init_db()
        logger.info("Database initialized successfully.")

        # Seed initial default admin and operator users if empty
        from backend.app.database import AsyncSessionLocal
        from backend.app.services.user_service import UserService
        from backend.app.services.telemetry_state import TelemetryStateService

        async with AsyncSessionLocal() as session:
            user_svc = UserService(session)
            admin_count = await user_svc.get_active_admin_count()
            if admin_count == 0:
                await user_svc.create_user(
                    username="admin",
                    display_name="System Administrator (Alice)",
                    role="ADMIN",
                    email="admin@factorymind.ai",
                    created_by="SYSTEM_INIT",
                    notes="Default platform administrator"
                )
                await user_svc.create_user(
                    username="operator",
                    display_name="Operations Engineer (Bob)",
                    role="OPERATOR",
                    email="operator@factorymind.ai",
                    created_by="SYSTEM_INIT",
                    notes="Default platform operations engineer"
                )
                await session.commit()
                logger.info("Seeded default named Administrator and Operator users.")

            # Refresh telemetry freshness states on startup
            tel_svc = TelemetryStateService(session)
            state_counts = await tel_svc.refresh_all_machine_states()
            await session.commit()
            logger.info(f"Startup machine telemetry state refresh completed: {state_counts}")
    except Exception as e:
        logger.error(f"Database initialization error: {e}", exc_info=True)

    # Initialize simulation engine
    sim_engine = get_simulation_engine()
    logger.info(f"Simulation Engine ready with Unit #{sim_engine.unit_number} ({sim_engine.max_cycle} cycles).")

    yield

    # Shutdown
    logger.info("Shutting down FactoryMind AI Backend...")
    await sim_engine.stop()
    await close_db()
    logger.info("Database connections closed.")


app = FastAPI(
    title="FactoryMind AI API",
    version="1.0.0",
    description="Enterprise Industrial Predictive Maintenance & Real-Time Turbofan Prognostics Platform",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Safe unhandled exception handler that prevents stack trace and secret leakage."""
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "An internal server error occurred. Operational telemetry and records remain safe.",
            "error_type": "INTERNAL_SERVER_ERROR"
        }
    )


# Register REST Routers under /api/v1
api_v1_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_v1_prefix)
app.include_router(firebase_auth.router, prefix=api_v1_prefix)
app.include_router(users.router, prefix=api_v1_prefix)
app.include_router(machines.router, prefix=api_v1_prefix)
app.include_router(machine_registrations.router, prefix=api_v1_prefix)
app.include_router(telemetry.router, prefix=api_v1_prefix)
app.include_router(predictions.router, prefix=api_v1_prefix)
app.include_router(model_versions.router, prefix=api_v1_prefix)
app.include_router(simulation.router, prefix=api_v1_prefix)
app.include_router(alerts.router, prefix=api_v1_prefix)
app.include_router(drift.router, prefix=api_v1_prefix)
app.include_router(diagnostics.router, prefix=api_v1_prefix)
app.include_router(sources.router, prefix=api_v1_prefix)
app.include_router(work_orders.router, prefix=api_v1_prefix)
app.include_router(outcomes.router, prefix=api_v1_prefix)
app.include_router(fleet.router, prefix=api_v1_prefix)
app.include_router(continuous_learning.router, prefix=api_v1_prefix)
app.include_router(datasets.router, prefix=api_v1_prefix)
app.include_router(notifications.router, prefix=api_v1_prefix)



@app.get("/health", tags=["Health"])
@app.get(f"{api_v1_prefix}/health", tags=["Health"])
async def healthcheck() -> Dict[str, Any]:
    """Health check endpoint confirming API and backend status."""
    from backend.app.firebase_admin_init import is_firebase_ready
    return {
        "status": "HEALTHY",
        "service": "FactoryMind AI Backend",
        "version": "1.0.0",
        "database": "SQLite Fallback" if settings.is_sqlite_fallback else "PostgreSQL/Supabase",
        "firebase_admin": "READY" if is_firebase_ready() else "NOT_CONFIGURED",
        "firebase_auth_mode": settings.FIREBASE_AUTH_MODE,
        "ml_inference_ready": True,
        "dataset": "NASA C-MAPSS FD001"
    }


@app.websocket(f"{api_v1_prefix}/stream")
async def websocket_telemetry_stream(websocket: WebSocket):
    """
    Real-Time WebSocket Stream broadcasting cycle observations, RUL forecasts,
    anomaly scores, and degradation alarms as the simulation progresses.
    """
    await ws_manager.connect(websocket)
    sim = get_simulation_engine()

    # Send initial status frame on connect
    try:
        initial_frame = {
            "type": "INITIAL_STATE",
            "unit_number": sim.unit_number,
            "current_cycle": sim.current_cycle,
            "max_cycle": sim.max_cycle,
            "is_running": sim.is_running,
            "is_paused": sim.is_paused,
            "latest_prediction": sim._last_result,
            "latest_telemetry": sim._last_telemetry,
        }
        await websocket.send_json(initial_frame)

        # Keep connection open and handle client messages
        while True:
            data = await websocket.receive_text()
            # Respond to client ping
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception as e:
        logger.warning(f"WebSocket client stream error: {e}")
        ws_manager.disconnect(websocket)
