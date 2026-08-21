/**
 * frontend/src/services/api.js
 * 
 * Production API Client connecting to FastAPI backend.
 * 
 * Authentication:
 *   - Firebase mode: Automatically attaches Authorization: Bearer <Firebase ID token>
 *   - Dev mode: Falls back to X-User-Role / X-Actor-Name headers
 */

import { getIdToken } from '../firebase/auth';
import { isFirebaseConfigured } from '../firebase/config';

const API_BASE = 'http://127.0.0.1:8000/api/v1';
const WS_URL = 'ws://127.0.0.1:8000/api/v1/stream';

// Session Persistence State (dev mode fallback)
const SESSION_ROLE_KEY = 'factorymind_user_role';
const SESSION_ACTOR_KEY = 'factorymind_actor_name';

// In-Memory API Cache for instant (<1ms) tab navigation & non-blocking SWR
const apiCache = new Map();
const apiPending = new Map();

export function getCached(path) {
  const item = apiCache.get(path);
  return item ? item.data : null;
}

export function getUserSession() {
  const role = localStorage.getItem(SESSION_ROLE_KEY);
  const actor = localStorage.getItem(SESSION_ACTOR_KEY);
  if (!role || (role !== 'ADMIN' && role !== 'OPERATOR')) {
    return { role: null, actor: null };
  }
  return {
    role,
    actor: actor || (role === 'ADMIN' ? 'Chief Operations Admin' : 'Lead Maintenance Engineer')
  };
}

export function setUserSession(role, actor = null) {
  const normRole = role && role.toUpperCase() === 'ADMIN' ? 'ADMIN' : 'OPERATOR';
  localStorage.setItem(SESSION_ROLE_KEY, normRole);
  if (actor) {
    localStorage.setItem(SESSION_ACTOR_KEY, actor);
  } else {
    const defaultActor = normRole === 'ADMIN' ? 'Chief Operations Admin' : 'Lead Maintenance Engineer';
    localStorage.setItem(SESSION_ACTOR_KEY, defaultActor);
  }
}

export function clearUserSession() {
  localStorage.removeItem(SESSION_ROLE_KEY);
  localStorage.removeItem(SESSION_ACTOR_KEY);
  apiCache.clear();
  apiPending.clear();
}

// Generic Fetch Wrapper with in-memory caching + Firebase Bearer Token + Dev Fallback Headers
async function request(path, options = {}) {
  const isGet = !options.method || options.method.toUpperCase() === 'GET';
  const url = `${API_BASE}${path}`;

  // If GET and cached within 10s, return cached immediately unless forceRefresh
  if (isGet && !options.forceRefresh && apiCache.has(path)) {
    const cached = apiCache.get(path);
    if (Date.now() - cached.ts < 10000) {
      return cached.data;
    }
  }

  // Deduplicate identical simultaneous in-flight GET requests
  if (isGet && apiPending.has(path)) {
    return apiPending.get(path);
  }

  const fetchPromise = (async () => {
    try {
      const { role, actor } = getUserSession();
      const headers = {
        'Content-Type': 'application/json',
        ...options.headers,
      };

      if (isFirebaseConfigured) {
        try {
          const token = await getIdToken();
          if (token) {
            headers['Authorization'] = `Bearer ${token}`;
          }
        } catch (err) {
          console.warn('[API] Failed to get Firebase ID token:', err);
        }
      }

      headers['X-User-Role'] = role || 'ADMIN';
      headers['X-Admin-Role'] = (role || 'admin').toLowerCase();
      headers['X-Actor-Name'] = actor || 'User (ADMIN)';

      const response = await fetch(url, {
        ...options,
        headers,
      });

      if (!response.ok) {
        const errorBody = await response.text();
        let errorDetail = errorBody;
        try {
          const parsed = JSON.parse(errorBody);
          if (parsed.detail) {
            errorDetail = typeof parsed.detail === 'string' ? parsed.detail : JSON.stringify(parsed.detail);
          }
        } catch (_) {}

        if (response.status === 403) {
          errorDetail = errorDetail || 'Permission denied — Authorized role required.';
        } else if (response.status === 401) {
          errorDetail = errorDetail || 'Authentication required.';
        } else if (response.status === 429) {
          errorDetail = errorDetail || 'Rate limit reached. Please wait a moment.';
        }

        const err = new Error(errorDetail);
        err.status = response.status;
        throw err;
      }

      const contentType = response.headers.get('content-type');
      let data;
      if (contentType && contentType.includes('application/json')) {
        data = await response.json();
      } else {
        data = await response.text();
      }

      if (isGet) {
        apiCache.set(path, { data, ts: Date.now() });
      }
      return data;
    } finally {
      if (isGet) {
        apiPending.delete(path);
      }
    }
  })();

  if (isGet) {
    apiPending.set(path, fetchPromise);
  }
  return fetchPromise;
}

