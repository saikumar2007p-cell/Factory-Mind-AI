/**
 * frontend/src/services/api.js
 * 
 * Production API Client connecting to FastAPI backend and live WebSocket stream.
 */

const API_BASE = 'http://127.0.0.1:8000/api/v1';
const WS_URL = 'ws://127.0.0.1:8000/api/v1/stream';

// Session Persistence State
const SESSION_ROLE_KEY = 'factorymind_user_role';
const SESSION_ACTOR_KEY = 'factorymind_actor_name';

export function getUserSession() {
  const role = localStorage.getItem(SESSION_ROLE_KEY) || 'ADMIN';
  const actor = localStorage.getItem(SESSION_ACTOR_KEY) || (role === 'ADMIN' ? 'Chief Operations Admin' : (role === 'OPERATOR' ? 'Field Engineer' : 'Read-Only Auditor'));
  return { role, actor };
}

export function setUserSession(role, actor = null) {
  const normRole = role ? role.toUpperCase() : 'OPERATOR';
  localStorage.setItem(SESSION_ROLE_KEY, normRole);
  if (actor) {
    localStorage.setItem(SESSION_ACTOR_KEY, actor);
  } else {
    const defaultActor = normRole === 'ADMIN' ? 'Chief Operations Admin' : (normRole === 'OPERATOR' ? 'Field Engineer' : 'Read-Only Auditor');
    localStorage.setItem(SESSION_ACTOR_KEY, defaultActor);
  }
}

export function clearUserSession() {
  localStorage.removeItem(SESSION_ROLE_KEY);
  localStorage.removeItem(SESSION_ACTOR_KEY);
}

// Generic Fetch Wrapper with Dynamic RBAC Headers
async function request(path, options = {}) {
  const url = `${API_BASE}${path}`;
  const { role, actor } = getUserSession();

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      'X-User-Role': role,
      'X-Admin-Role': role.toLowerCase(),
      'X-Actor-Name': actor,
      ...options.headers,
    },
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

    // Clean user-friendly message
    if (response.status === 403) {
      errorDetail = errorDetail || 'Permission denied — Authorized role required.';
    } else if (response.status === 401) {
      errorDetail = errorDetail || 'Authentication required.';
    } else if (response.status === 429) {
      errorDetail = errorDetail || 'Rate limit reached. Please wait a moment.';
    }

    const err = new Error(errorDetail);
    err.status = response.status;
    err.detail = errorDetail;
    throw err;
  }

  return response.json();
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
  const { role, actor } = getUserSession();
  const response = await fetch(`${API_BASE}/sources/upload-file`, {
    method: 'POST',
    headers: {
      'X-User-Role': role,
      'X-Admin-Role': role.toLowerCase(),
      'X-Actor-Name': actor
    },
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

export const getAuthMe = () => request('/auth/me');
export const getAuthRoles = () => request('/auth/roles');
export const switchAuthRole = (role, actorName = null) => request('/auth/switch-role', {
  method: 'POST',
  body: JSON.stringify({ role, actor_name: actorName })
});
export const getSecurityLogs = (limit = 100) => request(`/auth/security-audit-logs?limit=${limit}`);
export const clearAuthSession = () => request('/auth/clear-session', { method: 'POST' });

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
