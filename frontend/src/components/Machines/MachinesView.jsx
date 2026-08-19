import React, { useState } from 'react';
import {
  Cpu,
  Search,
  Filter,
  CheckCircle2,
  AlertTriangle,
  ArrowRight,
  Gauge,
  Clock
} from 'lucide-react';

export default function MachinesView({ machines, onSelectMachine, searchQuery, onSearchChange }) {
  const [statusFilter, setStatusFilter] = useState('ALL');

  const filteredMachines = machines.filter((m) => {
    const q = (searchQuery || '').trim().toLowerCase();
    const unitStr = String(m.unit_number);
    const paddedUnit = unitStr.padStart(3, '0');

    const matchSearch = !q || (
      (m.name || '').toLowerCase().includes(q) ||
      unitStr.includes(q) ||
      paddedUnit.includes(q) ||
      `unit ${unitStr}`.includes(q) ||
      `unit #${unitStr}`.includes(q) ||
      `unit #${paddedUnit}`.includes(q) ||
      (m.location || '').toLowerCase().includes(q) ||
      (m.status || '').toLowerCase().includes(q) ||
      (m.latest_risk_level || '').toLowerCase().includes(q)
    );

    // Status filter
    if (statusFilter === 'OPERATIONAL') return matchSearch && (m.status === 'OPERATIONAL' || m.latest_risk_level === 'NORMAL');
    if (statusFilter === 'WARNING') return matchSearch && (m.status === 'WARNING' || m.status === 'MONITORING' || m.latest_risk_level === 'WARNING' || m.latest_risk_level === 'MONITOR');
    if (statusFilter === 'CRITICAL') return matchSearch && (m.status === 'CRITICAL' || m.latest_risk_level === 'CRITICAL');
    return matchSearch;
  });

  const getStatusBadge = (lvl) => {
    switch (lvl) {
      case 'CRITICAL': return <span className="badge badge-critical"><span className="status-dot dot-critical" />Critical</span>;
      case 'WARNING':
      case 'MONITOR': return <span className="badge badge-warning"><span className="status-dot dot-warning" />Warning</span>;
      default: return <span className="badge badge-normal"><span className="status-dot dot-normal" />Operational</span>;
    }
  };

  return (
    <div>
      {/* Page Header */}
      <div className="page-header">
        <h2 className="page-title">Turbofan Engine Fleet</h2>
        <p className="page-description">Complete fleet registry of 100 NASA C-MAPSS turbofan engines with real-time prognostic status.</p>
      </div>

      {/* Filter & Search Bar */}
      <div className="card" style={{ marginBottom: '20px', padding: '12px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          {/* Status Filter Buttons */}
          <div style={{ display: 'flex', gap: '8px' }}>
            {['ALL', 'OPERATIONAL', 'WARNING', 'CRITICAL'].map((f) => (
              <button
                key={f}
                className={`btn btn-sm ${statusFilter === f ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setStatusFilter(f)}
              >
                {f === 'ALL' ? 'All Machines' : f.charAt(0) + f.slice(1).toLowerCase()}
              </button>
            ))}
          </div>

          <div style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
            Showing {filteredMachines.length} of {machines.length} engines
          </div>
        </div>
      </div>

      {/* Machines Grid */}
      {filteredMachines.length === 0 ? (
        <div className="empty-state">
          <Cpu size={40} className="empty-icon" />
          <div className="empty-title">No Machines Match Filter</div>
          <div className="empty-desc">Try clearing your search query or selecting a different status filter.</div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
          {filteredMachines.map((m) => {
            const health = m.latest_health_index !== undefined && m.latest_health_index !== null ? m.latest_health_index.toFixed(1) : '100.0';
            const rul = m.latest_rul !== undefined && m.latest_rul !== null ? m.latest_rul.toFixed(1) : '--';
            const risk = m.latest_risk_level || m.status;

            return (
              <div
                key={m.id}
                className="card"
                style={{
                  display: 'flex',
                  flexDirection: 'column',
                  cursor: 'pointer',
                  transition: 'transform 0.15s ease, border-color 0.15s ease'
                }}
                onClick={() => onSelectMachine(m.id)}
              >
                {/* Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <span className="mono" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)' }}>
                      UNIT #{String(m.unit_number).padStart(3, '0')}
                    </span>
                    <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
                      {m.name}
                    </h3>
                  </div>
                  {getStatusBadge(risk)}
                </div>

                {/* Body Meta */}
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '16px' }}>
                  <div>Type: {m.machine_type}</div>
                  <div>Location: {m.location}</div>
                </div>

                {/* Progress & Metrics */}
                <div style={{ marginTop: 'auto', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '6px' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Health Index</span>
                    <span className="mono" style={{ fontWeight: 700 }}>{health}%</span>
                  </div>
                  <div className="progress-bar-bg" style={{ marginBottom: '12px' }}>
                    <div
                      className={`progress-bar-fill ${parseFloat(health) < 60 ? 'fill-warning' : 'fill-normal'}`}
                      style={{ width: `${Math.min(100, parseFloat(health))}%` }}
                    />
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      RUL: <strong className="mono" style={{ color: 'var(--text-primary)' }}>{rul} cycles</strong>
                    </span>
                    <span style={{ fontSize: '12px', fontWeight: 600, color: '#2563eb', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      Inspect <ArrowRight size={12} />
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
