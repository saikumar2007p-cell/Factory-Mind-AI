import React, { useState, useRef, useEffect } from 'react';
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
  Lock,
  LogOut,
  Cpu,
  Activity,
  AlertTriangle,
  BrainCircuit,
  Wrench,
  Layers,
  TrendingUp,
  Sliders,
  CheckCircle2,
  ChevronRight,
  Sparkles,
  X
} from 'lucide-react';

const SENSOR_CATALOG = [
  { id: 's_2', name: 'T24 - LPC Outlet Temp', unit: '°R', type: 'temperature', machine: 'Turbofan' },
  { id: 's_3', name: 'T30 - HPC Outlet Temp', unit: '°R', type: 'temperature', machine: 'Turbofan' },
  { id: 's_4', name: 'T50 - LPT Outlet Temp', unit: '°R', type: 'temperature', machine: 'Turbofan' },
  { id: 's_7', name: 'Ps30 - HPC Outlet Pressure', unit: 'psia', type: 'pressure', machine: 'Turbofan' },
  { id: 's_8', name: 'phi - Fuel Flow Ratio', unit: 'ratio', type: 'flow', machine: 'Turbofan' },
  { id: 's_9', name: 'NRf - Physical Fan Speed', unit: 'rpm', type: 'speed', machine: 'Turbofan' },
  { id: 's_11', name: 'NRc - Physical Core Speed', unit: 'rpm', type: 'speed', machine: 'Turbofan' },
  { id: 's_12', name: 'BPR - Bypass Ratio', unit: 'ratio', type: 'ratio', machine: 'Turbofan' },
  { id: 's_13', name: 'farB - Burner Fuel-Air Ratio', unit: 'ratio', type: 'ratio', machine: 'Turbofan' },
  { id: 's_14', name: 'htBleed - Bleed Enthalpy', unit: 'BTU/s', type: 'energy', machine: 'Turbofan' },
  { id: 's_15', name: 'Nf_dmd - Demanded Fan Speed', unit: 'rpm', type: 'speed', machine: 'Turbofan' },
  { id: 's_17', name: 'W32 - HPT Coolant Bleed', unit: 'lb/s', type: 'flow', machine: 'Turbofan' },
  { id: 's_20', name: 'BPR Corrected', unit: 'ratio', type: 'ratio', machine: 'Turbofan' },
  { id: 's_21', name: 'W31 - HPT Coolant Corrected', unit: 'lb/s', type: 'flow', machine: 'Turbofan' },
  { id: 'input_voltage', name: 'Input Shaft Accelerometer', unit: 'V', type: 'vibration', machine: 'Gearbox' },
  { id: 'output_voltage', name: 'Output Shaft Accelerometer', unit: 'V', type: 'vibration', machine: 'Gearbox' },
  { id: 'tachometer', name: 'Tachometer Speed Pulses', unit: 'pulses', type: 'speed', machine: 'Gearbox' },
  { id: 'pressure_upstream', name: 'Solenoid Upstream Pressure', unit: 'kPa', type: 'pressure', machine: 'Valve' },
  { id: 'pressure_downstream', name: 'Solenoid Downstream Pressure', unit: 'kPa', type: 'pressure', machine: 'Valve' },
  { id: 'valve_command', name: 'Solenoid Valve Command Signal', unit: 'binary', type: 'control', machine: 'Valve' },
];

const NAVIGATION_SUGGESTIONS = [
  { id: 'dashboard', label: 'Fleet Overview & Real-Time Prognostics', icon: Activity, desc: 'Overall health status, critical units, and live playback' },
  { id: 'fleet', label: 'Fleet Intelligence & Predictive Planning', icon: Layers, desc: 'Prognostic coverage, subsystem analytics & planning queues' },
  { id: 'learning', label: 'Continuous Learning & Executive Intelligence', icon: TrendingUp, desc: 'Verified resolution metrics & recurring defect patterns' },
  { id: 'machines', label: 'Machine Fleet Directory', icon: Cpu, desc: 'Browse all 178 monitored engines, gearboxes & valves' },
  { id: 'alerts', label: 'Active Alarms & Alarms Ledger', icon: AlertTriangle, desc: 'Multi-cycle threshold breaches and warnings' },
  { id: 'insights', label: 'Grounded Gemini AI Diagnostics', icon: BrainCircuit, desc: 'Root-cause evidence & prescriptive work recommendations' },
  { id: 'maintenance', label: 'Closed-Loop Maintenance Work Orders', icon: Wrench, desc: 'Stage 8 lifecycle: Open -> Assigned -> In Progress -> Verified' },
  { id: 'settings', label: 'Datasets & Equipment Registry', icon: Database, desc: 'C-MAPSS FD001, PHM 2009 Gearbox, PHMAP 2023 Valve', adminOnly: true },
];

