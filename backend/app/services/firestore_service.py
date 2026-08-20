"""
backend/app/services/firestore_service.py

Centralized Firestore service layer for FactoryMind AI.
All Firestore read/write operations go through this module — no raw Firestore calls in routers.

Collections:
  organizations, factories, productionAreas, machines, subsystems, sensors,
  telemetry, users, predictions, diagnostics, anomalies, maintenancePlans,
  workOrders, documents, auditLogs
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger("factorymind.firestore")

_db = None


def _get_db():
    """Lazy-load Firestore client."""
    global _db
    if _db is None:
        from backend.app.firebase_admin_init import get_firestore_client
        _db = get_firestore_client()
    return _db


# ============================================================================
# USERS
# ============================================================================

def upsert_user(uid: str, data: Dict[str, Any]) -> bool:
    """Create or update a user document in users/{uid}."""
    db = _get_db()
    if not db:
        logger.warning("[Firestore] Not available — skipping upsert_user")
        return False
    try:
        doc_ref = db.collection("users").document(uid)
        doc_data = {
            "uid": uid,
            "email": data.get("email", ""),
            "name": data.get("name", data.get("display_name", "")),
            "role": data.get("role", "VIEWER"),
            "organizationId": data.get("organizationId", data.get("organization_id", "")),
            "active": data.get("active", True),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        }
        existing = doc_ref.get()
        if existing.exists:
            doc_ref.update(doc_data)
        else:
            doc_data["createdAt"] = datetime.now(timezone.utc).isoformat()
            doc_ref.set(doc_data)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_user failed: {e}")
        return False


def get_user(uid: str) -> Optional[Dict[str, Any]]:
    """Get user profile from users/{uid}."""
    db = _get_db()
    if not db:
        return None
    try:
        doc = db.collection("users").document(uid).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"[Firestore] get_user failed: {e}")
        return None


def get_users_by_org(organization_id: str) -> List[Dict[str, Any]]:
    """List all users for an organization."""
    db = _get_db()
    if not db:
        return []
    try:
        docs = db.collection("users").where("organizationId", "==", organization_id).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"[Firestore] get_users_by_org failed: {e}")
        return []


# ============================================================================
# ORGANIZATIONS
# ============================================================================

def upsert_organization(org_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_ref = db.collection("organizations").document(org_id)
        doc_data = {
            "organizationId": org_id,
            "name": data.get("name", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items() if k not in ("name",)},
        }
        existing = doc_ref.get()
        if not existing.exists:
            doc_data["createdAt"] = datetime.now(timezone.utc).isoformat()
        doc_ref.set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_organization failed: {e}")
        return False


def get_organization(org_id: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return None
    try:
        doc = db.collection("organizations").document(org_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"[Firestore] get_organization failed: {e}")
        return None


# ============================================================================
# FACTORIES
# ============================================================================

def upsert_factory(factory_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "factoryId": factory_id,
            "organizationId": data.get("organizationId", ""),
            "name": data.get("name", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items() if k not in ("name", "organizationId")},
        }
        db.collection("factories").document(factory_id).set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_factory failed: {e}")
        return False


def get_factories_by_org(organization_id: str) -> List[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return []
    try:
        docs = db.collection("factories").where("organizationId", "==", organization_id).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"[Firestore] get_factories_by_org failed: {e}")
        return []


# ============================================================================
# MACHINES
# ============================================================================

def upsert_machine(machine_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "machineId": machine_id,
            "organizationId": data.get("organizationId", ""),
            "factoryId": data.get("factoryId", ""),
            "areaId": data.get("areaId", ""),
            "name": data.get("name", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items() if k not in ("name", "organizationId", "factoryId", "areaId")},
        }
        db.collection("machines").document(machine_id).set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_machine failed: {e}")
        return False


def get_machines_by_org(organization_id: str) -> List[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return []
    try:
        docs = db.collection("machines").where("organizationId", "==", organization_id).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"[Firestore] get_machines_by_org failed: {e}")
        return []


def get_machine(machine_id: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return None
    try:
        doc = db.collection("machines").document(machine_id).get()
        return doc.to_dict() if doc.exists else None
    except Exception as e:
        logger.error(f"[Firestore] get_machine failed: {e}")
        return None


# ============================================================================
# SUBSYSTEMS
# ============================================================================

def upsert_subsystem(subsystem_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "subsystemId": subsystem_id,
            "machineId": data.get("machineId", ""),
            "organizationId": data.get("organizationId", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items()},
        }
        db.collection("subsystems").document(subsystem_id).set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_subsystem failed: {e}")
        return False


# ============================================================================
# SENSORS
# ============================================================================

def upsert_sensor(sensor_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "sensorId": sensor_id,
            "subsystemId": data.get("subsystemId", ""),
            "machineId": data.get("machineId", ""),
            "organizationId": data.get("organizationId", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items()},
        }
        db.collection("sensors").document(sensor_id).set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_sensor failed: {e}")
        return False


# ============================================================================
# TELEMETRY
# ============================================================================

def write_telemetry(data: Dict[str, Any]) -> bool:
    """Write a telemetry record. Auto-generates document ID."""
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "machineId": data.get("machineId", ""),
            "organizationId": data.get("organizationId", ""),
            "sensorId": data.get("sensorId", ""),
            "cycle": data.get("cycle"),
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "dataSource": data.get("dataSource", "NASA_CMAPSS_FD001"),
            "dataMode": data.get("dataMode", "DEMO"),
            **{k: v for k, v in data.items()
               if k not in ("machineId", "organizationId", "sensorId", "cycle", "timestamp", "dataSource", "dataMode")},
        }
        db.collection("telemetry").add(doc_data)
        return True
    except Exception as e:
        logger.error(f"[Firestore] write_telemetry failed: {e}")
        return False


def get_telemetry_by_machine(machine_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return []
    try:
        docs = (db.collection("telemetry")
                .where("machineId", "==", machine_id)
                .order_by("cycle", direction="DESCENDING")
                .limit(limit)
                .stream())
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"[Firestore] get_telemetry_by_machine failed: {e}")
        return []


# ============================================================================
# PREDICTIONS
# ============================================================================

def write_prediction(data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "machineId": data.get("machineId", ""),
            "organizationId": data.get("organizationId", ""),
            "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            **{k: v for k, v in data.items()},
        }
        db.collection("predictions").add(doc_data)
        return True
    except Exception as e:
        logger.error(f"[Firestore] write_prediction failed: {e}")
        return False


def get_latest_prediction(machine_id: str) -> Optional[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return None
    try:
        docs = (db.collection("predictions")
                .where("machineId", "==", machine_id)
                .order_by("timestamp", direction="DESCENDING")
                .limit(1)
                .stream())
        for doc in docs:
            return doc.to_dict()
        return None
    except Exception as e:
        logger.error(f"[Firestore] get_latest_prediction failed: {e}")
        return None


# ============================================================================
# DIAGNOSTICS
# ============================================================================

def write_diagnostic(data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "machineId": data.get("machineId", ""),
            "organizationId": data.get("organizationId", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items()},
        }
        db.collection("diagnostics").add(doc_data)
        return True
    except Exception as e:
        logger.error(f"[Firestore] write_diagnostic failed: {e}")
        return False


# ============================================================================
# ANOMALIES
# ============================================================================

def write_anomaly(data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "machineId": data.get("machineId", ""),
            "organizationId": data.get("organizationId", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items()},
        }
        db.collection("anomalies").add(doc_data)
        return True
    except Exception as e:
        logger.error(f"[Firestore] write_anomaly failed: {e}")
        return False


# ============================================================================
# MAINTENANCE PLANS
# ============================================================================

def upsert_maintenance_plan(plan_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "planId": plan_id,
            "organizationId": data.get("organizationId", ""),
            "machineId": data.get("machineId", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items()},
        }
        db.collection("maintenancePlans").document(plan_id).set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_maintenance_plan failed: {e}")
        return False


# ============================================================================
# WORK ORDERS
# ============================================================================

def upsert_work_order(wo_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "workOrderId": wo_id,
            "organizationId": data.get("organizationId", ""),
            "machineId": data.get("machineId", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items()},
        }
        db.collection("workOrders").document(wo_id).set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_work_order failed: {e}")
        return False


def get_work_orders_by_org(organization_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return []
    try:
        query = db.collection("workOrders").where("organizationId", "==", organization_id)
        if status:
            query = query.where("status", "==", status)
        docs = query.stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"[Firestore] get_work_orders_by_org failed: {e}")
        return []


# ============================================================================
# DOCUMENTS (metadata only — binary files go to Firebase Storage)
# ============================================================================

def save_document_metadata(doc_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "documentId": doc_id,
            "organizationId": data.get("organizationId", ""),
            "name": data.get("name", ""),
            "type": data.get("type", ""),
            "storagePath": data.get("storagePath", ""),
            "downloadUrl": data.get("downloadUrl", ""),
            "uploadedBy": data.get("uploadedBy", ""),
            "uploadedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items()
               if k not in ("organizationId", "name", "type", "storagePath", "downloadUrl", "uploadedBy")},
        }
        db.collection("documents").document(doc_id).set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] save_document_metadata failed: {e}")
        return False


def get_documents_by_org(organization_id: str) -> List[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return []
    try:
        docs = db.collection("documents").where("organizationId", "==", organization_id).stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"[Firestore] get_documents_by_org failed: {e}")
        return []


# ============================================================================
# AUDIT LOGS — append-only
# ============================================================================

def log_audit_event(data: Dict[str, Any]) -> bool:
    """
    Append an immutable audit log entry.
    Fields: organizationId, userId, role, action, resourceType, resourceId, timestamp, details
    """
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "organizationId": data.get("organizationId", ""),
            "userId": data.get("userId", ""),
            "role": data.get("role", ""),
            "action": data.get("action", ""),
            "resourceType": data.get("resourceType", ""),
            "resourceId": data.get("resourceId", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": data.get("details", {}),
        }
        db.collection("auditLogs").add(doc_data)
        return True
    except Exception as e:
        logger.error(f"[Firestore] log_audit_event failed: {e}")
        return False


def get_audit_logs(organization_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    db = _get_db()
    if not db:
        return []
    try:
        docs = (db.collection("auditLogs")
                .where("organizationId", "==", organization_id)
                .order_by("timestamp", direction="DESCENDING")
                .limit(limit)
                .stream())
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        logger.error(f"[Firestore] get_audit_logs failed: {e}")
        return []


# ============================================================================
# PRODUCTION AREAS
# ============================================================================

def upsert_production_area(area_id: str, data: Dict[str, Any]) -> bool:
    db = _get_db()
    if not db:
        return False
    try:
        doc_data = {
            "areaId": area_id,
            "factoryId": data.get("factoryId", ""),
            "organizationId": data.get("organizationId", ""),
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            **{k: v for k, v in data.items()},
        }
        db.collection("productionAreas").document(area_id).set(doc_data, merge=True)
        return True
    except Exception as e:
        logger.error(f"[Firestore] upsert_production_area failed: {e}")
        return False
