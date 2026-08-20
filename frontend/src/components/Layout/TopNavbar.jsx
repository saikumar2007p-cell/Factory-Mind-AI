import React from 'react';
import {
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  Search,
  Bell,
  Radio,
  User,
  Database,
  Lock
} from 'lucide-react';

export default function TopNavbar({
  title,
  subtitle,
  searchQuery,
  onSearchChange,
  simulationState,
  onStartSimulation,
  onPauseSimulation,
  onResumeSimulation,
  onStepSimulation,
  onResetSimulation,
  wsConnected,
  activeDataSource,
  onNavigateSettings,
  onNavigateAlerts,
  currentUserRole,
  currentUserActor,
  onRoleChange,
  onOpenRoleModal
}) {
  const isRunning = simulationState?.is_running;
  const isPaused = simulationState?.is_paused;
  // Stabilize counters: never show 0/undefined, always show last known good value
  const currentCycle = simulationState?.current_cycle ?? 0;
  const maxCycle = simulationState?.max_cycle ?? 192;
  const unitNumber = simulationState?.unit_number ?? 1;

  const sourceName = activeDataSource?.name || 'NASA C-MAPSS FD001';
  const isSimulation = activeDataSource?.is_simulation ?? true;
  const sourceStatus = activeDataSource?.status || 'CONNECTED';

  return (
    <header className="app-topbar">
      {/* Left: Page Title & Context */}
      <div className="topbar-left" style={{ minWidth: '220px' }}>
        <h1 className="topbar-title">{title}</h1>
        {subtitle && <span className="topbar-subtitle">{subtitle}</span>}
      </div>

      {/* Center: Search Field */}
      <div className="topbar-center" style={{ display: 'flex', alignItems: 'center', flex: 1, maxWidth: '360px', margin: '0 16px' }}>
        <div className="search-input-wrapper" style={{ width: '100%' }}>
          <Search size={15} className="search-icon" color="#64748b" />
          <input
            type="text"
            className="search-input"
            placeholder="Search engines, telemetry sensors, or alerts..."
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            style={{ width: '100%', fontSize: '13px', background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: '8px', color: '#0f172a' }}
          />
        </div>
      </div>

      {/* Right: Controls & User Profile Toolbar */}
      <div className="topbar-right" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Active Data Source Pill */}
        <div
          onClick={onNavigateSettings}
          title={`Active Data Source: ${sourceName} (${isSimulation ? 'Simulation' : 'Real Industrial Data'})`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            borderRadius: '6px',
            backgroundColor: '#ffffff',
            border: '1px solid #cbd5e1',
            fontSize: '11px',
            cursor: onNavigateSettings ? 'pointer' : 'default',
            whiteSpace: 'nowrap',
            color: '#1e293b',
            fontWeight: 600,
            boxShadow: 'var(--shadow-sm)'
          }}
        >
          <Database size={13} color="#2563eb" />
          <span>{sourceName}</span>
          <span
            style={{
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: sourceStatus === 'CONNECTED' ? '#16a34a' : '#d97706'
            }}
          />
        </div>

        {/* Replay Toolbar */}
        <div className="replay-toolbar" style={{ display: 'flex', alignItems: 'center', gap: '4px', background: '#ffffff', border: '1px solid #cbd5e1', padding: '4px 8px', borderRadius: '6px', boxShadow: 'var(--shadow-sm)' }}>
          <span style={{ fontSize: '11px', fontWeight: 700, color: '#475569', textTransform: 'uppercase', marginRight: '2px' }}>
            Unit #{String(unitNumber).padStart(3, '0')}
          </span>

          {!isRunning || isPaused ? (
            <button
              className="btn-ctrl active-play"
              onClick={isRunning ? onResumeSimulation : onStartSimulation}
              title={isRunning ? 'Resume Replay' : 'Start Replay'}
              style={{ padding: '3px 6px', background: '#2563eb', color: '#ffffff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              <Play size={12} />
            </button>
          ) : (
            <button
              className="btn-ctrl"
              onClick={onPauseSimulation}
              title="Pause Replay"
              style={{ padding: '3px 6px', background: '#d97706', color: '#ffffff', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              <Pause size={12} />
            </button>
          )}

          <button
            className="btn-ctrl"
            onClick={onStepSimulation}
            title="Step Next Cycle"
            style={{ padding: '3px 6px', background: '#f1f5f9', color: '#0f172a', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer' }}
          >
            <SkipForward size={12} />
          </button>

          <button
            className="btn-ctrl"
            onClick={onResetSimulation}
            title="Reset Trajectory to Cycle 1"
            style={{ padding: '3px 6px', background: '#f1f5f9', color: '#0f172a', border: '1px solid #cbd5e1', borderRadius: '4px', cursor: 'pointer' }}
          >
            <RotateCcw size={12} />
          </button>

          <span className="mono" style={{ fontSize: '11px', fontWeight: 700, color: '#0f172a', marginLeft: '4px' }}>
            {currentCycle}/{maxCycle}
          </span>
        </div>

        {/* Live Stream Connection Badge */}
        <div
          className={`badge ${wsConnected ? 'badge-normal' : 'badge-offline'}`}
          title={wsConnected ? 'WebSocket Live Streaming Active' : 'WebSocket Reconnecting'}
          style={{ fontSize: '11px', padding: '4px 8px' }}
        >
          <Radio size={12} className={wsConnected ? 'pulse' : ''} />
          <span>{wsConnected ? 'Live' : 'Polling'}</span>
        </div>

        {/* Notifications Icon */}
        <button
          className="btn-ctrl"
          style={{ position: 'relative', background: '#ffffff', border: '1px solid #cbd5e1', padding: '6px', borderRadius: '6px', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
          title="Active Alerts"
          onClick={onNavigateAlerts}
        >
          <Bell size={16} color="#0f172a" />
          <span
            style={{
              position: 'absolute',
              top: '4px',
              right: '4px',
              width: '6px',
              height: '6px',
              background: '#dc2626',
              borderRadius: '50%'
            }}
          />
        </button>

        {/* Role-Based Access Control Pill */}
        <button
          onClick={onOpenRoleModal}
          style={{
            background: currentUserRole === 'ADMIN' ? '#fef2f2' : (currentUserRole === 'OPERATOR' ? '#eff6ff' : '#f8fafc'),
            color: currentUserRole === 'ADMIN' ? '#991b1b' : (currentUserRole === 'OPERATOR' ? '#1e40af' : '#334155'),
            border: `1px solid ${currentUserRole === 'ADMIN' ? '#fca5a5' : (currentUserRole === 'OPERATOR' ? '#93c5fd' : '#cbd5e1')}`,
            borderRadius: '6px',
            padding: '5px 10px',
            fontSize: '11px',
            fontWeight: 700,
            cursor: 'pointer',
            boxShadow: 'var(--shadow-sm)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
          title="Click to authenticate session role (Admin vs Operator vs Viewer)"
        >
          <span>
            {currentUserRole === 'ADMIN' ? '👑 Admin — Full Access' : (currentUserRole === 'OPERATOR' ? '🔧 Operator — Operations' : '👁️ Viewer — Read Only')}
          </span>
        </button>

        {/* User Avatar */}
        <div
          onClick={onOpenRoleModal}
          style={{
            width: '30px',
            height: '30px',
            borderRadius: '50%',
            backgroundColor: currentUserRole === 'ADMIN' ? '#991b1b' : (currentUserRole === 'OPERATOR' ? '#1e40af' : '#334155'),
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#ffffff',
            fontWeight: '700',
            fontSize: '11px',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-sm)'
          }}
          title={`Click to authenticate role. Current User: ${currentUserActor || 'Authorized User'} (${currentUserRole || 'ADMIN'})`}
        >
          <User size={15} />
        </div>
      </div>
    </header>
  );
}