// Machines API
export const getMachines = () => request('/machines');
export const getMachine = (id) => request(`/machines/${id}`);

// Telemetry API
export const getTelemetry = (machineId, limit = 50, startCycle = null, endCycle = null) => {
  let query = `?limit=${limit}`;
  if (startCycle) query += `&start_cycle=${startCycle}`;
  if (endCycle) query += `&end_cycle=${endCycle}`;
  return request(`/telemetry/${machineId}${query}`);
};

// Predictions API
export const getLatestPrediction = (machineId) => request(`/predictions/${machineId}/latest`);
export const getPredictionHistory = (machineId, limit = 100) => request(`/predictions/${machineId}/history?limit=${limit}`);

// Alerts API
export const getAlerts = (machineId = null) => {
  const query = machineId ? `?machine_id=${machineId}` : '';
  return request(`/alerts${query}`);
};
export const getMachineAlerts = (machineId) => request(`/alerts/${machineId}`);
export const acknowledgeAlert = (alertId) => request(`/alerts/${alertId}/acknowledge`, { method: 'POST' });
export const getRecommendations = (machineId) => request(`/alerts/${machineId}/recommendations`);

// Diagnostics & Gemini RCA
export const getDiagnostics = (machineId, cycle = null) => {
  return request('/diagnostics/explain', {
    method: 'POST',
    body: JSON.stringify({ machine_id: machineId, cycle })
  });
};

// Simulation Controls
export const getSimulationStatus = () => request('/simulation/status');
export const simulationStart = (config = { unit_number: 1, start_cycle: 1, speed_multiplier: 1.0 }) => {
  return request('/simulation/start', {
    method: 'POST',
    body: JSON.stringify(config)
  });
};
export const simulationPause = () => request('/simulation/pause', { method: 'POST' });
export const simulationResume = () => request('/simulation/resume', { method: 'POST' });
export const simulationStop = () => request('/simulation/stop', { method: 'POST' });
export const simulationReset = (config = { unit_number: 1, start_cycle: 1 }) => {
  return request('/simulation/reset', {
    method: 'POST',
    body: JSON.stringify(config)
  });
};
export const simulationStep = () => request('/simulation/step', { method: 'POST' });

// Data Sources & Connectors API
export const getDataSources = () => request('/sources');
export const getActiveDataSource = () => request('/sources/active');
export const setActiveDataSource = (sourceId) => request(`/sources/set-active/${sourceId}`, {
  method: 'POST'
});
export const configureDataSource = (sourceId, restConfig = null, mqttConfig = null) => request('/sources/configure', {
  method: 'POST',
  body: JSON.stringify({
    source_id: sourceId,
    rest_config: restConfig,
    mqtt_config: mqttConfig
  })
});
export const testDataSourceConnection = (sourceId) => request(`/sources/test-connection/${sourceId}`, {
  method: 'POST'
});
export const uploadTelemetryFile = async (file, defaultMachineId = 'EXT_UNIT_01') => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('default_machine_id', defaultMachineId);

  const headers = {};

  // Attach Firebase token for file uploads too
  if (isFirebaseConfigured) {
    try {
      const token = await getIdToken();
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }
    } catch (err) {
      console.warn('[API] Failed to get Firebase token for upload:', err);
    }
  }

  // Dev fallback headers
  const { role, actor } = getUserSession();
  headers['X-User-Role'] = role;
  headers['X-Admin-Role'] = role.toLowerCase();
  headers['X-Actor-Name'] = actor;

  const response = await fetch(`${API_BASE}/sources/upload-file`, {
    method: 'POST',
    headers,
    body: formData
  });
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`Upload Error [${response.status}]: ${errorBody}`);
  }
  return response.json();
};
export const getSensorMappings = () => request('/sources/mappings');
export const updateSensorMappings = (mappings) => request('/sources/mappings', {
  method: 'POST',
  body: JSON.stringify({ mappings, unit_mappings: {} })
});
export const getMachineCompatibility = (machineId) => request(`/sources/compatibility/${machineId}`);

