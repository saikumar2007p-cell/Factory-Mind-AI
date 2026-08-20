import React, { useState, useEffect, useRef } from 'react';
import './styles/theme.css';
import Sidebar from './components/Layout/Sidebar';
import TopNavbar from './components/Layout/TopNavbar';
import DashboardView from './components/Dashboard/DashboardView';
import MachinesView from './components/Machines/MachinesView';
import MachineDetailView from './components/Machines/MachineDetailView';
import AlertsView from './components/Alerts/AlertsView';
import InsightsView from './components/Insights/InsightsView';
import MaintenanceView from './components/Maintenance/MaintenanceView';
import FleetIntelligenceView from './components/Fleet/FleetIntelligenceView';
import ContinuousLearningView from './components/Learning/ContinuousLearningView';
import ProductionView from './components/Production/ProductionView';
import DocumentsView from './components/Documents/DocumentsView';
import SettingsView from './components/Settings/SettingsView';
import RoleAuthModal from './components/Layout/RoleAuthModal';
import LoginPage from './components/Layout/LoginPage';
import { isFirebaseConfigured } from './firebase/config';
import { onAuthStateChanged, signOutUser, getCurrentUserRole } from './firebase/auth';
import { syncFirebaseUser } from './services/api';

import {
  getMachines,
  getAlerts,
  acknowledgeAlert,
  getDiagnostics,
  getSimulationStatus,
  simulationStart,
  simulationPause,
  simulationResume,
  simulationStep,
  simulationReset,
  createWebSocketStream,
  getActiveDataSource,
  getUserSession,
  setUserSession,
  switchAuthRole,
  clearUserSession
} from './services/api';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [selectedMachineId, setSelectedMachineId] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [isRoleModalOpen, setIsRoleModalOpen] = useState(false);
  const [authLoading, setAuthLoading] = useState(isFirebaseConfigured);

  // Login gate
  const [isLoggedIn, setIsLoggedIn] = useState(() => {
    if (isFirebaseConfigured) return false; // Wait for onAuthStateChanged
    const sess = getUserSession();
    return !!sess.role && !!sess.actor;
  });

  // User Session & RBAC State
  const [userSession, setUserSessionState] = useState(() => getUserSession());
  const userRole = userSession?.role || 'ADMIN';
  const userActor = userSession?.actor || 'Chief Operations Admin';

  // Firebase auth state listener
  useEffect(() => {
    if (!isFirebaseConfigured) {
      setAuthLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(async (firebaseUser) => {
      if (firebaseUser) {
        // User is signed in via Firebase
        const role = await getCurrentUserRole() || 'VIEWER';
        const displayName = firebaseUser.displayName || firebaseUser.email;
        setUserSession(role, displayName);
        setUserSessionState(getUserSession());
        setIsLoggedIn(true);

        // Sync user to Firestore (fire-and-forget)
        try {
          await syncFirebaseUser({
            uid: firebaseUser.uid,
            email: firebaseUser.email,
            name: displayName,
            role: role,
          });
        } catch (e) {
          console.warn('[App] Firestore sync skipped:', e);
        }
      } else {
        // Signed out
        setIsLoggedIn(false);
      }
      setAuthLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const handleRoleAuthenticated = (newRole, newActor) => {
    setUserSession(newRole, newActor);
    const updated = getUserSession();
    setUserSessionState(updated);
  };

  const handleLogin = (role, actor, firebaseInfo) => {
    setUserSession(role, actor);
    setUserSessionState(getUserSession());
    setIsLoggedIn(true);
  };

  const handleLogout = async () => {
    if (isFirebaseConfigured) {
      await signOutUser();
    }
    clearUserSession();
    setIsLoggedIn(false);
    setUserSessionState({ role: '', actor: '' });
  };

  // Show loading spinner during Firebase auth check
  if (authLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0c4a6e 100%)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        color: '#94a3b8', fontSize: 14
      }}>
        Authenticating...
      </div>
    );
  }

  // Show login page
  if (!isLoggedIn) {
    return <LoginPage onLogin={handleLogin} />;
  }

  // Data State
  const [fleetSummary, setFleetSummary] = useState(null);
  const [machines, setMachines] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [simulationState, setSimulationState] = useState(null);
  const [activeDataSource, setActiveDataSource] = useState(null);
  const [latestLiveFrame, setLatestLiveFrame] = useState(null);
  const [latestDiagnosis, setLatestDiagnosis] = useState(null);
  const [diagnosticsLoading, setDiagnosticsLoading] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const wsConnectedRef = useRef(false);
  const [backendOffline, setBackendOffline] = useState(false);

  // Initial Data Load
  const refreshFleetData = async () => {
    try {
      const [mRes, aRes, sRes, dRes] = await Promise.allSettled([
        getMachines(),
        getAlerts(),
        getSimulationStatus(),
        getActiveDataSource()
      ]);

      if (mRes.status === 'fulfilled') {
        setFleetSummary(mRes.value);
        setMachines(mRes.value.machines || []);
        setBackendOffline(false);
      } else {
        setBackendOffline(true);
      }

      if (aRes.status === 'fulfilled') {
        setAlerts(aRes.value.alerts || []);
      }
      if (sRes.status === 'fulfilled') {
        setSimulationState(prev => {
          const restState = sRes.value;
          if (wsConnectedRef.current && prev) {
            return {
              ...restState,
              current_cycle: prev.current_cycle,
              unit_number: prev.unit_number,
              max_cycle: prev.max_cycle,
              is_running: prev.is_running,
              is_paused: prev.is_paused,
            };
          }
          return restState;
        });
      }
      if (dRes.status === 'fulfilled') {
        setActiveDataSource(dRes.value);
      }
    } catch (e) {
      console.warn('Backend connection degraded:', e);
      setBackendOffline(true);
    }
  };

  useEffect(() => {
    refreshFleetData();
    const interval = setInterval(refreshFleetData, 5000);
    return () => clearInterval(interval);
  }, []);

  // WebSocket Live Stream
  useEffect(() => {
    const ws = createWebSocketStream(
      (data) => {
        if (data.type === 'INITIAL_STATE' || data.type === 'SIMULATION_TICK') {
          setLatestLiveFrame(data);
          setSimulationState(prev => ({
            ...prev,
            is_running: data.is_running !== undefined ? data.is_running : prev?.is_running,
            is_paused: data.is_paused !== undefined ? data.is_paused : prev?.is_paused,
            current_cycle: data.cycle || data.current_cycle || prev?.current_cycle,
            max_cycle: data.max_cycle || prev?.max_cycle || 192,
            unit_number: data.unit_number || prev?.unit_number || 1
          }));

          if (data.alert) {
            setAlerts(prev => [data.alert, ...prev.filter(a => a.id !== data.alert.id)]);
          }
        }
      },
      (status) => {
        const connected = status === 'CONNECTED';
        wsConnectedRef.current = connected;
        setWsConnected(connected);
      }
    );

    return () => ws.close();
  }, []);

  // Diagnostics Trigger
  const handleRunDiagnostics = async (machineId, cycle = null) => {
    setDiagnosticsLoading(true);
    try {
      const diag = await getDiagnostics(machineId, cycle);
      setLatestDiagnosis(diag);
    } catch (err) {
      console.error('Diagnostics failed', err);
    } finally {
      setDiagnosticsLoading(false);
    }
  };

  // Alert Acknowledgement
  const handleAcknowledgeAlert = async (alertId) => {
    try {
      const updated = await acknowledgeAlert(alertId);
      setAlerts(prev => prev.map(a => a.id === alertId ? { ...a, status: 'ACKNOWLEDGED' } : a));
    } catch (err) {
      console.error('Failed to acknowledge alert', err);
    }
  };

  // Simulation Controls
  const handleStartSimulation = async () => {
    try {
      const res = await simulationStart({ unit_number: 1, start_cycle: 1, speed_multiplier: 1.0 });
      setSimulationState(res);
    } catch (err) {
      console.error('Failed to start simulation', err);
    }
  };

  const handlePauseSimulation = async () => {
    try {
      const res = await simulationPause();
      setSimulationState(res);
    } catch (err) {
      console.error('Failed to pause simulation', err);
    }
  };

  const handleResumeSimulation = async () => {
    try {
      const res = await simulationResume();
      setSimulationState(res);
    } catch (err) {
      console.error('Failed to resume simulation', err);
    }
  };

  const handleStepSimulation = async () => {
    try {
      const res = await simulationStep();
      if (res) {
        setLatestLiveFrame(prev => ({
          ...prev,
          cycle: res.cycle,
          unit_number: res.unit_number,
          prediction: res.prediction,
          telemetry: res.telemetry
        }));
        setSimulationState(prev => ({
          ...prev,
          current_cycle: res.cycle
        }));
        if (res.alert) {
          setAlerts(prev => [res.alert, ...prev.filter(a => a.id !== res.alert.id)]);
        }
      }
    } catch (err) {
      console.error('Failed to step simulation', err);
    }
  };

  const handleResetSimulation = async () => {
    try {
      const res = await simulationReset({ unit_number: 1, start_cycle: 1 });
      setSimulationState(res);
      setLatestLiveFrame(null);
    } catch (err) {
      console.error('Failed to reset simulation', err);
    }
  };

  const handleSelectMachine = (id) => {
    setSelectedMachineId(id);
  };

  const handleBackToFleet = () => {
    setSelectedMachineId(null);
  };

  const handleSelectTab = (tabId) => {
    setSelectedMachineId(null);
    setActiveTab(tabId);
  };

  // Determine Active Header Title
  const getPageTitle = () => {
    if (selectedMachineId) {
      return { title: `Machine Details — Unit #${String(selectedMachineId).padStart(3, '0')}`, sub: 'Detailed sensor measurements and AI root-cause diagnostics' };
    }
    switch (activeTab) {
      case 'dashboard': return { title: 'Fleet Overview', sub: 'Plant-wide health & degradation status' };
      case 'fleet': return { title: 'Fleet Intelligence & Predictive Planning', sub: 'Prognostic coverage, subsystem defect analytics, and planning priorities' };
      case 'learning': return { title: 'Continuous Learning & Maintenance Intelligence', sub: 'Verified outcomes, defect recurrence patterns, and executive analytics' };
      case 'machines': return { title: 'Machine Fleet', sub: 'Monitored industrial equipment across all datasets' };
      case 'alerts': return { title: 'Active Alarms', sub: 'Multi-cycle threshold events and alarms' };
      case 'insights': return { title: 'AI Diagnostics', sub: 'Grounded Gemini root cause reasoning' };
      case 'maintenance': return { title: 'Prescriptive Maintenance', sub: 'Actionable work orders and tasks' };
      case 'production': return { title: 'Test Cell Production', sub: 'Active test cell metrics' };
      case 'documents': return { title: 'Documents', sub: 'Engineering reference & blueprints' };
      case 'settings': return { title: 'Platform Settings', sub: 'System configuration' };
      default: return { title: 'FactoryMind AI', sub: 'Industrial Control Platform' };
    }
  };

  const { title, sub } = getPageTitle();

  return (
    <div className="app-container">
      {/* Permanent Sidebar Navigation */}
      <Sidebar
        activeTab={activeTab}
        onSelectTab={handleSelectTab}
        fleetSummary={fleetSummary}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* Main Working Area */}
      <div className="app-main">
        {/* Permanent Top Navigation Bar */}
        <TopNavbar
          title={title}
          subtitle={sub}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          simulationState={simulationState}
          onStartSimulation={handleStartSimulation}
          onPauseSimulation={handlePauseSimulation}
          onResumeSimulation={handleResumeSimulation}
          onStepSimulation={handleStepSimulation}
          onResetSimulation={handleResetSimulation}
          wsConnected={wsConnected}
          activeDataSource={activeDataSource}
          onNavigateSettings={() => handleSelectTab('settings')}
          onNavigateAlerts={() => handleSelectTab('alerts')}
          currentUserRole={userRole}
          currentUserActor={userActor}
          onOpenRoleModal={() => setIsRoleModalOpen(true)}
          onLogout={handleLogout}
        />

        {/* Role Session Access Banner */}
        {userRole !== 'ADMIN' && (
          <div style={{
            background: userRole === 'OPERATOR' ? '#eff6ff' : '#fef2f2',
            border: `1px solid ${userRole === 'OPERATOR' ? '#93c5fd' : '#fca5a5'}`,
            borderRadius: '8px',
            padding: '10px 16px',
            margin: '16px 32px 0 32px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '12px',
            fontSize: '12px',
            boxShadow: 'var(--shadow-sm)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '16px' }}>{userRole === 'OPERATOR' ? '🔧' : '🔒'}</span>
              <span style={{ color: userRole === 'OPERATOR' ? '#1e40af' : '#991b1b', fontWeight: 600 }}>
                <strong>{userRole === 'OPERATOR' ? 'OPERATOR SESSION (Execution Access)' : 'VIEWER SESSION (Strictly Read-Only)'}:</strong>{' '}
                {userRole === 'OPERATOR'
                  ? 'You can create, assign, start, complete, and verify work orders. Platform data connectors and security audit logs are restricted to Admin.'
                  : 'Read-Only Mode Active. All state mutations, work order creations, and platform settings are disabled for Viewer role.'}
              </span>
            </div>
            <span className={`badge ${userRole === 'OPERATOR' ? 'badge-ai' : 'badge-critical'}`}>
              ROLE: {userRole}
            </span>
          </div>
        )}

        {/* Content Viewport */}
        <main className="content-viewport">
          {backendOffline && (
            <div style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              borderRadius: '8px',
              padding: '12px 16px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <span style={{ fontSize: '16px' }}>⚠️</span>
                <div>
                  <div style={{ fontWeight: 600, color: '#ef4444', fontSize: '13px' }}>Backend Service Offline / Reconnecting</div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                    Unable to reach FastAPI backend on <code className="mono">http://127.0.0.1:8000</code>. Retrying automatically every 5s.
                  </div>
                </div>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={refreshFleetData}
                style={{ borderColor: 'rgba(239, 68, 68, 0.4)', color: '#ef4444' }}
              >
                Retry Now
              </button>
            </div>
          )}

          {selectedMachineId ? (
            <MachineDetailView
              machineId={selectedMachineId}
              onBack={handleBackToFleet}
              onRunDiagnostics={handleRunDiagnostics}
              diagnosticsLoading={diagnosticsLoading}
              latestDiagnosis={latestDiagnosis}
              userRole={userRole}
            />
          ) : (
            <>
              {activeTab === 'dashboard' && (
                <DashboardView
                  fleetSummary={fleetSummary}
                  machines={machines}
                  alerts={alerts}
                  simulationState={simulationState}
                  latestLiveFrame={latestLiveFrame}
                  onSelectMachine={handleSelectMachine}
                  onNavigateTab={handleSelectTab}
                  onAcknowledgeAlert={handleAcknowledgeAlert}
                  onRunDiagnostics={handleRunDiagnostics}
                  diagnosticsLoading={diagnosticsLoading}
                  latestDiagnosis={latestDiagnosis}
                  userRole={userRole}
                  searchQuery={searchQuery}
                />
              )}
              {activeTab === 'fleet' && (
                <FleetIntelligenceView
                  onSelectMachine={handleSelectMachine}
                  onNavigateTab={handleSelectTab}
                  userRole={userRole}
                  searchQuery={searchQuery}
                />
              )}
              {activeTab === 'learning' && (
                <ContinuousLearningView
                  onSelectMachine={handleSelectMachine}
                  onNavigateTab={handleSelectTab}
                  latestLiveFrame={latestLiveFrame}
                  userRole={userRole}
                  searchQuery={searchQuery}
                />
              )}
              {activeTab === 'machines' && (
                <MachinesView
                  machines={machines}
                  onSelectMachine={handleSelectMachine}
                  searchQuery={searchQuery}
                  onSearchChange={setSearchQuery}
                  userRole={userRole}
                />
              )}
              {activeTab === 'alerts' && (
                <AlertsView
                  alerts={alerts}
                  onAcknowledgeAlert={handleAcknowledgeAlert}
                  onSelectMachine={handleSelectMachine}
                  userRole={userRole}
                  searchQuery={searchQuery}
                />
              )}
              {activeTab === 'insights' && (
                <InsightsView
                  machines={machines}
                  onSelectMachine={handleSelectMachine}
                  onRunDiagnostics={handleRunDiagnostics}
                  diagnosticsLoading={diagnosticsLoading}
                  latestDiagnosis={latestDiagnosis}
                  userRole={userRole}
                  searchQuery={searchQuery}
                />
              )}
              {activeTab === 'maintenance' && (
                <MaintenanceView
                  latestDiagnosis={latestDiagnosis}
                  onSelectMachine={handleSelectMachine}
                  machines={machines}
                  userRole={userRole}
                  searchQuery={searchQuery}
                />
              )}
              {activeTab === 'production' && <ProductionView userRole={userRole} />}
              {activeTab === 'documents' && <DocumentsView userRole={userRole} searchFilter={searchQuery} />}
              {activeTab === 'settings' && <SettingsView userRole={userRole} />}
            </>
          )}
        </main>
      </div>

      <RoleAuthModal
        isOpen={isRoleModalOpen}
        onClose={() => setIsRoleModalOpen(false)}
        currentRole={userRole}
        currentActor={userActor}
        onRoleAuthenticated={handleRoleAuthenticated}
      />
    </div>
  );
}
