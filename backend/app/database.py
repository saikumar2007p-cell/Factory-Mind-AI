"""
backend/app/database.py

Asynchronous SQLAlchemy Database Engine and Session Management.
Supports both PostgreSQL/Supabase and zero-config local SQLite fallback with identical ORM models.
"""

from typing import AsyncGenerator, Optional
import os
import sys
from pathlib import Path
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.orm import declarative_base

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.app.config import settings

Base = declarative_base()

_engine: Optional[AsyncEngine] = None
_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


def get_engine(db_url: Optional[str] = None) -> AsyncEngine:
    """Returns or creates the global AsyncEngine instance."""
    global _engine, _session_maker
    target_url = db_url or settings.effective_database_url

    if _engine is None or db_url is not None:
        # SQLite needs specific connect_args for multithreading
        connect_args = {}
        if "sqlite" in target_url.lower():
            connect_args = {"check_same_thread": False}

        _engine = create_async_engine(
            target_url,
            echo=False,
            future=True,
            connect_args=connect_args
        )
        _session_maker = async_sessionmaker(
            bind=_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False
        )

    return _engine


def get_session_maker(db_url: Optional[str] = None) -> async_sessionmaker[AsyncSession]:
    """Returns the configured session maker."""
    get_engine(db_url)
    assert _session_maker is not None
    return _session_maker


async def init_db(db_url: Optional[str] = None):
    """Initializes all database tables asynchronously."""
    engine = get_engine(db_url)
    
    # Import all models to register with Base.metadata
    from backend.app.models.machine import Machine
    from backend.app.models.telemetry import Telemetry
    from backend.app.models.prediction import Prediction
    from backend.app.models.anomaly import Anomaly
    from backend.app.models.alert import Alert
    from backend.app.models.recommendation import Recommendation
    from backend.app.models.work_order import WorkOrder, WorkOrderAuditLog

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    db_type = "Local SQLite Fallback" if ("sqlite" in (db_url or settings.effective_database_url).lower()) else "PostgreSQL / Supabase"
    print(f"[DATABASE] Initialized tables successfully on: {db_type}")


async def close_db():
    """Closes database connection pools cleanly."""
    global _engine, _session_maker
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_maker = None


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator for FastAPI and service operations."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
