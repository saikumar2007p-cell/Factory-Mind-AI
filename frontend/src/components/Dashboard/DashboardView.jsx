import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  BrainCircuit,
  Clock,
  ArrowRight,
  TrendingDown,
  Wrench,
  Sparkles,
  ShieldCheck,
  CheckSquare,
  UserCheck,
  Layers,
  TrendingUp
} from 'lucide-react';
import { getWorkOrdersSummary, getFleetSummary, getLearningOverview } from '../../services/api';

export default function DashboardView({
  fleetSummary,
  machines,
  alerts,
  simulationState,
  latestLiveFrame,
  onSelectMachine,
  onNavigateTab,
  onAcknowledgeAlert,
  onRunDiagnostics,
  diagnosticsLoading,
  latestDiagnosis
}) {
  const [woSummary, setWoSummary] = useState(null);
  const [fleetIntel, setFleetIntel] = useState(null);
  const [learningOverview, setLearningOverview] = useState(null);

  useEffect(() => {
    getWorkOrdersSummary().then(res => setWoSummary(res)).catch(() => {});
    getFleetSummary().then(res => setFleetIntel(res)).catch(() => {});
    getLearningOverview().then(res => setLearningOverview(res)).catch(() => {});
  }, [latestLiveFrame]);
  const total = fleetSummary?.total_machines || machines.length || 100;
  const operational = fleetSummary?.operational_count || (machines.filter(m => m.status === 'OPERATIONAL').length);
  const warning = fleetSummary?.warning_count || (machines.filter(m => m.status === 'WARNING' || m.status === 'MONITORING').length);
  const critical = fleetSummary?.critical_count || (machines.filter(m => m.status === 'CRITICAL').length);

  const activeAlerts = alerts.filter(a => a.status === 'ACTIVE');
  const sim = latestLiveFrame?.prediction || {};
  const currentCycle = latestLiveFrame?.cycle || simulationState?.current_cycle || 1;
  const maxCycle = simulationState?.max_cycle || 192;
  const progressPercent = Math.min(100, Math.round((currentCycle / maxCycle) * 100));

  const unit1 = machines.find(m => m.unit_number === 1 || m.id === 1);
  const healthIndex = sim.health_index != null ? sim.health_index : (unit1?.health_score != null ? unit1.health_score : null);
  const rulEstimate = sim.rul_estimate != null ? sim.rul_estimate : (unit1?.current_rul != null ? unit1.current_rul : null);
  const riskLevel = sim.risk_level || unit1?.risk_level || 'NORMAL';
  const anomalyScore = sim.anomaly_score != null ? sim.anomaly_score : null;

  const getStatusBadge = (lvl) => {
    switch (lvl) {
      case 'CRITICAL': return <span className="badge badge-critical"><span className="status-dot dot-critical" />Critical</span>;
      case 'WARNING':
      case 'MONITOR': return <span className="badge badge-warning"><span className="status-dot dot-warning" />Warning</span>;
      default: return <span className="badge badge-normal"><span className="status-dot dot-normal" />Running</span>;
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h2 className="page-title">Factory Operations Dashboard</h2>
        <p className="page-description">Real-time prognostic health, fleet degradation trends, and active maintenance alarms.</p>
      </div>

      {/* Top Level Fleet Summary Metrics Row */}
      <div className="metrics-row">
        {/* Total Machines */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Monitored Fleet</span>
            <Cpu size={18} color="var(--text-muted)" />
          </div>
          <div className="metric-value">{total}</div>
          <div className="metric-sub">NASA C-MAPSS Turbofan Units</div>
        </div>

        {/* Running / Healthy */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Normal / Running</span>
            <CheckCircle2 size={18} color="var(--status-normal)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--status-normal)' }}>{operational}</div>
          <div className="metric-sub">Nominal baseline operation</div>
        </div>

        {/* Warning / Degrading */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Attention Required</span>
            <AlertTriangle size={18} color="var(--status-warning)" />
          </div>
          <div className="metric-value" style={{ color: warning > 0 ? 'var(--status-warning)' : 'var(--text-primary)' }}>
            {warning}
          </div>
          <div className="metric-sub">{warning > 0 ? 'Sensor drift or thermal rise' : 'Zero elevated warnings'}</div>
        </div>

        {/* Active Alarms */}
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Active Alarms</span>
            <Activity size={18} color="var(--status-critical)" />
          </div>
          <div className="metric-value" style={{ color: activeAlerts.length > 0 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
            {activeAlerts.length}
          </div>
          <div className="metric-sub">{activeAlerts.length > 0 ? 'Requires operator acknowledgement' : 'All systems clear'}</div>
        </div>
      </div>

      {/* Live Replay Simulation Stream Banner */}
      <div className="card" style={{ marginBottom: '24px', borderLeft: '4px solid #2563eb' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span className="badge badge-ai">
                <Sparkles size={12} />
                Live Prognostic Stream
              </span>
              <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Turbofan Engine #001 (CF6-80C2)
              </span>
              {getStatusBadge(riskLevel)}
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
              Deterministic trajectory playback from C-MAPSS dataset. Stage 2 ML inference evaluated cycle-by-cycle.
            </div>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onSelectMachine(1)}
          >
            Open Machine Telemetry
            <ArrowRight size={14} />
          </button>
        </div>

        {/* Live Gauges & Progression */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid var(--border-subtle)' }}>
          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Current Trajectory Cycle
            </div>
            <div className="mono" style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px' }}>
              {currentCycle} <span style={{ fontSize: '13px', color: 'var(--text-muted)', fontWeight: 400 }}>/ {maxCycle} cycles</span>
            </div>
            <div className="progress-bar-bg" style={{ marginTop: '8px' }}>
              <div className="progress-bar-fill fill-normal" style={{ width: `${progressPercent}%` }} />
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Estimated Remaining Life (RUL)
            </div>
            <div className="mono" style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', color: rulEstimate != null && rulEstimate < 30 ? 'var(--status-warning)' : 'var(--text-primary)' }}>
              {rulEstimate != null ? (
                <>
                  {rulEstimate.toFixed(1)} <span style={{ fontSize: '13px', fontWeight: 400 }}>cycles</span>
                </>
              ) : (
                <span style={{ fontSize: '14px', color: 'var(--text-muted)' }}>RUL: UNAVAILABLE</span>
              )}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              LightGBM Prognostics Model
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              Composite Health Index
            </div>
            <div className="mono" style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', color: healthIndex != null && healthIndex < 60 ? 'var(--status-warning)' : 'var(--status-normal)' }}>
              {healthIndex != null ? `${healthIndex.toFixed(1)}%` : 'UNAVAILABLE'}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '4px' }}>
              {anomalyScore != null ? `Anomaly Score: ${anomalyScore.toFixed(4)}` : 'Anomaly Score: Baseline'}
            </div>
          </div>

          <div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 600 }}>
              AI Diagnostics
            </div>
            <button
              className="btn btn-primary btn-sm"
              style={{ marginTop: '4px', width: '100%' }}
              onClick={() => onRunDiagnostics(1)}
              disabled={diagnosticsLoading}
            >
              <BrainCircuit size={14} />
              {diagnosticsLoading ? 'Analyzing...' : 'Generate Gemini RCA'}
            </button>
          </div>
        </div>
      </div>

      {/* Maintenance Operations Closed-Loop Overview */}
      <div className="card" style={{ marginBottom: '24px', padding: '14px 18px', background: 'var(--bg-card-secondary)', border: '1px solid var(--border-subtle)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Wrench size={18} color="var(--color-primary)" />
            <div>
              <span style={{ fontSize: '14px', fontWeight: 700 }}>Closed-Loop Maintenance Operations</span>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)', marginLeft: '8px' }}>
                Traceable action queue from telemetry to verified repair
              </span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
            <div style={{ display: 'flex', gap: '14px', fontSize: '12px' }}>
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Open: </span>
                <strong className="mono">{woSummary?.open_count ?? 0}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--status-warning)' }}>High Priority: </span>
                <strong className="mono">{woSummary?.high_priority_count ?? 0}</strong>
              </div>
              <div>
                <span style={{ color: '#2563eb' }}>In Progress: </span>
                <strong className="mono">{woSummary?.in_progress_count ?? 0}</strong>
              </div>
              <div>
                <span style={{ color: 'var(--status-critical)' }}>Verification Req: </span>
                <strong className="mono">{woSummary?.verification_required_count ?? 0}</strong>
              </div>
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigateTab('maintenance')}
            >
              Open Work Orders
              <ArrowRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Active Alarms & Grounded AI Intelligence */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {/* Active Alarms Ledger */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertTriangle size={18} color="var(--status-warning)" />
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Active Degradation Alarms</h3>
            </div>
            <button
              className="btn btn-secondary btn-sm"
              onClick={() => onNavigateTab('alerts')}
            >
              View All ({alerts.length})
            </button>
          </div>

          {activeAlerts.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px' }}>
              <CheckCircle2 size={32} color="var(--status-normal)" style={{ marginBottom: '8px' }} />
              <div className="empty-title">All Systems Nominal</div>
              <div className="empty-desc">No unacknowledged degradation alarms across the turbofan fleet.</div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {activeAlerts.slice(0, 3).map((a) => (
                <div
                  key={a.id}
                  style={{
                    padding: '12px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: 'var(--bg-card-secondary)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className={`badge badge-${a.risk_level.toLowerCase()}`}>
                        {a.severity}
                      </span>
                      <span style={{ fontSize: '13px', fontWeight: 600 }}>
                        Turbofan #{String(a.machine_id).padStart(3, '0')} (Cycle {a.cycle})
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                      {a.reason}
                    </div>
                  </div>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => onAcknowledgeAlert(a.id)}
                  >
                    Acknowledge
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Latest AI Diagnostic Insight */}
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BrainCircuit size={18} color="var(--status-ai)" />
              <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Grounded AI Diagnostic Insight</h3>
            </div>
            <span className="badge badge-ai">
              {latestDiagnosis?.model_used || 'Gemini 3.6 Flash'}
            </span>
          </div>

          {latestDiagnosis ? (
            <div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                {latestDiagnosis.summary}
              </div>
              <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px', lineHeight: 1.4 }}>
                {latestDiagnosis.risk_explanation}
              </div>

              {latestDiagnosis.evidence && latestDiagnosis.evidence.length > 0 && (
                <div style={{ background: 'var(--bg-card-secondary)', padding: '10px 12px', borderRadius: 'var(--radius-md)', marginBottom: '12px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Observed Sensor Evidence
                  </div>
                  <ul style={{ paddingLeft: '18px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                    {latestDiagnosis.evidence.map((ev, idx) => (
                      <li key={idx} style={{ marginBottom: '2px' }}>{ev}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: '#eff6ff', borderRadius: 'var(--radius-md)', border: '1px solid #bfdbfe' }}>
                <Wrench size={16} color="#2563eb" style={{ flexShrink: 0 }} />
                <div style={{ fontSize: '12px', color: '#1e40af', fontWeight: 500 }}>
                  <strong>Recommended Action:</strong> {latestDiagnosis.recommended_action}
                </div>
              </div>
            </div>
          ) : (
            <div className="empty-state" style={{ padding: '24px' }}>
              <BrainCircuit size={32} color="var(--text-muted)" style={{ marginBottom: '8px' }} />
              <div className="empty-title">No Diagnostics Run Yet</div>
              <div className="empty-desc">Click "Generate Gemini RCA" on any machine to produce evidence-grounded maintenance recommendations.</div>
            </div>
          )}
        </div>
      </div>

      {/* Stage 9 Fleet Intelligence & Predictive Planning Card */}
      <div className="card" style={{ marginBottom: '24px', padding: '20px', borderLeft: '4px solid #38bdf8' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <Layers size={18} color="#38bdf8" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>
                Fleet Intelligence & Predictive Planning
              </h3>
              <span className="badge" style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', fontSize: '11px', fontWeight: 600 }}>
                Stage 9 Active
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
              Plant-wide prognostic coverage, subsystem defect analytics, and deterministic maintenance planning priorities.
            </p>
          </div>

          <button
            className="btn btn-primary btn-sm"
            onClick={() => onNavigateTab && onNavigateTab('fleet')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            View Fleet Intelligence →
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
          <div style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Healthy Fleet</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-normal)', marginTop: '2px' }}>
              {fleetIntel?.healthy_count ?? operational} / {total}
            </div>
          </div>

          <div style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Critical Risk</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: (fleetIntel?.critical_count || critical) > 0 ? 'var(--status-critical)' : 'var(--text-primary)', marginTop: '2px' }}>
              {fleetIntel?.critical_count ?? critical} units
            </div>
          </div>

          <div style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Attention Required</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: (fleetIntel?.warning_count || warning) > 0 ? 'var(--status-warning)' : 'var(--text-primary)', marginTop: '2px' }}>
              {fleetIntel?.warning_count ?? warning} units
            </div>
          </div>

          <div style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Active Workload</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#c084fc', marginTop: '2px' }}>
              {fleetIntel?.active_work_orders ?? (woSummary ? (woSummary.open_count + woSummary.assigned_count + woSummary.in_progress_count + woSummary.verification_required_count) : 0)} orders
            </div>
          </div>
        </div>
      </div>

      {/* Stage 10 Continuous Learning & Executive Intelligence Card */}
      <div className="card" style={{ marginBottom: '24px', padding: '20px', borderLeft: '4px solid #c084fc' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <TrendingUp size={18} color="#c084fc" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>
                Continuous Learning & Executive Intelligence
              </h3>
              <span className="badge" style={{ background: 'rgba(192, 132, 252, 0.15)', color: '#c084fc', fontSize: '11px', fontWeight: 600 }}>
                Stage 10 Active
              </span>
            </div>
            <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-muted)' }}>
              Empirical verification outcomes, recurring defect pattern recognition, and telemetry recovery feedback.
            </p>
          </div>

          <button
            className="btn btn-primary btn-sm"
            onClick={() => onNavigateTab && onNavigateTab('learning')}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', background: '#9333ea', borderColor: '#a855f7' }}
          >
            View Learning Intelligence →
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '12px', marginTop: '16px', paddingTop: '16px', borderTop: '1px solid rgba(255, 255, 255, 0.06)' }}>
          <div style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Verified Outcomes</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#34d399', marginTop: '2px' }}>
              {learningOverview?.executive_summary?.verified_outcomes_count ?? 0} ({learningOverview?.executive_summary?.resolved_count ?? 0} resolved)
            </div>
          </div>

          <div style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Recurring Patterns</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: (learningOverview?.recurring_count || 0) > 0 ? '#f87171' : 'var(--text-primary)', marginTop: '2px' }}>
              {learningOverview?.recurring_count ?? 0} detected
            </div>
          </div>

          <div style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Learning Signals</div>
            <div style={{ fontSize: '18px', fontWeight: 700, color: '#fbbf24', marginTop: '2px' }}>
              {learningOverview?.learning_signals_count ?? 0} active
            </div>
          </div>

          <div style={{ padding: '8px 12px', background: 'rgba(255, 255, 255, 0.02)', borderRadius: '6px' }}>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>Effectiveness</div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-secondary)', marginTop: '4px' }}>
              {learningOverview?.executive_summary?.maintenance_effectiveness_label || 'Awaiting verified data'}
            </div>
          </div>
        </div>
      </div>

      {/* Fleet Overview Quick Table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Turbofan Fleet Registry (C-MAPSS FD001)</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Showing 10 of {total} registered turbofan units.</p>
          </div>
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => onNavigateTab('machines')}
          >
            View All Machines
            <ArrowRight size={14} />
          </button>
        </div>

        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Unit #</th>
                <th>Engine Name</th>
                <th>Status</th>
                <th>Location</th>
                <th>Current Cycle</th>
                <th>Estimated RUL</th>
                <th>Health Index</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {machines.slice(0, 10).map((m) => {
                const rul = m.latest_rul !== undefined && m.latest_rul !== null ? m.latest_rul.toFixed(1) : '--';
                const health = m.latest_health_index !== undefined && m.latest_health_index !== null ? m.latest_health_index.toFixed(1) : '100.0';
                return (
                  <tr key={m.id}>
                    <td className="mono" style={{ fontWeight: 600 }}>#{String(m.unit_number).padStart(3, '0')}</td>
                    <td>{m.name}</td>
                    <td>{getStatusBadge(m.latest_risk_level || m.status)}</td>
                    <td>{m.location}</td>
                    <td className="mono">{m.current_cycle}</td>
                    <td className="mono" style={{ fontWeight: 600 }}>{rul} cycles</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div className="progress-bar-bg" style={{ width: '60px' }}>
                          <div
                            className={`progress-bar-fill ${parseFloat(health) < 60 ? 'fill-warning' : 'fill-normal'}`}
                            style={{ width: `${Math.min(100, parseFloat(health))}%` }}
                          />
                        </div>
                        <span className="mono" style={{ fontSize: '12px' }}>{health}%</span>
                      </div>
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => onSelectMachine(m.id)}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
