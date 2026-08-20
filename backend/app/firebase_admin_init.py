"""
backend/app/firebase_admin_init.py

Singleton Firebase Admin SDK initialization for FactoryMind AI.

Security rules:
- Service account JSON must NEVER be committed to Git (.gitignore enforced).
- FIREBASE_SERVICE_ACCOUNT_PATH env var points to the local file path.
- In CI/CD, FIREBASE_SERVICE_ACCOUNT_JSON env var can hold the JSON string directly.
- If neither is available, Admin SDK is initialized without credentials (limited functionality).
"""

import os
import json
import logging
from typing import Optional, Any

logger = logging.getLogger("factorymind.firebase")

try:
    # pyrefly: ignore [missing-import]
    import firebase_admin
    # pyrefly: ignore [missing-import]
    from firebase_admin import credentials, auth, firestore, storage as fb_storage
    FIREBASE_AVAILABLE = True
except ImportError:
    firebase_admin = None
    credentials = None
    auth = None
    firestore = None
    fb_storage = None
    FIREBASE_AVAILABLE = False
    logger.warning("[Firebase] firebase-admin package is not installed. Running in mock/fallback mode.")

_firebase_app: Optional[Any] = None


def get_firebase_app() -> Optional[Any]:
    """Returns the initialized Firebase Admin App singleton, or None if unconfigured."""
    return _firebase_app


def init_firebase_admin() -> Optional[Any]:
    """
    Initializes Firebase Admin SDK once.
    
    Resolution order for credentials:
    1. FIREBASE_SERVICE_ACCOUNT_JSON env var (JSON string — safe for CI/CD secrets)
    2. FIREBASE_SERVICE_ACCOUNT_PATH env var (path to service account JSON file)
    3. Application Default Credentials (GCP-hosted environments)
    
    Returns the initialized app or None if no credentials are available.
    """
    global _firebase_app

    if not FIREBASE_AVAILABLE:
        return None

    if _firebase_app is not None:
        return _firebase_app

    project_id = os.getenv("FIREBASE_PROJECT_ID")
    cred = None

    # --- Priority 1: Inline JSON (CI/CD secure env var) ---
    sa_json_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if sa_json_str:
        try:
            sa_dict = json.loads(sa_json_str)
            cred = credentials.Certificate(sa_dict)
            logger.info("[Firebase] Initialized with inline FIREBASE_SERVICE_ACCOUNT_JSON credential.")
        except Exception as e:
            logger.error(f"[Firebase] Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {e}")

    # --- Priority 2: File path ---
    if cred is None:
        sa_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "backend/firebase_service_account.json")
        if os.path.isfile(sa_path):
            try:
                cred = credentials.Certificate(sa_path)
                logger.info(f"[Firebase] Initialized with service account file: {sa_path}")
            except Exception as e:
                logger.error(f"[Firebase] Failed to load service account from {sa_path}: {e}")
        else:
            logger.warning(
                f"[Firebase] Service account file not found at '{sa_path}'. "
                "Firebase Admin SDK will use Application Default Credentials if available."
            )

    # --- Priority 3: Application Default Credentials (GCP-hosted) ---
    try:
        storage_bucket = None
        if project_id:
            storage_bucket = f"{project_id}.appspot.com"

        options = {}
        if project_id:
            options["projectId"] = project_id
        if storage_bucket:
            options["storageBucket"] = storage_bucket

        if cred:
            _firebase_app = firebase_admin.initialize_app(cred, options if options else None)
        else:
            _firebase_app = firebase_admin.initialize_app(options=options if options else None)
            logger.info("[Firebase] Initialized with Application Default Credentials.")

        logger.info(f"[Firebase] Admin SDK ready. Project: {project_id or 'unset'}")
        return _firebase_app

    except Exception as e:
        logger.error(f"[Firebase] Admin SDK initialization failed: {e}")
        _firebase_app = None
        return None


def is_firebase_ready() -> bool:
    """Returns True if Firebase Admin SDK is initialized and available."""
    return _firebase_app is not None and FIREBASE_AVAILABLE


def get_auth_client():
    """Returns Firebase Auth client (requires initialized app)."""
    return auth if FIREBASE_AVAILABLE else None


def get_firestore_client():
    """Returns Firestore client (requires initialized app)."""
    if not is_firebase_ready():
        return None
    return firestore.client() if firestore else None


def get_storage_bucket(bucket_name: Optional[str] = None):
    """Returns Firebase Storage bucket handle."""
    if not is_firebase_ready():
        return None
    try:
        return fb_storage.bucket(bucket_name) if fb_storage else None
    except Exception as e:
        logger.error(f"[Firebase Storage] Could not get bucket: {e}")
        return None
