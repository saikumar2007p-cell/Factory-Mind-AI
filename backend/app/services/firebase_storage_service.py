"""
backend/app/services/firebase_storage_service.py

Firebase Cloud Storage service for FactoryMind AI.
Handles CSV/XLSX datasets, PDFs, maintenance documents, and generated reports.

File organization:
    organizations/{organizationId}/
        datasets/
        documents/
        maintenance/
        reports/

Binary files go to Firebase Storage. Metadata goes to Firestore via firestore_service.
"""

import os
import uuid
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("factorymind.firebase_storage")


def _get_bucket(bucket_name: Optional[str] = None):
    """Lazy-load Firebase Storage bucket."""
    from backend.app.firebase_admin_init import get_storage_bucket
    return get_storage_bucket(bucket_name)


def _build_storage_path(organization_id: str, category: str, filename: str) -> str:
    """
    Build organization-scoped storage path.
    category: datasets | documents | maintenance | reports
    """
    safe_filename = filename.replace(" ", "_").replace("/", "_").replace("\\", "_")
    return f"organizations/{organization_id}/{category}/{safe_filename}"


def upload_file(
    local_path: str,
    organization_id: str,
    category: str,
    filename: Optional[str] = None,
    content_type: Optional[str] = None,
    metadata: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Upload a local file to Firebase Storage.

    Args:
        local_path: Absolute path to the local file
        organization_id: Tenant isolation key
        category: One of: datasets, documents, maintenance, reports
        filename: Override filename (defaults to basename of local_path)
        content_type: MIME type
        metadata: Custom metadata dict

    Returns:
        Dict with storagePath, downloadUrl, size, uploadedAt — or None on failure
    """
    bucket = _get_bucket()
    if not bucket:
        logger.warning("[Firebase Storage] Bucket not available — skipping upload")
        return None

    if not os.path.isfile(local_path):
        logger.error(f"[Firebase Storage] File not found: {local_path}")
        return None

    try:
        actual_filename = filename or os.path.basename(local_path)
        storage_path = _build_storage_path(organization_id, category, actual_filename)

        blob = bucket.blob(storage_path)

        if metadata:
            blob.metadata = metadata

        blob.upload_from_filename(local_path, content_type=content_type)

        # Make publicly readable with signed URL (1 hour expiry)
        download_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
        )

        file_size = os.path.getsize(local_path)

        result = {
            "storagePath": storage_path,
            "downloadUrl": download_url,
            "size": file_size,
            "contentType": content_type or blob.content_type,
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"[Firebase Storage] Uploaded: {storage_path} ({file_size} bytes)")
        return result

    except Exception as e:
        logger.error(f"[Firebase Storage] Upload failed: {e}")
        return None


def upload_file_bytes(
    file_bytes: bytes,
    organization_id: str,
    category: str,
    filename: str,
    content_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Upload raw bytes to Firebase Storage (for in-memory files like SpooledTemporaryFile).
    """
    bucket = _get_bucket()
    if not bucket:
        logger.warning("[Firebase Storage] Bucket not available — skipping upload")
        return None

    try:
        storage_path = _build_storage_path(organization_id, category, filename)
        blob = bucket.blob(storage_path)
        blob.upload_from_string(file_bytes, content_type=content_type)

        download_url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(hours=1),
            method="GET",
        )

        result = {
            "storagePath": storage_path,
            "downloadUrl": download_url,
            "size": len(file_bytes),
            "contentType": content_type or blob.content_type,
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(f"[Firebase Storage] Uploaded bytes: {storage_path} ({len(file_bytes)} bytes)")
        return result

    except Exception as e:
        logger.error(f"[Firebase Storage] Byte upload failed: {e}")
        return None


def get_signed_url(storage_path: str, expiry_minutes: int = 60) -> Optional[str]:
    """Get a time-limited signed download URL for an existing file."""
    bucket = _get_bucket()
    if not bucket:
        return None
    try:
        blob = bucket.blob(storage_path)
        if not blob.exists():
            logger.warning(f"[Firebase Storage] Blob not found: {storage_path}")
            return None
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expiry_minutes),
            method="GET",
        )
    except Exception as e:
        logger.error(f"[Firebase Storage] Signed URL generation failed: {e}")
        return None


def delete_file(storage_path: str) -> bool:
    """Delete a file from Firebase Storage."""
    bucket = _get_bucket()
    if not bucket:
        return False
    try:
        blob = bucket.blob(storage_path)
        blob.delete()
        logger.info(f"[Firebase Storage] Deleted: {storage_path}")
        return True
    except Exception as e:
        logger.error(f"[Firebase Storage] Delete failed: {e}")
        return False


def list_files(organization_id: str, category: str) -> list:
    """List all files in an organization's category folder."""
    bucket = _get_bucket()
    if not bucket:
        return []
    try:
        prefix = f"organizations/{organization_id}/{category}/"
        blobs = bucket.list_blobs(prefix=prefix)
        return [
            {
                "name": blob.name,
                "size": blob.size,
                "contentType": blob.content_type,
                "updatedAt": blob.updated.isoformat() if blob.updated else None,
            }
            for blob in blobs
        ]
    except Exception as e:
        logger.error(f"[Firebase Storage] List files failed: {e}")
        return []
