import React, { useState, useEffect } from 'react';
import {
  ArrowLeft,
  BrainCircuit,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  Wrench,
  Sparkles,
  RefreshCw,
  ShieldCheck,
  UserCheck,
  Plus
} from 'lucide-react';
import {
  getMachine,
  getTelemetry,
  getLatestPrediction,
  getPredictionHistory,
  getMachineAlerts,
  getDiagnostics,
  getMachineWorkOrders,
  createWorkOrder,
  getMachineMaintenanceHistory,
  getLearningSignals,
  getCached
} from '../../services/api';

import BehavioralChangeFeed from './BehavioralChangeFeed';


export default function MachineDetailView({
  machineId,
  onBack,
  onRunDiagnostics,
  diagnosticsLoading,
  latestDiagnosis,
  userRole = 'ADMIN'
}) {
  const [machine, setMachine] = useState(() => getCached(`/machines/${machineId}`));
  const [telemetry, setTelemetry] = useState(() => getCached(`/telemetry/${machineId}?limit=30`)?.telemetry || []);
  const [prediction, setPrediction] = useState(() => getCached(`/predictions/${machineId}/latest`));
  const [predHistory, setPredHistory] = useState(() => getCached(`/predictions/${machineId}/history?limit=50`) || []);
  const [alerts, setAlerts] = useState(() => getCached(`/alerts/machine/${machineId}`) || []);
  const [workOrders, setWorkOrders] = useState(() => getCached(`/work-orders/machine/${machineId}`) || []);
  const [maintHistory, setMaintHistory] = useState(null);
  const [machineSignals, setMachineSignals] = useState([]);
  const [loading, setLoading] = useState(() => !getCached(`/machines/${machineId}`));
  const [activeTab, setActiveTab] = useState('telemetry'); // telemetry, trends, alerts, maintenance, learning
  const [selectedSensor, setSelectedSensor] = useState('s_4'); // T50 default

  useEffect(() => {
    async function loadData() {
      if (!getCached(`/machines/${machineId}`)) {
        setLoading(true);
      }
      try {
        const [mRes, tRes, pRes, hRes, aRes, wRes, histRes, sigRes] = await Promise.allSettled([
          getMachine(machineId),
          getTelemetry(machineId, 30),
          getLatestPrediction(machineId),
          getPredictionHistory(machineId, 50),
          getMachineAlerts(machineId),
          getMachineWorkOrders(machineId),
          getMachineMaintenanceHistory(machineId),
          getLearningSignals()
        ]);

        if (mRes.status === 'fulfilled') setMachine(mRes.value);
        if (tRes.status === 'fulfilled') setTelemetry(tRes.value.telemetry || []);
        if (pRes.status === 'fulfilled') setPrediction(pRes.value);
        if (hRes.status === 'fulfilled') setPredHistory(hRes.value || []);
        if (aRes.status === 'fulfilled') setAlerts(aRes.value || []);
        if (wRes.status === 'fulfilled') setWorkOrders(wRes.value || []);
        if (histRes.status === 'fulfilled' && histRes.value && histRes.value.length > 0) {
          setMaintHistory(histRes.value[0]);
        }
        if (sigRes.status === 'fulfilled' && sigRes.value?.signals) {
          const matched = sigRes.value.signals.filter(s => s.entity_id === machineId || (s.source_records?.work_orders && s.source_records.work_orders.some(wid => (wRes.value || []).some(w => w.id === wid))));
          setMachineSignals(matched);
        }
      } catch (err) {
        console.error('Failed loading machine details', err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [machineId]);

  const latestTel = telemetry.length > 0 ? telemetry[telemetry.length - 1] : null;
  const currentPred = prediction || {};
  const currentCycle = latestTel?.cycle || machine?.current_cycle || 1;
  const rul = currentPred.rul_estimate !== undefined ? currentPred.rul_estimate.toFixed(1) : (machine?.latest_rul ? machine.latest_rul.toFixed(1) : '127.5');
  const health = currentPred.health_index !== undefined ? currentPred.health_index.toFixed(1) : (machine?.latest_health_index ? machine.latest_health_index.toFixed(1) : '99.5');
  const risk = currentPred.risk_level || machine?.latest_risk_level || 'NORMAL';
  const riskScore = currentPred.risk_score !== undefined ? currentPred.risk_score.toFixed(1) : '0.5';

  const sensorMeta = [
    { id: 's_2', name: 'T24', desc: 'LPC Outlet Temperature', subsystem: 'Low Pressure Compressor', unit: '°R', baseline: 642.0 },
    { id: 's_3', name: 'T30', desc: 'HPC Outlet Temperature', subsystem: 'High Pressure Compressor', unit: '°R', baseline: 1587.0 },
    { id: 's_4', name: 'T50', desc: 'LPT Outlet Temperature', subsystem: 'Low Pressure Turbine', unit: '°R', baseline: 1403.2 },
    { id: 's_7', name: 'P30', desc: 'HPC Outlet Pressure', subsystem: 'High Pressure Compressor', unit: 'psia', baseline: 554.0 },
    { id: 's_8', name: 'Nf', desc: 'Physical Fan Speed', subsystem: 'Fan', unit: 'rpm', baseline: 2388.0 },
    { id: 's_9', name: 'Nc', desc: 'Physical Core Speed', subsystem: 'Core Engine', unit: 'rpm', baseline: 9046.0 },
    { id: 's_11', name: 'Ps30', desc: 'Static HPC Pressure', subsystem: 'High Pressure Compressor', unit: 'psia', baseline: 47.4 },
    { id: 's_12', name: 'phi', desc: 'Fuel Flow Ratio', subsystem: 'Fuel System', unit: 'pps/psi', baseline: 521.8 },
    { id: 's_13', name: 'NRf', desc: 'Corrected Fan Speed', subsystem: 'Fan', unit: 'rpm', baseline: 2388.0 },
    { id: 's_14', name: 'NRc', desc: 'Corrected Core Speed', subsystem: 'Core Engine', unit: 'rpm', baseline: 8135.0 },
    { id: 's_15', name: 'BPR', desc: 'Bypass Ratio', subsystem: 'Bypass Duct', unit: '--', baseline: 8.41 },
    { id: 's_17', name: 'htBleed', desc: 'Bleed Enthalpy', subsystem: 'Bleed Air System', unit: '--', baseline: 391.5 },
    { id: 's_20', name: 'W31', desc: 'HPT Coolant Bleed', subsystem: 'High Pressure Turbine', unit: 'lbm/s', baseline: 39.0 },
    { id: 's_21', name: 'W32', desc: 'LPT Coolant Bleed', subsystem: 'Low Pressure Turbine', unit: 'lbm/s', baseline: 23.4 }
  ];

  const getStatusBadge = (lvl) => {
    switch (lvl) {
      case 'CRITICAL': return <span className="badge badge-critical"><span className="status-dot dot-critical" />Critical Risk</span>;
      case 'WARNING':
      case 'MONITOR': return <span className="badge badge-warning"><span className="status-dot dot-warning" />Warning / Monitoring</span>;
      default: return <span className="badge badge-normal"><span className="status-dot dot-normal" />Operational</span>;
    }
  };

  // Render SVG Trend Chart for selected sensor
  const renderTrendChart = () => {
    if (!telemetry || telemetry.length < 2) {
      return (
        <div className="empty-state" style={{ padding: '24px' }}>
          <Activity size={32} color="var(--text-muted)" style={{ marginBottom: '8px' }} />
          <div className="empty-title">Insufficient Historical Points</div>
          <div className="empty-desc">Telemetry data from additional cycles is needed to plot trend trajectory.</div>
        </div>
      );
    }

    const points = telemetry.map(t => ({ cycle: t.cycle, val: t[selectedSensor] || 0 }));
    const minVal = Math.min(...points.map(p => p.val));
    const maxVal = Math.max(...points.map(p => p.val));
    const range = (maxVal - minVal) || 1;

    const width = 640;
    const height = 180;
    const padding = 30;

    const svgPoints = points.map((p, idx) => {
      const x = padding + (idx / (points.length - 1)) * (width - 2 * padding);
      const y = height - padding - ((p.val - minVal) / range) * (height - 2 * padding);
      return `${x},${y}`;
    }).join(' ');

    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Sensor Trajectory: {sensorMeta.find(s => s.id === selectedSensor)?.name} ({sensorMeta.find(s => s.id === selectedSensor)?.desc})
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            Min: {minVal.toFixed(2)} | Max: {maxVal.toFixed(2)} {sensorMeta.find(s => s.id === selectedSensor)?.unit}
          </div>
        </div>

        <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} style={{ background: 'var(--bg-card-secondary)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          {/* Grid lines */}
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="#e2e8f0" strokeDasharray="3 3" />
          <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="#e2e8f0" strokeDasharray="3 3" />
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="#e2e8f0" />

          {/* Polyline */}
          <polyline
            fill="none"
            stroke="#2563eb"
            strokeWidth="2.5"
            points={svgPoints}
          />

          {/* Data dots */}
          {points.map((p, idx) => {
            const x = padding + (idx / (points.length - 1)) * (width - 2 * padding);
            const y = height - padding - ((p.val - minVal) / range) * (height - 2 * padding);
            return (
              <circle
                key={idx}
                cx={x}
                cy={y}
                r="3"
                fill="#ffffff"
                stroke="#2563eb"
                strokeWidth="2"
              />
            );
          })}
        </svg>
      </div>
    );
  };

  return (
    <div>
      {/* Top Action Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onBack}
        >
          <ArrowLeft size={14} />
          Back to Machine Fleet
        </button>

        <button
          className="btn btn-primary"
          onClick={() => onRunDiagnostics(machineId)}
          disabled={diagnosticsLoading}
        >
          <BrainCircuit size={16} />
          {diagnosticsLoading ? 'Reasoning with Gemini...' : 'Run Gemini AI Diagnosis'}
        </button>
      </div>

      {/* Machine Header Card */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
              <span className="mono" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-muted)' }}>
                UNIT #{machine?.unit_number ? String(machine.unit_number).padStart(3, '0') : String(machineId).padStart(3, '0')}
              </span>
              <h2 style={{ fontSize: '20px', fontWeight: 700 }}>{machine?.name || `Turbofan Engine #${machineId}`}</h2>
              {getStatusBadge(risk)}

              {/* Telemetry Freshness State Badge */}
              <span
                style={{
                  fontSize: '11px',
                  fontWeight: 600,
                  padding: '2px 8px',
                  borderRadius: '12px',
                  backgroundColor: (machine?.telemetry_state || 'CURRENT') === 'CURRENT' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                  color: (machine?.telemetry_state || 'CURRENT') === 'CURRENT' ? '#10b981' : '#f59e0b',
                  border: `1px solid ${(machine?.telemetry_state || 'CURRENT') === 'CURRENT' ? 'rgba(16, 185, 129, 0.3)' : 'rgba(245, 158, 11, 0.3)'}`
                }}
              >
                Stream: {machine?.telemetry_state || 'CURRENT'}
              </span>

              {/* Prediction Confidence Badge */}
              {prediction?.confidence_level && (
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: '12px',
                    backgroundColor: prediction.confidence_level === 'HIGH' ? 'rgba(99, 102, 241, 0.15)' : (prediction.confidence_level === 'MEDIUM' ? 'rgba(245, 158, 11, 0.15)' : 'rgba(239, 68, 68, 0.15)'),
                    color: prediction.confidence_level === 'HIGH' ? '#818cf8' : (prediction.confidence_level === 'MEDIUM' ? '#fbbf24' : '#f87171'),
                    border: `1px solid ${prediction.confidence_level === 'HIGH' ? 'rgba(99, 102, 241, 0.3)' : 'rgba(239, 68, 68, 0.3)'}`
                  }}
                  title={prediction.confidence_reason || 'ML Confidence Diagnostics'}
                >
                  Confidence: {prediction.confidence_level} ({Math.round((prediction.confidence_score || 0.9) * 100)}%)
                </span>
              )}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              {machine?.machine_type || 'Turbofan Engine CF6-80C2'} &bull; {machine?.location || 'Test Cell 1'} &bull; Cycle <strong className="mono">{currentCycle}</strong>
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Estimated RUL</div>
              <div className="mono" style={{ fontSize: '22px', fontWeight: 700, color: parseFloat(rul) < 30 ? 'var(--status-warning)' : 'var(--text-primary)' }}>
                {rul} <span style={{ fontSize: '12px', fontWeight: 400 }}>cycles</span>
              </div>
            </div>
            <div style={{ width: '1px', background: 'var(--border-subtle)', margin: '0 4px' }} />
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>Health Index</div>
              <div className="mono" style={{ fontSize: '22px', fontWeight: 700, color: parseFloat(health) < 60 ? 'var(--status-warning)' : 'var(--status-normal)' }}>
                {health}%
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Grounded Gemini Diagnostic Report (If available) */}
      {latestDiagnosis && (
        <div className="card" style={{ marginBottom: '20px', borderLeft: '4px solid #2563eb' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BrainCircuit size={18} color="var(--status-ai)" />
              <h3 style={{ fontSize: '16px', fontWeight: 700 }}>AI Root Cause Analysis & Diagnostic Report</h3>
            </div>
            <span className="badge badge-ai">
              {latestDiagnosis.source === 'gemini' ? `Google ${latestDiagnosis.model_used}` : 'Deterministic Grounded Fallback'}
            </span>
          </div>

          <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
            {latestDiagnosis.summary}
          </div>
          <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '14px', lineHeight: 1.5 }}>
            {latestDiagnosis.risk_explanation}
          </div>

          {/* Evidence bullet points */}
          {latestDiagnosis.evidence && latestDiagnosis.evidence.length > 0 && (
            <div style={{ background: 'var(--bg-card-secondary)', padding: '12px 14px', borderRadius: 'var(--radius-md)', marginBottom: '14px' }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '6px' }}>
                Observed Sensor Evidence (NASA C-MAPSS)
              </div>
              <ul style={{ paddingLeft: '18px', fontSize: '13px', color: 'var(--text-secondary)' }}>
                {latestDiagnosis.evidence.map((ev, idx) => (
                  <li key={idx} style={{ marginBottom: '4px' }}>{ev}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Recommended Work Order */}
          <div style={{ padding: '12px 14px', background: '#eff6ff', borderRadius: 'var(--radius-md)', border: '1px solid #bfdbfe', display: 'flex', alignItems: 'flex-start', gap: '10px' }}>
            <Wrench size={18} color="#2563eb" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#1e40af' }}>
                Prescriptive Maintenance Action:
              </div>
              <div style={{ fontSize: '13px', color: '#1e3a8a', marginTop: '2px' }}>
                {latestDiagnosis.recommended_action}
              </div>
            </div>
          </div>

          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px' }}>
            <strong>Engineering Notice:</strong> {latestDiagnosis.limitations}
          </div>
        </div>
      )}

      {/* Tabs Menu */}
      <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-subtle)', marginBottom: '16px', flexWrap: 'wrap' }}>
        {[
          { id: 'telemetry', label: 'Sensor Telemetry (21 Channels)' },
          { id: 'trends', label: 'Degradation Trends' },
          { id: 'drift', label: 'Drift & Behavioral Shifts' },
          { id: 'alerts', label: `Alarms & History (${alerts.length})` },
          { id: 'maintenance', label: `Work Orders (${workOrders.length})` },
          { id: 'learning', label: 'Learning & Outcomes' }
        ].map((tab) => (
          <button
            key={tab.id}
            className={`btn btn-sm ${activeTab === tab.id ? 'btn-primary' : 'btn-secondary'}`}
            style={{ borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0', borderBottom: 'none' }}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>


      {/* Tab: Real Sensor Telemetry Table */}
      {activeTab === 'telemetry' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Active Turbofan Core Measurements (Cycle {currentCycle})</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Real values derived from C-MAPSS dataset</span>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Sensor</th>
                  <th>Measurement</th>
                  <th>Subsystem</th>
                  <th>Observed Value</th>
                  <th>Baseline</th>
                  <th>Delta</th>
                  <th>Trend</th>
                </tr>
              </thead>
              <tbody>
                {sensorMeta.map((s) => {
                  const val = latestTel ? latestTel[s.id] : null;
                  const valNum = val !== null && val !== undefined ? parseFloat(val) : s.baseline;
                  const delta = valNum - s.baseline;
                  const isUp = delta > 0.05;
                  const isDown = delta < -0.05;

                  return (
                    <tr key={s.id}>
                      <td className="mono" style={{ fontWeight: 600 }}>{s.name}</td>
                      <td>{s.desc}</td>
                      <td><span className="badge badge-offline">{s.subsystem}</span></td>
                      <td className="mono" style={{ fontWeight: 700 }}>
                        {valNum.toFixed(2)} <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{s.unit}</span>
                      </td>
                      <td className="mono" style={{ color: 'var(--text-muted)' }}>{s.baseline.toFixed(2)}</td>
                      <td className="mono" style={{ color: Math.abs(delta) > 1.0 ? 'var(--status-warning)' : 'var(--text-secondary)' }}>
                        {delta > 0 ? `+${delta.toFixed(2)}` : delta.toFixed(2)}
                      </td>
                      <td>
                        {isUp ? (
                          <span style={{ color: '#d97706', display: 'flex', alignItems: 'center', gap: '2px', fontSize: '12px' }}>
                            <TrendingUp size={14} /> Rising
                          </span>
                        ) : isDown ? (
                          <span style={{ color: '#2563eb', display: 'flex', alignItems: 'center', gap: '2px', fontSize: '12px' }}>
                            <TrendingDown size={14} /> Dropping
                          </span>
                        ) : (
                          <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '2px', fontSize: '12px' }}>
                            <Minus size={14} /> Stable
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Sensor Degradation Trend Chart */}
      {activeTab === 'trends' && (
        <div className="card">
          <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', flexWrap: 'wrap' }}>
            {sensorMeta.slice(0, 8).map((s) => (
              <button
                key={s.id}
                className={`btn btn-sm ${selectedSensor === s.id ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setSelectedSensor(s.id)}
              >
                {s.name} ({s.desc})
              </button>
            ))}
          </div>
          {renderTrendChart()}
        </div>
      )}

      {/* Tab: Alerts & History */}
      {activeTab === 'alerts' && (
        <div className="card">
          <h3 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '12px' }}>Engine Degradation Event Log</h3>
          {alerts.length === 0 ? (
            <div className="empty-state">
              <CheckCircle2 size={32} color="var(--status-normal)" style={{ marginBottom: '8px' }} />
              <div className="empty-title">Zero Active Alarms</div>
              <div className="empty-desc">No degradation threshold breaches recorded for this engine.</div>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Alarm ID</th>
                    <th>Cycle</th>
                    <th>Severity</th>
                    <th>Reason</th>
                    <th>Status</th>
                    <th>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((a) => (
                    <tr key={a.id}>
                      <td className="mono">#{a.id}</td>
                      <td className="mono">{a.cycle}</td>
                      <td><span className={`badge badge-${a.risk_level.toLowerCase()}`}>{a.severity}</span></td>
                      <td>{a.reason}</td>
                      <td><span className="badge badge-normal">{a.status}</span></td>
                      <td className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{a.created_at || 'Recent'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Maintenance & Work Orders */}
      {activeTab === 'maintenance' && (
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <div>
              <h3 style={{ fontSize: '14px', fontWeight: 600 }}>Active & Historical Work Orders for Unit #{machine?.unit_number ? String(machine.unit_number).padStart(3, '0') : machineId}</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Traceable maintenance actions generated from ML anomalies and Gemini diagnostics.</p>
            </div>
            {userRole === 'VIEWER' ? (
              <div style={{ padding: '6px 12px', background: 'rgba(255,255,255,0.05)', borderRadius: '6px', fontSize: '11px', color: 'var(--text-muted)', border: '1px solid rgba(255,255,255,0.1)' }}>
                👁️ Viewer Mode (Read-Only)
              </div>
            ) : (
              <button
                className="btn btn-primary btn-sm"
                onClick={async () => {
                  try {
                    const res = await createWorkOrder({
                      machine_id: machineId,
                      title: `Inspection & Maintenance - Unit #${machineId}`,
                      recommended_action: latestDiagnosis?.recommended_action || 'Inspect high-pressure compressor stages and replace thermal gaskets.',
                      affected_subsystem: 'Turbofan Core',
                      priority: risk === 'CRITICAL' ? 'CRITICAL' : (risk === 'WARNING' ? 'HIGH' : 'MEDIUM'),
                      risk_level: risk
                    });
                    alert(`Work Order ${res.work_order_code} successfully created!`);
                    const wRes = await getMachineWorkOrders(machineId);
                    setWorkOrders(wRes || []);
                  } catch (err) {
                    const msg = err.status === 403 ? 'Permission denied — Operator or Admin authorization required.' : (err.detail || err.message);
                    alert(`Failed to create work order: ${msg}`);
                  }
                }}
              >
                <Plus size={14} /> Create Work Order
              </button>
            )}
          </div>

          {workOrders.length === 0 ? (
            <div className="empty-state">
              <CheckCircle2 size={32} color="var(--status-normal)" style={{ marginBottom: '8px' }} />
              <div className="empty-title">No Active Work Orders</div>
              <div className="empty-desc">No maintenance procedures currently dispatched for this machine unit.</div>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Order Code</th>
                    <th>Subsystem</th>
                    <th>Priority</th>
                    <th>Status</th>
                    <th>Prescriptive Action</th>
                    <th>Assigned To</th>
                    <th>Verification</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {workOrders.map((wo) => (
                    <tr key={wo.id}>
                      <td className="mono" style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{wo.work_order_code}</td>
                      <td><span className="badge badge-offline">{wo.affected_subsystem}</span></td>
                      <td>
                        <span className={`badge ${wo.priority === 'CRITICAL' ? 'badge-critical' : (wo.priority === 'HIGH' ? 'badge-warning' : 'badge-normal')}`}>
                          {wo.priority}
                        </span>
                      </td>
                      <td><span className="badge badge-normal">{wo.status}</span></td>
                      <td style={{ maxWidth: '300px', fontSize: '12px' }}>{wo.recommended_action}</td>
                      <td style={{ fontSize: '12px', fontWeight: wo.assigned_to === 'Unassigned' ? 400 : 600, color: wo.assigned_to === 'Unassigned' ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                        {wo.assigned_to || 'Unassigned'}
                      </td>
                      <td>
                        {wo.verification_status ? (
                          <span className="badge badge-ai">{wo.verification_status}</span>
                        ) : (
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Pending</span>
                        )}
                      </td>
                      <td className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                        {wo.created_at ? new Date(wo.created_at).toLocaleDateString() : 'Recent'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Tab: Continuous Learning & Machine Outcomes */}
      {activeTab === 'learning' && (
        <div className="card animate-fade-in" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div>
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>
                Unit #{machine?.unit_number || machineId} Maintenance History & Empirical Learning
              </h3>
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
                Verified resolution rate, defect recurrence status, and empirical observations.
              </p>
            </div>
            <span className="badge badge-ai">Stage 10 Active</span>
          </div>

          {/* Machine KPIs */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '12px', marginBottom: '20px' }}>
            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>TOTAL ORDERS</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#ffffff', marginTop: '2px' }}>
                {maintHistory?.maintenance_count ?? workOrders.length}
              </div>
            </div>

            <div style={{ background: 'rgba(52, 211, 153, 0.06)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '10px', color: '#34d399' }}>RESOLVED</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
                {maintHistory?.resolved_count ?? 0}
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>RECURRENCE STATUS</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: maintHistory?.recurring_issue_status === 'RECURRING_FAILURE' ? '#f87171' : 'var(--text-primary)', marginTop: '4px' }}>
                {maintHistory?.recurring_issue_status || 'STABLE'}
              </div>
            </div>

            <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px', borderRadius: '6px', textAlign: 'center' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>EFFECTIVENESS</div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: '#38bdf8', marginTop: '4px' }}>
                {maintHistory?.historical_effectiveness || 'UNAVAILABLE'}
              </div>
            </div>
          </div>

          {/* Machine Learning Signals */}
          <div style={{ marginBottom: '16px' }}>
            <h4 style={{ fontSize: '13px', fontWeight: 600, color: '#ffffff', marginBottom: '8px' }}>
              Empirical Observations & Signals for this Machine
            </h4>
            {machineSignals.length > 0 ? (
              <div style={{ display: 'grid', gap: '10px' }}>
                {machineSignals.map(sig => (
                  <div key={sig.signal_id} style={{ background: 'rgba(255, 255, 255, 0.02)', padding: '12px', borderRadius: '6px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                      <span style={{ fontSize: '12px', fontWeight: 600, color: '#ffffff' }}>{sig.observation_title}</span>
                      <span className="badge" style={{ background: 'rgba(192, 132, 252, 0.15)', color: '#c084fc', fontSize: '10px' }}>{sig.confidence_level}</span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{sig.explanation}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ background: 'rgba(255,255,255,0.01)', padding: '16px', borderRadius: '6px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '12px' }}>
                No machine-specific recurring defect signals detected.
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab: Behavioral Change & Drift Detection */}
      {activeTab === 'drift' && (
        <BehavioralChangeFeed machineId={machineId} userRole={userRole} />
      )}
    </div>
  );
}

