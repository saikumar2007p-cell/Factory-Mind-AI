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


def AsyncSessionLocal(db_url: Optional[str] = None) -> AsyncSession:
    """Convenience factory returning a new AsyncSession."""
    maker = get_session_maker(db_url)
    return maker()


async def init_db(db_url: Optional[str] = None):
    """Initializes all database tables and applies safe incremental schema migrations."""
    engine = get_engine(db_url)
    
    # Import all models to register with Base.metadata
    import backend.app.models

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Safe column migrations for existing databases
        migration_statements = [
            "ALTER TABLE machines ADD COLUMN telemetry_state VARCHAR(20) DEFAULT 'NO_DATA'",
            "ALTER TABLE machines ADD COLUMN last_telemetry_at DATETIME",
            "ALTER TABLE machines ADD COLUMN telemetry_freshness_seconds INTEGER DEFAULT 300",
            "ALTER TABLE predictions ADD COLUMN confidence_level VARCHAR(25)",
            "ALTER TABLE predictions ADD COLUMN confidence_score FLOAT",
            "ALTER TABLE predictions ADD COLUMN out_of_distribution_sensors JSON",
            "ALTER TABLE predictions ADD COLUMN confidence_reason VARCHAR(500)",
            "ALTER TABLE telemetry ADD COLUMN data_source_type VARCHAR(20) DEFAULT 'CMAPSS'",
            "ALTER TABLE telemetry ADD COLUMN sensor_data JSON",
        ]
        from sqlalchemy import text
        for stmt in migration_statements:
            try:
                await conn.execute(text(stmt))
            except Exception:
                # Column already exists
                pass
        
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