export default function TopNavbar({
  title,
  subtitle,
  searchQuery = '',
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
  onOpenRoleModal,
  onLogout,
  machines = [],
  alerts = [],
  onSelectMachine,
  onNavigateTab
}) {
  const [isOpen, setIsOpen] = useState(false);
  const searchContainerRef = useRef(null);

  const isRunning = simulationState?.is_running;
  const isPaused = simulationState?.is_paused;
  const currentCycle = simulationState?.current_cycle ?? 0;
  const maxCycle = simulationState?.max_cycle ?? 192;
  const unitNumber = simulationState?.unit_number ?? 1;

  const sourceName = activeDataSource?.name || 'NASA C-MAPSS FD001';
  const isSimulation = activeDataSource?.is_simulation ?? true;
  const sourceStatus = activeDataSource?.status || 'CONNECTED';

  // Click outside to close recommendations
  useEffect(() => {
    function handleClickOutside(event) {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const q = (searchQuery || '').trim().toLowerCase();

  // Filter machines
  const matchingMachines = machines.filter(m => {
    if (!q) return true;
    const uStr = String(m.unit_number || m.id);
    return uStr.includes(q) ||
      `unit #${uStr}`.toLowerCase().includes(q) ||
      (m.name && m.name.toLowerCase().includes(q)) ||
      (m.machine_type && m.machine_type.toLowerCase().includes(q)) ||
      (m.location && m.location.toLowerCase().includes(q));
  }).slice(0, 5);

  // Filter sensors
  const matchingSensors = SENSOR_CATALOG.filter(s => {
    if (!q) return false;
    return s.id.toLowerCase().includes(q) ||
      s.name.toLowerCase().includes(q) ||
      s.type.toLowerCase().includes(q) ||
      s.machine.toLowerCase().includes(q);
  }).slice(0, 4);

  // Filter navigation
  const matchingNav = NAVIGATION_SUGGESTIONS.filter(n => {
    if (n.adminOnly && currentUserRole !== 'ADMIN') return false;
    if (!q) return true;
    return n.label.toLowerCase().includes(q) ||
      n.desc.toLowerCase().includes(q) ||
      n.id.toLowerCase().includes(q);
  }).slice(0, 3);

  // Filter alerts
  const matchingAlerts = alerts.filter(a => {
    if (!q) return false;
    return (a.reason && a.reason.toLowerCase().includes(q)) ||
      (a.severity && a.severity.toLowerCase().includes(q)) ||
      String(a.machine_id).includes(q) ||
      String(a.id).includes(q);
  }).slice(0, 3);

  const handleSelectMachineJump = (machineId) => {
    setIsOpen(false);
    onSearchChange('');
    if (onSelectMachine) {
      onSelectMachine(machineId);
    }
  };

  const handleSelectNavJump = (tabId) => {
    setIsOpen(false);
    onSearchChange('');
    if (onNavigateTab) {
      onNavigateTab(tabId);
    }
  };

  const handleSelectSensor = (sensor) => {
    onSearchChange(sensor.id);
    setIsOpen(false);
  };

  return (
    <header className="app-topbar">
      {/* Left: Page Title & Context */}
      <div className="topbar-left" style={{ minWidth: '220px' }}>
        <h1 className="topbar-title">{title}</h1>
        {subtitle && <span className="topbar-subtitle">{subtitle}</span>}
      </div>

      {/* Center: Search Field with Smart Recommendations Dropdown */}
      <div
        ref={searchContainerRef}
        className="topbar-center"
        style={{ display: 'flex', alignItems: 'center', flex: 1, maxWidth: '420px', margin: '0 16px', position: 'relative' }}
      >
        <div className="search-input-wrapper" style={{ width: '100%', position: 'relative' }}>
          <Search size={15} className="search-icon" color="#64748b" />
          <input
            type="text"
            className="search-input"
            placeholder="Search units (e.g. #001), sensors (T50), alarms, or views..."
            value={searchQuery}
            onFocus={() => setIsOpen(true)}
            onChange={(e) => {
              onSearchChange(e.target.value);
              setIsOpen(true);
            }}
            onKeyDown={(e) => {
              if (e.key === 'Escape') {
                setIsOpen(false);
              }
            }}
            style={{
              width: '100%',
              fontSize: '13px',
              background: '#f8fafc',
              border: isOpen ? '1px solid #3b82f6' : '1px solid #cbd5e1',
              borderRadius: '8px',
              color: '#0f172a',
              paddingRight: searchQuery ? '30px' : '12px',
              boxShadow: isOpen ? '0 0 0 3px rgba(59, 130, 246, 0.15)' : 'none',
              transition: 'all 0.15s ease'
            }}
          />

          {searchQuery && (
            <button
              onClick={() => {
                onSearchChange('');
                setIsOpen(false);
              }}
              style={{
                position: 'absolute',
                right: '8px',
                top: '50%',
                transform: 'translateY(-50%)',
                background: 'transparent',
                border: 'none',
                color: '#94a3b8',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                padding: '2px'
              }}
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* Floating Recommended Suggestions Overlay */}
        {isOpen && (
          <div
            style={{
              position: 'absolute',
              top: 'calc(100% + 8px)',
              left: 0,
              right: 0,
              background: '#ffffff',
              borderRadius: '10px',
              border: '1px solid #cbd5e1',
              boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.15), 0 8px 10px -6px rgba(0, 0, 0, 0.1)',
              zIndex: 9999,
              maxHeight: '440px',
              overflowY: 'auto',
              padding: '8px 0'
            }}
          >
            {/* 1. Quick Navigation Recommendations */}
            {matchingNav.length > 0 && (
              <div style={{ marginBottom: '6px' }}>
                <div style={{ padding: '4px 14px', fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {q ? 'Matching Views' : '⚡ Recommended Actions'}
                </div>
                {matchingNav.map((n) => {
                  const NavIcon = n.icon;
                  return (
                    <div
                      key={n.id}
                      onClick={() => handleSelectNavJump(n.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '7px 14px',
                        cursor: 'pointer',
                        transition: 'background 0.1s ease',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#f1f5f9'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                        <div style={{ width: '24px', height: '24px', borderRadius: '6px', background: '#eff6ff', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <NavIcon size={13} color="#2563eb" />
                        </div>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 600, color: '#0f172a' }}>{n.label}</div>
                          <div style={{ fontSize: '10px', color: '#64748b' }}>{n.desc}</div>
                        </div>
                      </div>
                      <ChevronRight size={14} color="#94a3b8" />
                    </div>
                  );
                })}
              </div>
            )}

            {/* 2. Machines Matching */}
            {matchingMachines.length > 0 && (
              <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '6px', marginBottom: '6px' }}>
                <div style={{ padding: '4px 14px', fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  🤖 Matching Equipment & Units ({machines.length} total)
                </div>
                {matchingMachines.map((m) => {
                  const isCrit = m.latest_risk_level === 'CRITICAL' || m.status === 'CRITICAL';
                  const isWarn = m.latest_risk_level === 'WARNING' || m.status === 'WARNING';
                  const badgeColor = isCrit ? '#dc2626' : (isWarn ? '#d97706' : '#16a34a');
                  const badgeBg = isCrit ? '#fef2f2' : (isWarn ? '#fffbeb' : '#f0fdf4');
                  const rul = m.latest_rul != null ? `${m.latest_rul.toFixed(1)} cyc` : 'RUL: --';

                  return (
                    <div
                      key={m.id}
                      onClick={() => handleSelectMachineJump(m.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '7px 14px',
                        cursor: 'pointer',
                        transition: 'background 0.1s ease',
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#f1f5f9'}
                      onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '9px' }}>
                        <div style={{ width: '24px', height: '24px', borderRadius: '6px', background: '#f8fafc', border: '1px solid #cbd5e1', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '10px', fontWeight: 700, color: '#334155' }}>
                          #{String(m.unit_number || m.id).padStart(3, '0')}
                        </div>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 600, color: '#0f172a' }}>{m.name}</div>
                          <div style={{ fontSize: '10px', color: '#64748b' }}>
                            {m.machine_type || 'Turbofan Engine'} • {m.location || 'Test Cell'}
                          </div>
                        </div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span style={{ fontSize: '10px', fontWeight: 700, color: '#475569' }}>{rul}</span>
                        <span style={{ fontSize: '9px', fontWeight: 700, padding: '2px 6px', borderRadius: '4px', background: badgeBg, color: badgeColor, border: `1px solid ${badgeColor}30` }}>
                          {m.latest_risk_level || m.status || 'NORMAL'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {/* 3. Sensor Channels Matching */}
            {matchingSensors.length > 0 && (
              <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '6px', marginBottom: '6px' }}>
                <div style={{ padding: '4px 14px', fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  📊 Telemetry Sensors ({matchingSensors.length} found)
                </div>
                {matchingSensors.map((s) => (
                  <div
                    key={s.id}
                    onClick={() => handleSelectSensor(s)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '6px 14px',
                      cursor: 'pointer',
                      transition: 'background 0.1s ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f1f5f9'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '10px', fontFamily: 'monospace', fontWeight: 700, padding: '2px 6px', background: '#f1f5f9', borderRadius: '4px', border: '1px solid #cbd5e1' }}>
                        {s.id}
                      </span>
                      <span style={{ fontSize: '12px', color: '#0f172a', fontWeight: 500 }}>{s.name}</span>
                    </div>
                    <span style={{ fontSize: '10px', color: '#64748b', fontWeight: 600 }}>
                      {s.unit} • {s.type}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* 4. Active Alerts Matching */}
            {matchingAlerts.length > 0 && (
              <div style={{ borderTop: '1px solid #f1f5f9', paddingTop: '6px' }}>
                <div style={{ padding: '4px 14px', fontSize: '10px', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  ⚠️ Active Alarms ({matchingAlerts.length} found)
                </div>
                {matchingAlerts.map((a) => (
                  <div
                    key={a.id}
                    onClick={() => {
                      setIsOpen(false);
                      if (onSelectMachine && a.machine_id) {
                        onSelectMachine(a.machine_id);
                      } else if (onNavigateAlerts) {
                        onNavigateAlerts();
                      }
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '6px 14px',
                      cursor: 'pointer',
                      transition: 'background 0.1s ease',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#fef2f2'}
                    onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <AlertTriangle size={13} color="#dc2626" />
                      <span style={{ fontSize: '11px', color: '#0f172a', fontWeight: 600 }}>{a.reason || 'Telemetry Deviation'}</span>
                    </div>
                    <span style={{ fontSize: '10px', color: '#dc2626', fontWeight: 700 }}>
                      Unit #{String(a.machine_id).padStart(3, '0')}
                    </span>
                  </div>
                ))}
              </div>
            )}

            {/* Footer hint */}
            <div style={{ borderTop: '1px solid #f1f5f9', padding: '6px 14px', display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#94a3b8' }}>
              <span>Press <kbd style={{ background: '#f1f5f9', border: '1px solid #cbd5e1', borderRadius: '3px', padding: '1px 4px' }}>ESC</kbd> to dismiss</span>
              <span>Instant Omnibox Search Active</span>
            </div>
          </div>
        )}
      </div>

      {/* Right: Controls & User Profile Toolbar */}
      <div className="topbar-right" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {/* Active Data Source Pill */}
        <div
          onClick={currentUserRole === 'ADMIN' ? onNavigateSettings : undefined}
          title={currentUserRole === 'ADMIN' ? `Active Data Source: ${sourceName} (Click to manage settings)` : `Active Data Source: ${sourceName}`}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '5px 10px',
            borderRadius: '6px',
            backgroundColor: '#ffffff',
            border: '1px solid #cbd5e1',
            fontSize: '11px',
            cursor: currentUserRole === 'ADMIN' && onNavigateSettings ? 'pointer' : 'default',
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

        {/* Logout / Sign Out Button */}
        {onLogout && (
          <button
            onClick={onLogout}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '5px',
              padding: '5px 9px',
              background: '#f8fafc',
              border: '1px solid #cbd5e1',
              borderRadius: '6px',
              color: '#64748b',
              fontSize: '11px',
              fontWeight: 700,
              cursor: 'pointer',
              boxShadow: 'var(--shadow-sm)',
              transition: 'all 0.15s ease'
            }}
            title="Sign out of FactoryMind AI session"
          >
            <LogOut size={13} color="#dc2626" />
            <span>Sign Out</span>
          </button>
        )}
      </div>
    </header>
  );
}