// Work Orders & Closed-Loop Maintenance API (Stage 8)
export const getWorkOrders = (params = {}) => {
  const query = new URLSearchParams();
  if (params.status && params.status !== 'ALL') query.append('status', params.status);
  if (params.machine_id) query.append('machine_id', params.machine_id);
  if (params.priority) query.append('priority', params.priority);
  const qs = query.toString();
  return request(`/work-orders${qs ? `?${qs}` : ''}`);
};

export const getWorkOrdersSummary = () => request('/work-orders/summary');

export const getWorkOrderDetails = (id) => request(`/work-orders/${id}`);

export const getWorkOrderComparison = (id) => request(`/work-orders/${id}/comparison`);

export const createWorkOrder = (payload) => request('/work-orders', {
  method: 'POST',
  body: JSON.stringify(payload)
});

export const assignWorkOrder = (id, assignedTo, notes = null) => request(`/work-orders/${id}/assign`, {
  method: 'POST',
  body: JSON.stringify({ assigned_to: assignedTo, notes })
});

export const startWorkOrder = (id) => request(`/work-orders/${id}/start`, {
  method: 'POST'
});

export const completeWorkOrder = (id) => request(`/work-orders/${id}/complete`, {
  method: 'POST'
});

export const verifyWorkOrder = (id, verificationStatus, verificationNotes = null) => request(`/work-orders/${id}/verify`, {
  method: 'POST',
  body: JSON.stringify({
    verification_status: verificationStatus,
    verification_notes: verificationNotes
  })
});

export const getMachineWorkOrders = (machineId) => request(`/machines/${machineId}/work-orders`);

// ============================================================================
// STAGE 9 FLEET INTELLIGENCE & PREDICTIVE PLANNING APIS
// ============================================================================

export const getFleetSummary = () => request('/fleet/summary');
export const getFleetMachines = (params = {}) => {
  const query = new URLSearchParams(params).toString();
  return request(`/fleet/machines${query ? `?${query}` : ''}`);
};
export const getFleetRiskDistribution = () => request('/fleet/risk-distribution');
export const getFleetMaintenanceLoad = () => request('/fleet/maintenance-load');
export const getFleetSubsystems = () => request('/fleet/subsystems');
export const getFleetAttentionRequired = () => request('/fleet/attention-required');
export const getFleetPlanning = () => request('/fleet/planning');

// Stage 10: Continuous Learning & Executive Intelligence APIs
export const getMaintenanceEffectiveness = () => request('/learning/maintenance-effectiveness');
export const getMachineMaintenanceHistory = (machineId = null) => {
  const q = machineId ? `?machine_id=${machineId}` : '';
  return request(`/learning/machine-history${q}`);
};
export const getRecurringFailures = () => request('/learning/recurring-failures');
export const getLearningSubsystems = () => request('/learning/subsystems');
export const getLearningSignals = () => request('/learning/signals');
export const getHistoricalTrends = (trendType = null) => {
  const q = trendType ? `?trend_type=${encodeURIComponent(trendType)}` : '';
  return request(`/learning/trends${q}`);
};
export const getExecutiveSummary = () => request('/learning/executive-summary');
export const getLearningOverview = () => request('/learning/overview');

// ============================================================================
// STAGE 11 AUTHENTICATION & SECURITY AUDIT APIS
// ============================================================================

