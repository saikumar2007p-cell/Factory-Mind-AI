import React, { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Filter,
  Clock,
  ArrowRight,
  ShieldCheck,
  Wrench
} from 'lucide-react';
import { createWorkOrder } from '../../services/api';

export default function AlertsView({ alerts, onAcknowledgeAlert, onSelectMachine, userRole = 'ADMIN', searchQuery }) {
  const [filter, setFilter] = useState('ALL'); // ALL, ACTIVE, ACKNOWLEDGED

  const filtered = alerts.filter(a => {
    if (filter === 'ACTIVE' && a.status !== 'ACTIVE') return false;
    if (filter === 'ACKNOWLEDGED' && a.status !== 'ACKNOWLEDGED') return false;

    const q = (searchQuery || '').trim().toLowerCase();
    if (!q) return true;

    const unitStr = String(a.machine_id);
    const paddedUnit = unitStr.padStart(3, '0');

    return (
      String(a.id).includes(q) ||
      unitStr.includes(q) ||
      paddedUnit.includes(q) ||
      `unit ${unitStr}`.includes(q) ||
      `unit #${unitStr}`.includes(q) ||
      `unit #${paddedUnit}`.includes(q) ||
      (a.severity || '').toLowerCase().includes(q) ||
      (a.reason || '').toLowerCase().includes(q) ||
      (a.status || '').toLowerCase().includes(q) ||
      (a.subsystem || '').toLowerCase().includes(q)
    );
  });

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">Degradation Alarms Ledger</h2>
        <p className="page-description">Actionable alerts generated strictly by the Stage 2 multi-cycle persistence decision engine.</p>
      </div>

      {/* Filter Tabs */}
      <div className="card" style={{ marginBottom: '20px', padding: '12px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            {['ALL', 'ACTIVE', 'ACKNOWLEDGED'].map((f) => (
              <button
                key={f}
                className={`btn btn-sm ${filter === f ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setFilter(f)}
              >
                {f.charAt(0) + f.slice(1).toLowerCase()} ({f === 'ALL' ? alerts.length : alerts.filter(a => a.status === f).length})
              </button>
            ))}
          </div>
          <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
            Showing {filtered.length} alarms
          </span>
        </div>
      </div>

      {/* Alarms Table */}
      <div className="card">
        {filtered.length === 0 ? (
          <div className="empty-state">
            <CheckCircle2 size={36} color="var(--status-normal)" style={{ marginBottom: '8px' }} />
            <div className="empty-title">No Alarms in Ledger</div>
            <div className="empty-desc">No degradation threshold breaches match the active filter criteria.</div>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Alarm ID</th>
                  <th>Machine Unit</th>
                  <th>Cycle</th>
                  <th>Severity</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th>Created At</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((a) => (
                  <tr key={a.id}>
                    <td className="mono" style={{ fontWeight: 600 }}>#{a.id}</td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '2px 8px' }}
                        onClick={() => onSelectMachine(a.machine_id)}
                      >
                        Unit #{String(a.machine_id).padStart(3, '0')}
                      </button>
                    </td>
                    <td className="mono">{a.cycle}</td>
                    <td><span className={`badge badge-${a.risk_level.toLowerCase()}`}>{a.severity}</span></td>
                    <td>{a.reason}</td>
                    <td>
                      <span className={`badge ${a.status === 'ACTIVE' ? 'badge-warning' : 'badge-normal'}`}>
                        {a.status}
                      </span>
                    </td>
                    <td className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {a.created_at ? new Date(a.created_at).toLocaleTimeString() : 'Recent'}
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                        {userRole === 'VIEWER' ? (
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Read-Only</span>
                        ) : (
                          <>
                            {a.status === 'ACTIVE' ? (
                              <button
                                className="btn btn-primary btn-sm"
                                onClick={() => onAcknowledgeAlert(a.id)}
                              >
                                Acknowledge
                              </button>
                            ) : (
                              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Acknowledged</span>
                            )}

                            <button
                              className="btn btn-secondary btn-sm"
                              style={{ padding: '4px 8px' }}
                              title="Dispatch Work Order from this Alarm"
                              onClick={async () => {
                                try {
                                  const res = await createWorkOrder({
                                    machine_id: a.machine_id,
                                    title: `Alarm Remediation: ${a.reason}`,
                                    recommended_action: `Inspect machine components triggering alarm: ${a.reason}`,
                                    affected_subsystem: 'Turbofan Core',
                                    priority: a.severity === 'CRITICAL' ? 'CRITICAL' : (a.severity === 'HIGH' ? 'HIGH' : 'MEDIUM'),
                                    risk_level: a.risk_level,
                                    source_alert_id: a.id,
                                    observed_evidence: a.evidence || {}
                                  });
                                  alert(`Work Order ${res.work_order_code} created from Alarm #${a.id}!`);
                                } catch (err) {
                                  const msg = err.status === 403 ? 'Permission denied — Operator or Admin authorization required.' : (err.detail || err.message);
                                  alert(`Failed to create work order: ${msg}`);
                                }
                              }}
                            >
                              <Wrench size={12} />
                              Create WO
                            </button>
                          </>
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
