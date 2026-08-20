"""
backend/app/config.py

Application settings and environment configuration management using Pydantic Settings.
"""

from typing import List, Optional
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"


class Settings(BaseSettings):
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Database
    DATABASE_URL: Optional[str] = None
    FALLBACK_SQLITE_URL: str = f"sqlite+aiosqlite:///{ROOT_DIR / 'factorymind.db'}"

    # Supabase (LEGACY — kept temporarily for SQL-based ML pipeline compatibility)
    SUPABASE_URL: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # Firebase Admin SDK (Backend only — never expose to frontend)
    FIREBASE_SERVICE_ACCOUNT_PATH: Optional[str] = None
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_AUTH_MODE: str = "DEVELOPMENT"  # FIREBASE or DEVELOPMENT

    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_API_MODEL: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Simulation defaults
    SIMULATION_TICK_RATE_MS: int = 1000
    DEFAULT_UNIT_ID: int = 1

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def effective_gemini_model(self) -> str:
        """Returns configured Gemini model identifier."""
        return self.GEMINI_API_MODEL or self.GEMINI_MODEL or "gemini-2.0-flash"

    @property
    def effective_database_url(self) -> str:
        """Returns configured DATABASE_URL or the verified local SQLite fallback."""
        url = self.DATABASE_URL
        if url and url.strip():
            url_str = url.strip()
            if url_str.startswith("postgresql://") or url_str.startswith("postgres://") or url_str.startswith("postgresql+asyncpg://"):
                try:
                    import asyncpg
                    return url_str.replace("postgresql://", "postgresql+asyncpg://").replace("postgres://", "postgresql+asyncpg://")
                except ImportError:
                    return self.FALLBACK_SQLITE_URL
            return url_str
        return self.FALLBACK_SQLITE_URL

    @property
    def is_sqlite_fallback(self) -> bool:
        """Checks whether the active database connection is SQLite fallback."""
        return "sqlite" in self.effective_database_url.lower()

    @property
    def is_firebase_auth_enabled(self) -> bool:
        """Returns True if Firebase authentication mode is enabled for production."""
        return self.FIREBASE_AUTH_MODE.upper() == "FIREBASE"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