export const authRegister = (email, password, displayName = null, role = 'ADMIN') => request('/auth/register', {
  method: 'POST',
  body: JSON.stringify({
    email,
    password,
    display_name: displayName,
    role
  })
});

export const authLogin = (email, password) => request('/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email, password })
});

export const getAuthMe = () => request('/auth/me');
export const getAuthRoles = () => request('/auth/roles');
export const switchAuthRole = (role, actorName = null) => request('/auth/switch-role', {
  method: 'POST',
  body: JSON.stringify({ role, actor_name: actorName })
});
export const getSecurityLogs = (limit = 100) => request(`/auth/security-audit-logs?limit=${limit}`);
export const clearAuthSession = () => request('/auth/clear-session', { method: 'POST' });

// ============================================================================
// FIREBASE AUTH APIS
// ============================================================================

export const verifyFirebaseToken = () => request('/firebase/verify');
export const syncFirebaseUser = (payload = {}) => request('/firebase/sync-user', {
  method: 'POST',
  body: JSON.stringify(payload)
});
export const setFirebaseUserRole = (uid, role, organizationId) => request('/firebase/set-role', {
  method: 'POST',
  body: JSON.stringify({ uid, role, organization_id: organizationId })
});

// ============================================================================
// PHASE 2 HARDENING APIS
// ============================================================================

// Model Version Registry & Rollback
export const getModelVersions = (machineId = null, statusFilter = null) => {
  let query = '';
  const params = [];
  if (machineId) params.push(`machine_id=${machineId}`);
  if (statusFilter) params.push(`status_filter=${statusFilter}`);
  if (params.length) query = `?${params.join('&')}`;
  return request(`/model-versions${query}`);
};
export const getActiveModelVersion = (machineId) => request(`/model-versions/machine/${machineId}/active`);
export const getRollbackCandidates = (machineId) => request(`/model-versions/machine/${machineId}/rollback-candidates`);
export const registerModelCandidate = (payload) => request('/model-versions', {
  method: 'POST',
  body: JSON.stringify(payload)
});
export const approveModelVersion = (versionId, approvedBy, notes = null) => request(`/model-versions/${versionId}/approve`, {
  method: 'POST',
  body: JSON.stringify({ approved_by: approvedBy, notes })
});
export const rollbackModelVersion = (machineId, rollbackReason, rolledBackBy) => request(`/model-versions/machine/${machineId}/rollback`, {
  method: 'POST',
  body: JSON.stringify({ rollback_reason: rollbackReason, rolled_back_by: rolledBackBy })
});

// Behavioral Change & Drift Detection
export const getBehavioralChanges = (machineId, statusFilter = null) => {
  const query = statusFilter ? `?investigation_status=${statusFilter}` : '';
  return request(`/drift/machine/${machineId}${query}`);
};
export const getFleetPendingChanges = () => request('/drift/fleet/pending');
export const investigateBehavioralChange = (changeId, payload) => request(`/drift/${changeId}/investigate`, {
  method: 'POST',
  body: JSON.stringify(payload)
});

// Ground-Truth Maintenance Outcomes
export const getOutcomes = (limit = 50) => request(`/outcomes?limit=${limit}`);
export const getMachineOutcomes = (machineId) => request(`/outcomes/machine/${machineId}`);
export const getModelPerformance = () => request('/outcomes/performance');
export const getRetrainingCandidates = () => request('/outcomes/retraining-candidates');
export const recordOutcome = (payload) => request('/outcomes', {
  method: 'POST',
  body: JSON.stringify(payload)
});

// Named User Management (Multi-Admin)
export const getUsers = () => request('/users');
export const getMyUser = () => request('/users/me');
export const createUser = (payload) => request('/users', {
  method: 'POST',
  body: JSON.stringify(payload)
});
export const updateUserRole = (userId, newRole) => request(`/users/${userId}/role`, {
  method: 'PATCH',
  body: JSON.stringify({ new_role: newRole })
});
export const deactivateUser = (userId) => request(`/users/${userId}`, {
  method: 'DELETE'
});

