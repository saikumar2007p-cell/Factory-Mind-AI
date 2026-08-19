import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  BrainCircuit,
  Wrench,
  ShieldCheck,
  Clock,
  Layers,
  ArrowRight,
  TrendingDown,
  RefreshCw,
  Info,
  Database,
  Search,
  Filter,
  CheckSquare,
  AlertOctagon,
  FileText,
  Sliders,
  Sparkles
} from 'lucide-react';
import {
  getFleetSummary,
  getFleetMachines,
  getFleetRiskDistribution,
  getFleetMaintenanceLoad,
  getFleetSubsystems,
  getFleetAttentionRequired,
  getFleetPlanning
} from '../../services/api';

export default function FleetIntelligenceView({ onSelectMachine, onNavigateTab, searchQuery: propSearchQuery }) {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // API State
  const [summary, setSummary] = useState(null);
  const [riskDist, setRiskDist] = useState(null);
  const [maintenanceLoad, setMaintenanceLoad] = useState(null);
  const [subsystems, setSubsystems] = useState([]);
  const [attentionItems, setAttentionItems] = useState([]);
  const [planningData, setPlanningData] = useState(null);

  // Filter states
  const [planningFilter, setPlanningFilter] = useState('ALL');
  const [internalSearchQuery, setInternalSearchQuery] = useState('');
  const searchQuery = propSearchQuery !== undefined ? propSearchQuery : internalSearchQuery;

  const loadData = async (isRefresh = false, isSilent = false) => {
    if (isSilent) {
      // Background silent update — no spinner toggles to prevent UI flashing or state jumping
    } else if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError(null);

    try {
      const [sumRes, distRes, loadRes, subsRes, attRes, planRes] = await Promise.allSettled([
        getFleetSummary(),
        getFleetRiskDistribution(),
        getFleetMaintenanceLoad(),
        getFleetSubsystems(),
        getFleetAttentionRequired(),
        getFleetPlanning()
      ]);

      if (sumRes.status === 'fulfilled') setSummary(sumRes.value);
      if (distRes.status === 'fulfilled') setRiskDist(distRes.value);
      if (loadRes.status === 'fulfilled') setMaintenanceLoad(loadRes.value);
      if (subsRes.status === 'fulfilled') setSubsystems(subsRes.value?.subsystems || []);
      if (attRes.status === 'fulfilled') setAttentionItems(attRes.value?.items || []);
      if (planRes.status === 'fulfilled') setPlanningData(planRes.value);

    } catch (err) {
      console.error('Error loading fleet intelligence data:', err);
      setError('Unable to load fleet analytics. Please check backend connection.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData(false, false);
    const interval = setInterval(() => loadData(true, true), 10000);
    return () => clearInterval(interval);
  }, []);

  const getRiskBadge = (risk) => {
    switch (risk) {
      case 'CRITICAL':
        return <span className="badge badge-critical"><span className="status-dot dot-critical" />CRITICAL</span>;
      case 'WARNING':
        return <span className="badge badge-warning"><span className="status-dot dot-warning" />WARNING</span>;
      case 'MONITOR':
        return <span className="badge badge-warning" style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#eab308' }}><span className="status-dot" style={{ background: '#eab308' }} />MONITOR</span>;
      case 'NORMAL':
        return <span className="badge badge-normal"><span className="status-dot dot-normal" />NORMAL</span>;
      case 'STALE':
        return <span className="badge" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8' }}><span className="status-dot" style={{ background: '#94a3b8' }} />STALE</span>;
      default:
        return <span className="badge" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8' }}>UNKNOWN</span>;
    }
  };

  const getPlanningBadge = (state) => {
    switch (state) {
      case 'Immediate Attention':
        return <span className="badge badge-critical" style={{ fontWeight: 700 }}>Immediate Attention</span>;
      case 'High Priority':
        return <span className="badge badge-warning" style={{ fontWeight: 700 }}>High Priority</span>;
      case 'Schedule Inspection':
        return <span className="badge" style={{ background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', fontWeight: 600 }}>Schedule Inspection</span>;
      case 'Monitor Closely':
        return <span className="badge" style={{ background: 'rgba(234, 179, 8, 0.15)', color: '#eab308', fontWeight: 600 }}>Monitor Closely</span>;
      case 'Insufficient Data':
        return <span className="badge" style={{ background: 'rgba(148, 163, 184, 0.15)', color: '#94a3b8' }}>Insufficient Data</span>;
      default:
        return <span className="badge badge-normal">No Action Recommended</span>;
    }
  };

  const filteredAttention = (attentionItems || []).filter(item => {
    const q = (searchQuery || '').trim().toLowerCase();
    if (!q) return true;
    const unitStr = String(item.unit_number || item.machine_id);
    const paddedUnit = unitStr.padStart(3, '0');
    return (
      (item.name || '').toLowerCase().includes(q) ||
      unitStr.includes(q) ||
      paddedUnit.includes(q) ||
      `unit ${unitStr}`.includes(q) ||
      `unit #${unitStr}`.includes(q) ||
      `unit #${paddedUnit}`.includes(q) ||
      (item.risk_level || '').toLowerCase().includes(q) ||
      (item.recommended_action || '').toLowerCase().includes(q)
    );
  });

  const filteredPlans = (planningData?.plans || []).filter(plan => {
    const matchesFilter = planningFilter === 'ALL' || plan.planning_state === planningFilter;
    const q = (searchQuery || '').trim().toLowerCase();
    if (!q) return matchesFilter;
    const unitStr = String(plan.unit_number || plan.machine_id);
    const paddedUnit = unitStr.padStart(3, '0');
    const matchesSearch = (
      (plan.machine_name || '').toLowerCase().includes(q) ||
      unitStr.includes(q) ||
      paddedUnit.includes(q) ||
      `unit ${unitStr}`.includes(q) ||
      `unit #${unitStr}`.includes(q) ||
      `unit #${paddedUnit}`.includes(q) ||
      (plan.planning_state || '').toLowerCase().includes(q) ||
      (plan.recommendation_title || '').toLowerCase().includes(q)
    );
    return matchesFilter && matchesSearch;
  });

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* 1. Header & Source Transparency */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h2 className="page-title" style={{ margin: 0 }}>Fleet Intelligence & Predictive Planning</h2>
            <span style={{ fontSize: '11px', padding: '3px 8px', borderRadius: '6px', background: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', fontWeight: 600 }}>
              Stage 9 Active
            </span>
          </div>
          <p className="page-description" style={{ marginTop: '4px' }}>
            Plant-wide prognostic coverage, subsystem reliability defect analytics, and deterministic maintenance planning priorities.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          {/* Data Source Label */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 12px', background: '#ffffff', border: '1px solid #cbd5e1', borderRadius: '8px', fontSize: '12px', boxShadow: 'var(--shadow-sm)' }}>
            <Database size={14} color="#2563eb" />
            <span style={{ color: '#475569', fontWeight: 600 }}>Source:</span>
            <span style={{ color: '#2563eb', fontWeight: 700 }}>NASA C-MAPSS FD001 — Simulation</span>
          </div>

          <button
            className="btn btn-secondary"
            onClick={() => loadData(true)}
            disabled={refreshing}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', padding: '6px 12px' }}
          >
            <RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '8px', color: '#f87171', fontSize: '13px' }}>
          {error}
        </div>
      )}

      {/* 2. Fleet Health KPI Summary Grid */}
      <div className="metrics-row" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))' }}>
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Monitored Fleet</span>
            <Cpu size={16} color="var(--text-muted)" />
          </div>
          <div className="metric-value">{summary?.total_machines ?? 100}</div>
          <div className="metric-sub">NASA C-MAPSS Turbofans</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Normal / Healthy</span>
            <CheckCircle2 size={16} color="var(--status-normal)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--status-normal)' }}>
            {summary?.healthy_count ?? 0}
          </div>
          <div className="metric-sub">Baseline nominal</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Warning / Monitor</span>
            <AlertTriangle size={16} color="var(--status-warning)" />
          </div>
          <div className="metric-value" style={{ color: (summary?.warning_count || 0) > 0 ? 'var(--status-warning)' : 'var(--text-primary)' }}>
            {summary?.warning_count ?? 0}
          </div>
          <div className="metric-sub">Sensor drift observed</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Critical Failure Risk</span>
            <AlertOctagon size={16} color="var(--status-critical)" />
          </div>
          <div className="metric-value" style={{ color: (summary?.critical_count || 0) > 0 ? 'var(--status-critical)' : 'var(--text-primary)' }}>
            {summary?.critical_count ?? 0}
          </div>
          <div className="metric-sub">Imminent intervention</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Stale / Offline</span>
            <Clock size={16} color="#94a3b8" />
          </div>
          <div className="metric-value" style={{ color: '#94a3b8' }}>
            {(summary?.stale_count || 0) + (summary?.missing_data_count || 0)}
          </div>
          <div className="metric-sub">Telemetry feed delayed</div>
        </div>
      </div>

      {/* 3. Predictive Coverage & Maintenance Workload Overview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))', gap: '20px' }}>
        {/* ML & Prognostic Coverage Card */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <BrainCircuit size={18} color="#38bdf8" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>Predictive ML Coverage</h3>
            </div>
            <span style={{ fontSize: '11px', color: '#94a3b8' }}>21-Channel Schema</span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
            <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>ML Compatible</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#38bdf8', marginTop: '4px' }}>
                {summary?.ml_compatible_count ?? 100}
              </div>
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>Complete 21 channels</div>
            </div>

            <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>ML Incompatible</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#94a3b8', marginTop: '4px' }}>
                {summary?.ml_incompatible_count ?? 0}
              </div>
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>Missing channels</div>
            </div>

            <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>RUL Available</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--status-normal)', marginTop: '4px' }}>
                {summary?.rul_available_count ?? 0}
              </div>
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>Active prognostic inference</div>
            </div>

            <div style={{ padding: '12px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.06)' }}>
              <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase' }}>RUL Unavailable</div>
              <div style={{ fontSize: '20px', fontWeight: 700, color: '#94a3b8', marginTop: '4px' }}>
                {summary?.rul_unavailable_count ?? 0}
              </div>
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '2px' }}>Zero fake numbers</div>
            </div>
          </div>
        </div>

        {/* Stage 8 Maintenance Operations Load Card */}
        <div className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wrench size={18} color="#a855f7" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>Maintenance Operations Workload</h3>
            </div>
            {onNavigateTab && (
              <button 
                className="btn btn-secondary" 
                onClick={() => onNavigateTab('maintenance')}
                style={{ fontSize: '11px', padding: '4px 8px' }}
              >
                Go to Maintenance →
              </button>
            )}
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px', textAlign: 'center' }}>
            <div style={{ padding: '10px 4px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>Open</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#60a5fa', marginTop: '4px' }}>
                {maintenanceLoad?.open_count ?? 0}
              </div>
            </div>
            <div style={{ padding: '10px 4px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>Assigned</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#fbbf24', marginTop: '4px' }}>
                {maintenanceLoad?.assigned_count ?? 0}
              </div>
            </div>
            <div style={{ padding: '10px 4px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>In Progress</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#f59e0b', marginTop: '4px' }}>
                {maintenanceLoad?.in_progress_count ?? 0}
              </div>
            </div>
            <div style={{ padding: '10px 4px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>Verif Req</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#c084fc', marginTop: '4px' }}>
                {maintenanceLoad?.verification_required_count ?? 0}
              </div>
            </div>
            <div style={{ padding: '10px 4px', background: 'rgba(255, 255, 255, 0.03)', borderRadius: '8px' }}>
              <div style={{ fontSize: '10px', color: '#94a3b8', textTransform: 'uppercase' }}>Verified</div>
              <div style={{ fontSize: '18px', fontWeight: 700, color: 'var(--status-normal)', marginTop: '4px' }}>
                {maintenanceLoad?.verified_count ?? 0}
              </div>
            </div>
          </div>

          <div style={{ marginTop: '14px', display: 'flex', justifyContent: 'space-between', fontSize: '12px', color: '#94a3b8', borderTop: '1px solid rgba(255, 255, 255, 0.06)', paddingTop: '10px' }}>
            <span>Critical Workload: <strong style={{ color: '#f87171' }}>{maintenanceLoad?.critical_workload ?? 0}</strong></span>
            <span>High Priority: <strong style={{ color: '#fbbf24' }}>{maintenanceLoad?.high_priority_workload ?? 0}</strong></span>
            <span>Verification Backlog: <strong style={{ color: '#c084fc' }}>{maintenanceLoad?.verification_backlog_count ?? 0}</strong></span>
          </div>
        </div>
      </div>

      {/* 4. Fleet Risk Distribution Breakdown */}
      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} color="#60a5fa" />
            <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>Fleet Risk Distribution</h3>
          </div>
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>Total: {summary?.total_machines ?? 100} units</span>
        </div>

        {/* Multi-segment Progress Bar */}
        <div style={{ height: '12px', background: 'rgba(255, 255, 255, 0.05)', borderRadius: '6px', overflow: 'hidden', display: 'flex', marginBottom: '16px' }}>
          <div style={{ width: `${((riskDist?.critical || 0) / (summary?.total_machines || 100)) * 100}%`, background: 'var(--status-critical)' }} title={`Critical: ${riskDist?.critical || 0}`} />
          <div style={{ width: `${((riskDist?.warning || 0) / (summary?.total_machines || 100)) * 100}%`, background: 'var(--status-warning)' }} title={`Warning: ${riskDist?.warning || 0}`} />
          <div style={{ width: `${((riskDist?.monitor || 0) / (summary?.total_machines || 100)) * 100}%`, background: '#eab308' }} title={`Monitor: ${riskDist?.monitor || 0}`} />
          <div style={{ width: `${((riskDist?.normal || 0) / (summary?.total_machines || 100)) * 100}%`, background: 'var(--status-normal)' }} title={`Normal: ${riskDist?.normal || 0}`} />
          <div style={{ width: `${((riskDist?.stale || 0) / (summary?.total_machines || 100)) * 100}%`, background: '#94a3b8' }} title={`Stale: ${riskDist?.stale || 0}`} />
          <div style={{ width: `${((riskDist?.unknown_insufficient || 0) / (summary?.total_machines || 100)) * 100}%`, background: '#475569' }} title={`Insufficient: ${riskDist?.unknown_insufficient || 0}`} />
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap', fontSize: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'var(--status-critical)' }} />
            <span style={{ color: '#cbd5e1' }}>Critical: <strong>{riskDist?.critical ?? 0}</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'var(--status-warning)' }} />
            <span style={{ color: '#cbd5e1' }}>Warning: <strong>{riskDist?.warning ?? 0}</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#eab308' }} />
            <span style={{ color: '#cbd5e1' }}>Monitor: <strong>{riskDist?.monitor ?? 0}</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: 'var(--status-normal)' }} />
            <span style={{ color: '#cbd5e1' }}>Normal: <strong>{riskDist?.normal ?? 0}</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#94a3b8' }} />
            <span style={{ color: '#cbd5e1' }}>Stale: <strong>{riskDist?.stale ?? 0}</strong></span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', background: '#475569' }} />
            <span style={{ color: '#cbd5e1' }}>Unknown / No Data: <strong>{riskDist?.unknown_insufficient ?? 0}</strong></span>
          </div>
        </div>
      </div>

      {/* 5. Machines Requiring Attention Table */}
      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '10px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertOctagon size={18} color="#f87171" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>Machines Requiring Attention</h3>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>
              Priority-ranked turbofan units with active alarms, critical drift, or low RUL.
            </p>
          </div>
          <span style={{ fontSize: '12px', padding: '4px 10px', borderRadius: '6px', background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', fontWeight: 600 }}>
            {attentionItems.length} Units Flagged
          </span>
        </div>

        {attentionItems.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
            <CheckCircle2 size={32} color="var(--status-normal)" style={{ margin: '0 auto 8px auto' }} />
            <div>No machines currently require urgent attention.</div>
            <div style={{ fontSize: '12px', color: '#64748b', marginTop: '4px' }}>All monitored fleet units are operating within nominal baseline envelopes.</div>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Machine</th>
                  <th>Risk Level</th>
                  <th>RUL Estimate</th>
                  <th>Anomaly</th>
                  <th>Data Quality</th>
                  <th>ML Schema</th>
                  <th>Active Work Order</th>
                  <th>Recommended Action</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredAttention.map((item) => (
                  <tr key={item.machine_id} style={{ cursor: 'pointer' }} onClick={() => onSelectMachine && onSelectMachine(item.machine_id)}>
                    <td style={{ fontWeight: 700, color: '#0f172a' }}>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
                        {item.name || `Turbofan Engine #${item.unit_number}`}
                      </div>
                      <div style={{ fontSize: '11px', color: '#475569', fontWeight: 600 }}>
                        Unit #{String(item.unit_number).padStart(3, '0')}
                      </div>
                    </td>
                    <td>{getRiskBadge(item.risk_level)}</td>
                    <td style={{ fontWeight: 600, color: item.rul_available && item.rul_estimate !== null ? (item.rul_estimate <= 25 ? '#f87171' : '#38bdf8') : '#94a3b8' }}>
                      {item.rul_available && item.rul_estimate !== null ? `${item.rul_estimate.toFixed(1)} cyc` : 'RUL: UNAVAILABLE'}
                    </td>
                    <td>
                      {item.anomaly_status === 'ANOMALOUS' ? (
                        <span style={{ color: '#f87171', fontWeight: 600 }}>ANOMALOUS</span>
                      ) : (
                        <span style={{ color: '#94a3b8' }}>NORMAL</span>
                      )}
                    </td>
                    <td>
                      <span style={{ fontSize: '11px', color: item.data_quality === 'STALE' ? '#f59e0b' : '#38bdf8' }}>
                        {item.data_quality}
                      </span>
                    </td>
                    <td>
                      <span style={{ fontSize: '11px', color: item.ml_compatibility === 'COMPATIBLE' ? '#34d399' : '#f87171' }}>
                        {item.ml_compatibility}
                      </span>
                    </td>
                    <td>
                      {item.active_work_order_code ? (
                        <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', fontWeight: 600 }}>
                          {item.active_work_order_code} ({item.active_work_order_status})
                        </span>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#64748b' }}>None</span>
                      )}
                    </td>
                    <td style={{ fontSize: '12px', color: '#cbd5e1', maxWidth: '280px' }}>
                      {item.recommended_action}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (onSelectMachine) onSelectMachine(item.machine_id);
                        }}
                        style={{ fontSize: '11px', padding: '4px 8px' }}
                      >
                        Inspect Unit →
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* 6. Subsystem Reliability & Defect Analytics */}
      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sliders size={18} color="#a855f7" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>Turbofan Subsystem Reliability Analytics</h3>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>
              Multi-subsystem defect frequencies and historical maintenance resolution rates.
            </p>
          </div>
          <span style={{ fontSize: '12px', color: '#94a3b8' }}>{subsystems.length} Monitored Subsystems</span>
        </div>

        {subsystems.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
            Insufficient historical data.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px' }}>
            {subsystems.map((subsys) => (
              <div
                key={subsys.subsystem}
                style={{
                  padding: '16px',
                  background: 'rgba(255, 255, 255, 0.02)',
                  border: '1px solid rgba(255, 255, 255, 0.06)',
                  borderRadius: '10px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '10px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: '#ffffff' }}>{subsys.subsystem}</span>
                  <span
                    style={{
                      fontSize: '10px',
                      padding: '2px 6px',
                      borderRadius: '4px',
                      fontWeight: 600,
                      background: subsys.health_status === 'CRITICAL' ? 'rgba(239, 68, 68, 0.2)' : (subsys.health_status === 'DEGRADED' ? 'rgba(245, 158, 11, 0.2)' : 'rgba(16, 185, 129, 0.2)'),
                      color: subsys.health_status === 'CRITICAL' ? '#f87171' : (subsys.health_status === 'DEGRADED' ? '#fbbf24' : '#34d399')
                    }}
                  >
                    {subsys.health_status}
                  </span>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', fontSize: '11px', textAlign: 'center' }}>
                  <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '6px', borderRadius: '6px' }}>
                    <div style={{ color: '#94a3b8' }}>Alerts</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#cbd5e1', marginTop: '2px' }}>{subsys.associated_alert_count}</div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '6px', borderRadius: '6px' }}>
                    <div style={{ color: '#94a3b8' }}>Work Orders</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: '#c084fc', marginTop: '2px' }}>{subsys.work_order_count}</div>
                  </div>
                  <div style={{ background: 'rgba(255, 255, 255, 0.03)', padding: '6px', borderRadius: '6px' }}>
                    <div style={{ color: '#94a3b8' }}>Critical</div>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: subsys.critical_issue_count > 0 ? '#f87171' : '#cbd5e1', marginTop: '2px' }}>
                      {subsys.critical_issue_count}
                    </div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b', borderTop: '1px solid rgba(255, 255, 255, 0.04)', paddingTop: '8px' }}>
                  <span>Resolved: <strong style={{ color: 'var(--status-normal)' }}>{subsys.verification_outcomes?.RESOLVED || 0}</strong></span>
                  <span>Recurring: <strong style={{ color: '#fbbf24' }}>{subsys.recurring_issue_count || 0}</strong></span>
                  <span>Units: <strong style={{ color: '#94a3b8' }}>{subsys.affected_units?.length || 0}</strong></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 7. Predictive Maintenance Planning Queue */}
      <div className="card" style={{ padding: '20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} color="#fbbf24" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 600, color: '#ffffff' }}>Maintenance Planning Queue</h3>
            </div>
            <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#94a3b8' }}>
              Deterministic decision-support recommendations. Authorize work orders as an operator.
            </p>
          </div>

          {/* Planning Filter Tabs */}
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {['ALL', 'Immediate Attention', 'High Priority', 'Schedule Inspection', 'Monitor Closely', 'No Action Recommended', 'Insufficient Data'].map((f) => (
              <button
                key={f}
                className={`btn ${planningFilter === f ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setPlanningFilter(f)}
                style={{ fontSize: '11px', padding: '4px 8px' }}
              >
                {f}
              </button>
            ))}
          </div>
        </div>

        {/* Read-Only Decision Support Notice */}
        <div style={{ padding: '10px 14px', background: 'rgba(59, 130, 246, 0.08)', border: '1px solid rgba(59, 130, 246, 0.2)', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px', fontSize: '12px', color: '#93c5fd' }}>
          <Info size={16} color="#60a5fa" style={{ flexShrink: 0 }} />
          <span>
            <strong>Decision Support Advisory:</strong> Planning recommendations are generated deterministically based on prognostic wear rates. Work orders are never created automatically. Human authorization is strictly mandatory.
          </span>
        </div>

        {filteredPlans.length === 0 ? (
          <div style={{ padding: '32px', textAlign: 'center', color: '#94a3b8', fontSize: '13px' }}>
            No planning records match the selected filter.
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rank</th>
                  <th>Machine</th>
                  <th>Planning State</th>
                  <th>Risk / RUL</th>
                  <th>Active Work Order</th>
                  <th>Recommendation</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredPlans.slice(0, 50).map((plan) => (
                  <tr key={plan.machine_id}>
                    <td style={{ fontWeight: 700, color: '#94a3b8' }}>#{plan.urgency_rank}</td>
                    <td style={{ fontWeight: 700, color: '#0f172a' }}>
                      <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>
                        {plan.machine_name || `Turbofan Engine #${plan.unit_number}`}
                      </div>
                      <div style={{ fontSize: '11px', color: '#475569', fontWeight: 600 }}>
                        Unit #{String(plan.unit_number).padStart(3, '0')}
                      </div>
                    </td>
                    <td>{getPlanningBadge(plan.planning_state)}</td>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                        <div>{getRiskBadge(plan.risk_level)}</div>
                        <span style={{ fontSize: '11px', color: plan.rul_available && plan.rul_estimate !== null ? '#38bdf8' : '#94a3b8' }}>
                          {plan.rul_available && plan.rul_estimate !== null ? `RUL: ${plan.rul_estimate.toFixed(1)} cyc` : 'RUL: UNAVAILABLE'}
                        </span>
                      </div>
                    </td>
                    <td>
                      {plan.active_work_order_code ? (
                        <span style={{ fontSize: '11px', padding: '2px 6px', borderRadius: '4px', background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', fontWeight: 600 }}>
                          {plan.active_work_order_code} ({plan.active_work_order_status})
                        </span>
                      ) : (
                        <span style={{ fontSize: '11px', color: '#64748b' }}>No Work Order</span>
                      )}
                    </td>
                    <td style={{ fontSize: '12px', maxWidth: '340px' }}>
                      <div style={{ fontWeight: 600, color: '#ffffff' }}>{plan.recommendation_title}</div>
                      <div style={{ color: '#94a3b8', marginTop: '2px', fontSize: '11px' }}>{plan.suggested_action}</div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          className="btn btn-secondary"
                          onClick={() => onSelectMachine && onSelectMachine(plan.machine_id)}
                          style={{ fontSize: '11px', padding: '4px 8px' }}
                        >
                          View Unit
                        </button>
                        {plan.active_work_order_id && onNavigateTab && (
                          <button
                            className="btn btn-primary"
                            onClick={() => onNavigateTab('maintenance')}
                            style={{ fontSize: '11px', padding: '4px 8px' }}
                          >
                            Maintenance
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
