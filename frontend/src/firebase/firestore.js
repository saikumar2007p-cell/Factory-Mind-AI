/**
 * frontend/src/firebase/firestore.js
 *
 * Firestore data access layer for FactoryMind AI.
 * Centralized queries — no raw Firestore calls in React components.
 */

import {
  collection, doc, getDoc, getDocs, addDoc, setDoc, updateDoc,
  query, where, orderBy, limit, onSnapshot, serverTimestamp,
} from 'firebase/firestore';
import { db, isFirebaseConfigured } from './config';

// ── Helper ──
function checkDb() {
  if (!isFirebaseConfigured || !db) {
    console.warn('[Firestore] Not configured — operation skipped');
    return false;
  }
  return true;
}

// ============================================================================
// USERS
// ============================================================================

export async function getUserProfile(uid) {
  if (!checkDb()) return null;
  const snap = await getDoc(doc(db, 'users', uid));
  return snap.exists() ? snap.data() : null;
}

export async function saveUserProfile(uid, data) {
  if (!checkDb()) return;
  await setDoc(doc(db, 'users', uid), {
    ...data,
    updatedAt: serverTimestamp(),
  }, { merge: true });
}

// ============================================================================
// ORGANIZATIONS
// ============================================================================

export async function getOrganization(orgId) {
  if (!checkDb()) return null;
  const snap = await getDoc(doc(db, 'organizations', orgId));
  return snap.exists() ? snap.data() : null;
}

// ============================================================================
// DOCUMENTS (metadata — files are in Firebase Storage)
// ============================================================================

export async function getDocuments(orgId) {
  if (!checkDb()) return [];
  const q = query(
    collection(db, 'documents'),
    where('organizationId', '==', orgId),
    orderBy('uploadedAt', 'desc')
  );
  const snap = await getDocs(q);
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

export async function saveDocumentMetadata(data) {
  if (!checkDb()) return null;
  const docRef = await addDoc(collection(db, 'documents'), {
    ...data,
    uploadedAt: serverTimestamp(),
  });
  return docRef.id;
}

// ============================================================================
// AUDIT LOGS
// ============================================================================

export async function getAuditLogs(orgId, maxResults = 100) {
  if (!checkDb()) return [];
  const q = query(
    collection(db, 'auditLogs'),
    where('organizationId', '==', orgId),
    orderBy('timestamp', 'desc'),
    limit(maxResults)
  );
  const snap = await getDocs(q);
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

/**
 * Real-time listener for audit logs (admin dashboard).
 * Returns unsubscribe function.
 */
export function listenToAuditLogs(orgId, callback, maxResults = 50) {
  if (!checkDb()) return () => {};
  const q = query(
    collection(db, 'auditLogs'),
    where('organizationId', '==', orgId),
    orderBy('timestamp', 'desc'),
    limit(maxResults)
  );
  return onSnapshot(q, (snap) => {
    const logs = snap.docs.map(d => ({ id: d.id, ...d.data() }));
    callback(logs);
  });
}

// ============================================================================
// MACHINES
// ============================================================================

export async function getMachinesFromFirestore(orgId) {
  if (!checkDb()) return [];
  const q = query(
    collection(db, 'machines'),
    where('organizationId', '==', orgId)
  );
  const snap = await getDocs(q);
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

// ============================================================================
// WORK ORDERS
// ============================================================================

export async function getWorkOrdersFromFirestore(orgId, statusFilter = null) {
  if (!checkDb()) return [];
  let q;
  if (statusFilter) {
    q = query(
      collection(db, 'workOrders'),
      where('organizationId', '==', orgId),
      where('status', '==', statusFilter)
    );
  } else {
    q = query(
      collection(db, 'workOrders'),
      where('organizationId', '==', orgId)
    );
  }
  const snap = await getDocs(q);
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

// ============================================================================
// TELEMETRY
// ============================================================================

export async function getTelemetryFromFirestore(machineId, maxResults = 50) {
  if (!checkDb()) return [];
  const q = query(
    collection(db, 'telemetry'),
    where('machineId', '==', machineId),
    orderBy('cycle', 'desc'),
    limit(maxResults)
  );
  const snap = await getDocs(q);
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

// ============================================================================
// PREDICTIONS
// ============================================================================

export async function getLatestPredictionFromFirestore(machineId) {
  if (!checkDb()) return null;
  const q = query(
    collection(db, 'predictions'),
    where('machineId', '==', machineId),
    orderBy('timestamp', 'desc'),
    limit(1)
  );
  const snap = await getDocs(q);
  return snap.docs.length > 0 ? { id: snap.docs[0].id, ...snap.docs[0].data() } : null;
}