// Machine Registration Review Gate
export const getMachineRegistrations = (statusFilter = null) => {
  const query = statusFilter ? `?status_filter=${statusFilter}` : '';
  return request(`/machine-registrations${query}`);
};
export const getPendingRegistrations = () => request('/machine-registrations/pending');
export const getPendingRegistrationCount = () => request('/machine-registrations/count-pending');
export const approveMachineRegistration = (requestId, payload) => request(`/machine-registrations/${requestId}/approve`, {
  method: 'POST',
  body: JSON.stringify(payload)
});
export const rejectMachineRegistration = (requestId, payload) => request(`/machine-registrations/${requestId}/reject`, {
  method: 'POST',
  body: JSON.stringify(payload)
});

// WebSocket Live Stream Connection
export function createWebSocketStream(onMessage, onStatusChange) {
  let socket = null;
  let isClosedExplicitly = false;
  let reconnectTimer = null;

  function connect() {
    try {
      socket = new WebSocket(WS_URL);

      socket.onopen = () => {
        if (onStatusChange) onStatusChange('CONNECTED');
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onMessage) onMessage(data);
        } catch (e) {
          console.warn('Malformed WS message', e);
        }
      };

      socket.onclose = () => {
        if (onStatusChange) onStatusChange('DISCONNECTED');
        if (!isClosedExplicitly) {
          reconnectTimer = setTimeout(connect, 2000);
        }
      };

      socket.onerror = (err) => {
        if (onStatusChange) onStatusChange('ERROR');
      };
    } catch (err) {
      if (onStatusChange) onStatusChange('ERROR');
    }
  }

  connect();

  return {
    send: (msg) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(msg);
      }
    },
    close: () => {
      isClosedExplicitly = true;
      if (reconnectTimer) clearTimeout(reconnectTimer);
      if (socket) socket.close();
    }
  };
}

// ============================================================================
// MULTI-DATASET & EQUIPMENT REGISTRY APIS
// ============================================================================

export const getDatasets = () => request('/datasets/');
export const getDatasetStatus = () => request('/datasets/status');
export const getEquipmentTypes = () => request('/datasets/equipment-types');
export const getDatasetDetail = (datasetId) => request(`/datasets/${datasetId}`);
export const getDatasetSensors = (datasetId) => request(`/datasets/${datasetId}/sensors`);
export const getDatasetTasks = (datasetId) => request(`/datasets/${datasetId}/tasks`);
export const checkDatasetAvailability = (datasetId) => request(`/datasets/${datasetId}/availability`);

// ============================================================================
// WHATSAPP ALERT & ADMIN NOTIFICATION APIS
// ============================================================================

export const getWhatsAppSettings = () => request('/notifications/whatsapp/settings');

export const updateWhatsAppSettings = (data) =>
  request('/notifications/whatsapp/settings', {
    method: 'POST',
    body: JSON.stringify(data)
  });

export const sendWhatsAppAlert = (alertData) =>
  request('/notifications/whatsapp/send', {
    method: 'POST',
    body: JSON.stringify(alertData)
  });

export const testWhatsAppAlert = (phoneNumber) =>
  request('/notifications/whatsapp/test', {
    method: 'POST',
    body: JSON.stringify(phoneNumber ? { phone_number: phoneNumber } : {})
  });

export const getWhatsAppLogs = () => request('/notifications/whatsapp/logs');

export const triggerAutomatedCycleAlert = (machineId = 1) =>
  request(`/notifications/whatsapp/trigger-automated-cycle?machine_id=${machineId}`, {
    method: 'POST'
  });

export function openWhatsAppDirect(phone, message) {
  let cleanPhone = (phone || '').replace(/[^\d+]/g, '').replace(/^\+/, '');
  if (cleanPhone.length === 10 && /^[6789]/.test(cleanPhone)) {
    cleanPhone = `91${cleanPhone}`;
  }
  const encoded = encodeURIComponent(message || '🚨 FactoryMind AI Alert Notification');
  const url = cleanPhone ? `https://wa.me/${cleanPhone}?text=${encoded}` : `https://api.whatsapp.com/send?text=${encoded}`;
  window.open(url, '_blank', 'noopener,noreferrer');
  return url;
}


