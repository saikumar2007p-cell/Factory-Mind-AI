import React, { useState, useEffect } from 'react';
import {
  Wrench,
  CheckCircle2,
  Clock,
  AlertTriangle,
  Calendar,
  ShieldCheck,
  Search,
  Plus,
  ArrowRight,
  UserCheck,
  Play,
  CheckSquare,
  FileText,
  Activity,
  X,
  Sparkles,
  Info,
  Database,
  Cpu
} from 'lucide-react';
import {
  getWorkOrders,
  getWorkOrdersSummary,
  getWorkOrderDetails,
  getWorkOrderComparison,
  createWorkOrder,
  assignWorkOrder,
  startWorkOrder,
  completeWorkOrder,
  verifyWorkOrder
} from '../../services/api';

import GroundTruthOutcomeModal from './GroundTruthOutcomeModal';

export default function MaintenanceView({ latestDiagnosis, onSelectMachine, machines = [], userRole = 'ADMIN', searchQuery: propSearchQuery }) {
  const [workOrders, setWorkOrders] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [internalSearchQuery, setInternalSearchQuery] = useState('');
  const searchQuery = propSearchQuery !== undefined ? propSearchQuery : internalSearchQuery;
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [isAssignModalOpen, setIsAssignModalOpen] = useState(false);
  const [isVerifyModalOpen, setIsVerifyModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isOutcomeModalOpen, setIsOutcomeModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);


  // Form states
  const [assigneeName, setAssigneeName] = useState('');
  const [verifyOutcome, setVerifyOutcome] = useState('RESOLVED');
  const [verifyNotes, setVerifyNotes] = useState('');
  const [createForm, setCreateForm] = useState({
    machine_id: 1,
    title: '',
    recommended_action: '',
    affected_subsystem: 'Turbofan Core',
    priority: 'MEDIUM',
    assigned_to: ''
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const [ordersRes, sumRes] = await Promise.allSettled([
        getWorkOrders({ status: statusFilter !== 'ALL' ? statusFilter : undefined }),
        getWorkOrdersSummary()
      ]);
      if (ordersRes.status === 'fulfilled') {
        setWorkOrders(ordersRes.value || []);
      }
      if (sumRes.status === 'fulfilled') {
        setSummary(sumRes.value);
      }
    } catch (err) {
      console.error('Failed loading maintenance work orders', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter]);

  const handleSelectOrder = async (orderId) => {
    try {
      const details = await getWorkOrderDetails(orderId);
      setSelectedOrder(details);
      const comp = await getWorkOrderComparison(orderId);
      setComparison(comp);
    } catch (err) {
      console.error('Failed fetching order details', err);
    }
  };

  const handleAssign = async (e) => {
    e.preventDefault();
    if (!selectedOrder || !assigneeName.trim() || actionLoading) return;
    setActionLoading(true);
    try {
      await assignWorkOrder(selectedOrder.id, assigneeName.trim());
      setIsAssignModalOpen(false);
      setAssigneeName('');
      await handleSelectOrder(selectedOrder.id);
      await loadData();
    } catch (err) {
      const msg = err.status === 422 || err.detail?.includes('Invalid lifecycle transition')
        ? 'Invalid workflow transition. Refresh the work order and continue from its current status.'
        : (err.detail || err.message || 'Unable to complete this operation. Please try again.');
      alert(`Assignment failed: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = async (orderId) => {
    if (actionLoading) return;
    setActionLoading(true);
    try {
      await startWorkOrder(orderId);
      await handleSelectOrder(orderId);
      await loadData();
    } catch (err) {
      const msg = err.status === 422 || err.detail?.includes('Invalid lifecycle transition')
        ? 'Invalid workflow transition. Refresh the work order and continue from its current status.'
        : (err.detail || err.message || 'Unable to complete this operation. Please try again.');
      alert(`Failed to start execution: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleComplete = async (orderId) => {
    if (actionLoading) return;
    setActionLoading(true);
    try {
      await completeWorkOrder(orderId);
      await handleSelectOrder(orderId);
      await loadData();
    } catch (err) {
      const msg = err.status === 422 || err.detail?.includes('Invalid lifecycle transition')
        ? 'Invalid workflow transition. Refresh the work order and continue from its current status.'
        : (err.detail || err.message || 'Unable to complete this operation. Please try again.');
      alert(`Failed to complete work order: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleVerify = async (e) => {
    e.preventDefault();
    if (!selectedOrder || actionLoading) return;
    setActionLoading(true);
    try {
      await verifyWorkOrder(selectedOrder.id, verifyOutcome, verifyNotes);
      setIsVerifyModalOpen(false);
      setVerifyNotes('');
      await handleSelectOrder(selectedOrder.id);
      await loadData();
    } catch (err) {
      const msg = err.status === 422 || err.detail?.includes('Invalid lifecycle transition')
        ? 'Invalid workflow transition. Refresh the work order and continue from its current status.'
        : (err.detail || err.message || 'Unable to complete this operation. Please try again.');
      alert(`Verification failed: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateNew = async (e) => {
    e.preventDefault();
    if (!createForm.title.trim() || !createForm.recommended_action.trim() || actionLoading) {
      alert('Title and Prescriptive Action are required.');
      return;
    }
    setActionLoading(true);
    try {
      const assignedVal = createForm.assigned_to.trim() || 'Unassigned';
      await createWorkOrder({
        machine_id: parseInt(createForm.machine_id),
        title: createForm.title.trim(),
        recommended_action: createForm.recommended_action.trim(),
        affected_subsystem: createForm.affected_subsystem.trim() || 'Turbofan Core',
        priority: createForm.priority,
        assigned_to: assignedVal
      });
      setIsCreateModalOpen(false);
      setCreateForm({
        machine_id: 1,
        title: '',
        recommended_action: '',
        affected_subsystem: 'Turbofan Core',
        priority: 'MEDIUM',
        assigned_to: ''
      });
      await loadData();
    } catch (err) {
      const msg = err.detail || err.message || 'Unable to complete this operation. Please try again.';
      alert(`Failed to create work order: ${msg}`);
    } finally {
      setActionLoading(false);
    }
  };

  const filteredOrders = workOrders.filter((wo) => {
    const q = (searchQuery || '').trim().toLowerCase();
    if (!q) return true;
    const unitStr = String(wo.machine_id);
    const paddedUnit = unitStr.padStart(3, '0');
    return (
      (wo.work_order_code || '').toLowerCase().includes(q) ||
      unitStr.includes(q) ||
      paddedUnit.includes(q) ||
      `unit ${unitStr}`.includes(q) ||
      `unit #${unitStr}`.includes(q) ||
      `unit #${paddedUnit}`.includes(q) ||
      (wo.machine_name || '').toLowerCase().includes(q) ||
      (wo.affected_subsystem || '').toLowerCase().includes(q) ||
      (wo.title || '').toLowerCase().includes(q) ||
      (wo.status || '').toLowerCase().includes(q) ||
      (wo.priority || '').toLowerCase().includes(q) ||
      (wo.assigned_to || '').toLowerCase().includes(q) ||
      (wo.recommended_action || '').toLowerCase().includes(q)
    );
  });

  const getStatusBadge = (status) => {
    switch (status) {
      case 'OPEN':
      case 'RECOMMENDED':
        return <span className="badge badge-normal"><Clock size={12} /> Open</span>;
      case 'ASSIGNED':
        return <span className="badge badge-ai"><UserCheck size={12} /> Assigned</span>;
      case 'IN_PROGRESS':
        return <span className="badge badge-warning"><Activity size={12} /> In Progress</span>;
      case 'COMPLETED':
      case 'VERIFICATION_REQUIRED':
        return <span className="badge badge-warning" style={{ background: '#fef3c7', color: '#92400e', borderColor: '#fde68a' }}><CheckSquare size={12} /> Verification Required</span>;
      case 'VERIFIED':
        return <span className="badge badge-normal" style={{ background: '#ecfdf5', color: '#065f46', borderColor: '#a7f3d0' }}><ShieldCheck size={12} /> Verified</span>;
      default:
        return <span className="badge badge-normal">{status}</span>;
    }
  };

  const getPriorityBadge = (priority) => {
    switch (priority) {
      case 'CRITICAL': return <span className="badge badge-critical">Critical</span>;
      case 'HIGH': return <span className="badge badge-warning">High</span>;
      case 'MEDIUM': return <span className="badge badge-ai">Medium</span>;
      default: return <span className="badge badge-normal">Low</span>;
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 className="page-title">Closed-Loop Maintenance Operations & Verification</h2>
          <p className="page-description">
            Traceable execution from ML anomaly detection and Gemini root-cause diagnosis to assigned maintenance and verified resolution.
          </p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setIsCreateModalOpen(true)}
        >
          <Plus size={16} />
          Create Work Order
        </button>
      </div>

      {/* Summary Metrics Cards */}
      <div className="metrics-row" style={{ marginBottom: '20px' }}>
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Open Queue</span>
            <Clock size={18} color="var(--text-muted)" />
          </div>
          <div className="metric-value">{summary?.open_count ?? 0}</div>
          <div className="metric-sub">Awaiting technician assignment</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Assigned</span>
            <UserCheck size={18} color="#2563eb" />
          </div>
          <div className="metric-value" style={{ color: '#2563eb' }}>{summary?.assigned_count ?? 0}</div>
          <div className="metric-sub">Technicians assigned</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">In Progress</span>
            <Activity size={18} color="var(--status-warning)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--status-warning)' }}>{summary?.in_progress_count ?? 0}</div>
          <div className="metric-sub">Active field maintenance</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Verification Required</span>
            <CheckSquare size={18} color="var(--status-critical)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--status-critical)' }}>{summary?.verification_required_count ?? 0}</div>
          <div className="metric-sub">Awaiting post-work sign-off</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Verified</span>
            <ShieldCheck size={18} color="var(--status-normal)" />
          </div>
          <div className="metric-value" style={{ color: 'var(--status-normal)' }}>{summary?.verified_count ?? 0}</div>
          <div className="metric-sub">Completed & sign-off verified</div>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="card" style={{ marginBottom: '20px', padding: '12px 16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
            {[
              { id: 'ALL', label: 'All' },
              { id: 'OPEN', label: 'Open' },
              { id: 'ASSIGNED', label: 'Assigned' },
              { id: 'IN_PROGRESS', label: 'In Progress' },
              { id: 'VERIFICATION_REQUIRED', label: 'Verification Required' },
              { id: 'VERIFIED', label: 'Verified' }
            ].map((tab) => (
              <button
                key={tab.id}
                className={`btn btn-sm ${statusFilter === tab.id ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setStatusFilter(tab.id)}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ position: 'relative' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search unit, code, subsystem..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  padding: '6px 12px 6px 30px',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  background: 'var(--bg-main)',
                  fontSize: '13px',
                  width: '220px'
                }}
              />
            </div>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Showing {filteredOrders.length} records
            </span>
          </div>
        </div>
      </div>

      {/* Main Work Orders Table */}
      <div className="card">
        {loading ? (
          <div className="empty-state" style={{ padding: '32px' }}>
            <Clock size={32} color="var(--text-muted)" style={{ marginBottom: '8px' }} />
            <div className="empty-title">Loading Work Orders...</div>
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="empty-state" style={{ padding: '32px' }}>
            <Info size={36} color="var(--text-muted)" style={{ marginBottom: '8px' }} />
            <div className="empty-title">No work orders match the current filter.</div>
            <div className="empty-desc">No records available.</div>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Order Code</th>
                  <th>Machine Unit</th>
                  <th>Subsystem</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Prescriptive Action</th>
                  <th>Assigned To</th>
                  <th>Created</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredOrders.map((wo) => (
                  <tr key={wo.id}>
                    <td className="mono" style={{ fontWeight: 700, color: 'var(--color-primary)' }}>
                      {wo.work_order_code}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '2px 8px' }}
                        onClick={() => onSelectMachine && onSelectMachine(wo.machine_id)}
                      >
                        Unit #{String(wo.machine_id).padStart(3, '0')}
                      </button>
                    </td>
                    <td><span className="badge badge-offline">{wo.affected_subsystem || 'Turbofan Core'}</span></td>
                    <td>{getPriorityBadge(wo.priority)}</td>
                    <td>{getStatusBadge(wo.status)}</td>
                    <td style={{ maxWidth: '320px', fontSize: '13px' }}>{wo.recommended_action}</td>
                    <td style={{ fontSize: '12px', color: (!wo.assigned_to || wo.assigned_to === 'Unassigned') ? 'var(--text-muted)' : 'var(--text-primary)', fontWeight: (!wo.assigned_to || wo.assigned_to === 'Unassigned') ? 400 : 600 }}>
                      {wo.assigned_to || 'Unassigned'}
                    </td>
                    <td className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {wo.created_at ? new Date(wo.created_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleSelectOrder(wo.id)}
                      >
                        Manage
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Selected Work Order Management Drawer / Panel */}
      {selectedOrder && (
        <div className="card" style={{ marginTop: '24px', borderLeft: '4px solid var(--color-primary)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px', flexWrap: 'wrap' }}>
                <span className="mono" style={{ fontSize: '16px', fontWeight: 800, color: 'var(--color-primary)' }}>
                  {selectedOrder.work_order_code}
                </span>
                <button
                  className="btn btn-secondary btn-sm"
                  style={{ padding: '2px 8px', fontSize: '12px' }}
                  onClick={() => onSelectMachine && onSelectMachine(selectedOrder.machine_id)}
                >
                  Unit #{String(selectedOrder.machine_id).padStart(3, '0')}
                </button>
                {getStatusBadge(selectedOrder.status)}
                {getPriorityBadge(selectedOrder.priority)}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '4px' }}>
                <span>Data Source: <strong>{selectedOrder.data_source || 'NASA C-MAPSS FD001 — Simulation'}</strong></span>
                <span>&bull;</span>
                <span>Real Industrial Data: <strong>Not Configured</strong></span>
                <span>&bull;</span>
                <span>Subsystem: <strong>{selectedOrder.affected_subsystem || 'N/A'}</strong></span>
                <span>&bull;</span>
                <span>Risk Level: <strong>{selectedOrder.risk_level || 'N/A'}</strong></span>
              </div>
            </div>

            <button
              className="btn btn-secondary btn-sm"
              onClick={() => setSelectedOrder(null)}
            >
              <X size={14} /> Close
            </button>
          </div>

          {/* Action Ribbon depending strictly on lifecycle status */}
          <div style={{ background: 'var(--bg-card-secondary)', padding: '14px', borderRadius: 'var(--radius-md)', marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Workflow Action:</span>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                Assigned: <strong>{selectedOrder.assigned_to || 'Unassigned'}</strong>
              </span>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
              {/* OPEN: ONLY show Assign Technician (NEVER show Start Execution) */}
              {(selectedOrder.status === 'OPEN' || selectedOrder.status === 'RECOMMENDED') && (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => setIsAssignModalOpen(true)}
                >
                  <UserCheck size={14} /> Assign Technician
                </button>
              )}

              {/* ASSIGNED: Show Start Execution & Reassign */}
              {selectedOrder.status === 'ASSIGNED' && (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => setIsAssignModalOpen(true)}
                  >
                    <UserCheck size={14} /> Reassign
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleStart(selectedOrder.id)}
                  >
                    <Play size={14} /> Start Execution
                  </button>
                </div>
              )}

              {/* IN_PROGRESS: Show Mark Maintenance Completed */}
              {selectedOrder.status === 'IN_PROGRESS' && (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => handleComplete(selectedOrder.id)}
                >
                  <CheckSquare size={14} /> Mark Maintenance Completed
                </button>
              )}

              {/* VERIFICATION_REQUIRED: Show Perform Verification Sign-Off */}
              {(selectedOrder.status === 'VERIFICATION_REQUIRED' || selectedOrder.status === 'COMPLETED') && (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => setIsVerifyModalOpen(true)}
                  style={{ background: '#059669', borderColor: '#059669' }}
                >
                  <ShieldCheck size={14} /> Perform Verification Sign-Off
                </button>
              )}

              {/* VERIFIED: Show Verification Complete & Record Outcome Button */}
              {selectedOrder.status === 'VERIFIED' && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                  <span className="badge badge-normal" style={{ background: '#ecfdf5', color: '#065f46', borderColor: '#a7f3d0' }}>
                    <ShieldCheck size={14} /> Verification Complete ({selectedOrder.verification_status || 'RESOLVED'})
                  </span>
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => setIsOutcomeModalOpen(true)}
                    style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                  >
                    <Sparkles size={14} color="#6366f1" /> Record Ground-Truth Outcome
                  </button>
                </div>
              )}
            </div>
          </div>


          {/* Details 2-Column Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '16px' }}>
            {/* Prescriptive Action, Traceability & Observed Evidence */}
            <div style={{ background: 'var(--bg-main)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Prescriptive Maintenance Directive & Traceability
              </div>
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '12px' }}>
                {selectedOrder.recommended_action}
              </div>

              {/* Traceability Metadata */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', marginBottom: '12px', padding: '8px', background: 'var(--bg-card-secondary)', borderRadius: 'var(--radius-sm)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Origin / Source:</span>
                  <span style={{ fontWeight: 600 }}>
                    {selectedOrder.source_alert_id ? `Alert #${selectedOrder.source_alert_id}` : (selectedOrder.source_recommendation_id ? `AI Recommendation #${selectedOrder.source_recommendation_id}` : 'Manual Work Order')}
                  </span>
                </div>
                {selectedOrder.source_alert_id && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Source Alert ID:</span>
                    <span className="mono">Alert #{selectedOrder.source_alert_id}</span>
                  </div>
                )}
                {selectedOrder.source_recommendation_id && (
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span style={{ color: 'var(--text-muted)' }}>Source Recommendation ID:</span>
                    <span className="mono">Recommendation #{selectedOrder.source_recommendation_id}</span>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Assigned To:</span>
                  <span>{selectedOrder.assigned_to || 'Unassigned'}</span>
                </div>
              </div>

              {/* ML Compatibility & Prognostic Evidence */}
              {selectedOrder.ml_evidence && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    ML Compatibility & Prognostic Evidence
                  </div>
                  <div style={{ padding: '8px', background: 'var(--bg-card-secondary)', borderRadius: 'var(--radius-sm)', fontSize: '12px' }}>
                    {selectedOrder.ml_evidence.ml_compatibility === 'INCOMPATIBLE' ? (
                      <div style={{ color: 'var(--status-critical)' }}>
                        <div><strong>ML Compatibility:</strong> INCOMPATIBLE</div>
                        <div><strong>RUL Prediction:</strong> UNAVAILABLE</div>
                        <div><strong>Anomaly Prediction:</strong> UNAVAILABLE</div>
                      </div>
                    ) : (
                      <div>
                        <div>RUL Estimate: <strong className="mono">{selectedOrder.ml_evidence.rul_estimate != null ? `${selectedOrder.ml_evidence.rul_estimate} cycles` : 'UNAVAILABLE'}</strong></div>
                        <div>Anomaly Score: <strong className="mono">{selectedOrder.ml_evidence.anomaly_score != null ? selectedOrder.ml_evidence.anomaly_score : 'UNAVAILABLE'}</strong></div>
                        {selectedOrder.ml_evidence.health_index != null && (
                          <div>Health Index: <strong className="mono">{selectedOrder.ml_evidence.health_index}%</strong></div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Observed Telemetry Evidence */}
              <div>
                <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                  Observed Sensor Telemetry Evidence
                </div>
                {selectedOrder.observed_evidence ? (
                  <pre style={{ background: 'var(--bg-card-secondary)', padding: '8px', borderRadius: 'var(--radius-sm)', fontSize: '11px', overflowX: 'auto' }}>
                    {JSON.stringify(selectedOrder.observed_evidence, null, 2)}
                  </pre>
                ) : (
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                    No records available.
                  </div>
                )}
              </div>
            </div>

            {/* Lifecycle Timeline & Verification Outcome */}
            <div style={{ background: 'var(--bg-main)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Traceable Lifecycle Timestamps
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Created At:</span>
                  <span className="mono">{selectedOrder.created_at ? new Date(selectedOrder.created_at).toLocaleString() : 'N/A'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Started At:</span>
                  <span className="mono">{selectedOrder.started_at ? new Date(selectedOrder.started_at).toLocaleString() : 'N/A'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Completed At:</span>
                  <span className="mono">{selectedOrder.completed_at ? new Date(selectedOrder.completed_at).toLocaleString() : 'N/A'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>Verified At:</span>
                  <span className="mono">{selectedOrder.verified_at ? new Date(selectedOrder.verified_at).toLocaleString() : 'N/A'}</span>
                </div>
              </div>

              {selectedOrder.verification_status && (
                <div style={{ marginTop: '14px', padding: '10px', background: 'var(--bg-card-secondary)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', marginBottom: '4px' }}>
                    Verification Inspection Result
                  </div>
                  <div style={{ fontSize: '13px', fontWeight: 600 }}>
                    Status: <span style={{ color: selectedOrder.verification_status === 'RESOLVED' ? 'var(--status-normal)' : 'var(--status-warning)' }}>{selectedOrder.verification_status}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '4px' }}>
                    Notes: {selectedOrder.verification_notes || 'N/A'}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Post-Maintenance Telemetry Comparison (Before vs After) */}
          <div style={{ background: 'var(--bg-card-secondary)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)', marginBottom: '16px' }}>
            <div style={{ fontSize: '13px', fontWeight: 700, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Activity size={16} color="var(--color-primary)" />
              Post-Maintenance Telemetry Comparison (Before vs After)
            </div>

            {comparison?.has_post_maintenance_data && comparison.after ? (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div style={{ padding: '10px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    Before Maintenance (Baseline)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px' }}>
                    <div>Risk Level: <strong>{comparison.before?.risk_level || 'N/A'}</strong></div>
                    <div>RUL Estimate: <strong className="mono">{comparison.before?.rul_estimate != null ? `${comparison.before.rul_estimate} cycles` : 'UNAVAILABLE'}</strong></div>
                    <div>Health Index: <strong className="mono">{comparison.before?.health_index != null ? `${comparison.before.health_index}%` : 'N/A'}</strong></div>
                    <div>Anomaly Score: <strong className="mono">{comparison.before?.anomaly_score != null ? comparison.before.anomaly_score : 'UNAVAILABLE'}</strong></div>
                  </div>
                </div>

                <div style={{ padding: '10px', background: 'var(--bg-main)', borderRadius: 'var(--radius-sm)' }}>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--status-normal)', textTransform: 'uppercase', marginBottom: '4px' }}>
                    After Maintenance (Current Telemetry)
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', fontSize: '12px' }}>
                    <div>Cycle: <strong className="mono">{comparison.after?.cycle ?? 'N/A'}</strong></div>
                    <div>Risk Level: <strong>{comparison.after?.risk_level || 'N/A'}</strong></div>
                    <div>RUL Estimate: <strong className="mono">{comparison.after?.rul_estimate != null ? `${comparison.after.rul_estimate.toFixed(1)} cycles` : 'UNAVAILABLE'}</strong></div>
                    <div>Health Index: <strong className="mono">{comparison.after?.health_index != null ? `${comparison.after.health_index.toFixed(1)}%` : 'N/A'}</strong></div>
                    <div>Anomaly Score: <strong className="mono">{comparison.after?.anomaly_score != null ? comparison.after.anomaly_score : 'UNAVAILABLE'}</strong></div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: '12px', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                Post-maintenance verification data unavailable.
              </div>
            )}
          </div>

          {/* Audit Trail Ledger */}
          {selectedOrder.audit_logs && selectedOrder.audit_logs.length > 0 && (
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px' }}>
                Operational Audit History
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {selectedOrder.audit_logs.map((log) => (
                  <div
                    key={log.id}
                    style={{
                      padding: '8px 12px',
                      background: 'var(--bg-main)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-subtle)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      fontSize: '12px'
                    }}
                  >
                    <div>
                      <strong style={{ color: 'var(--color-primary)' }}>{log.event_type}</strong> by <span>{log.actor}</span>
                      {log.notes && <span style={{ color: 'var(--text-secondary)', marginLeft: '8px' }}>&bull; {log.notes}</span>}
                    </div>
                    <span className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : ''}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Assign Modal */}
      {isAssignModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card" style={{ width: '420px', maxWidth: '90%' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '12px' }}>Assign Maintenance Technician</h3>
            <form onSubmit={handleAssign}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Technician / Team Identifier</label>
                <input
                  type="text"
                  placeholder="Enter technician or team identifier (e.g. Lead Tech, Avionics Team)"
                  value={assigneeName}
                  onChange={(e) => setAssigneeName(e.target.value)}
                  required
                  style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                />
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsAssignModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm">Confirm Assignment</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Verification Modal */}
      {isVerifyModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card" style={{ width: '480px', maxWidth: '90%' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '12px' }}>Maintenance Verification Sign-Off</h3>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '14px' }}>
              Confirm whether post-maintenance inspection and sensor telemetry have resolved the degradation condition.
            </p>
            <form onSubmit={handleVerify}>
              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Verification Outcome</label>
                <select
                  value={verifyOutcome}
                  onChange={(e) => setVerifyOutcome(e.target.value)}
                  style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                >
                  <option value="RESOLVED">Resolved (Maintenance succeeded & telemetry normalized)</option>
                  <option value="PARTIALLY_RESOLVED">Partially Resolved (Further monitoring required)</option>
                  <option value="NOT_RESOLVED">Not Resolved (Issue persists)</option>
                  <option value="UNABLE_TO_VERIFY">Unable to Verify (Telemetry or sensor unavailable)</option>
                </select>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Verification Inspection Notes</label>
                <textarea
                  placeholder="Enter physical or borescope inspection notes and observations..."
                  value={verifyNotes}
                  onChange={(e) => setVerifyNotes(e.target.value)}
                  rows={3}
                  style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '13px' }}
                />
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsVerifyModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm" style={{ background: '#059669', borderColor: '#059669' }}>
                  Submit Verification
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Create Work Order Modal */}
      {isCreateModalOpen && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div className="card" style={{ width: '480px', maxWidth: '90%' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, marginBottom: '12px' }}>Create Maintenance Work Order</h3>
            <form onSubmit={handleCreateNew}>
              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Target Machine Unit</label>
                <select
                  value={createForm.machine_id}
                  onChange={(e) => setCreateForm({ ...createForm, machine_id: e.target.value })}
                  style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                >
                  {(machines.length > 0 ? machines : [{ id: 1, unit_number: 1, name: 'Turbofan Engine #001' }]).map((m) => (
                    <option key={m.id} value={m.id}>
                      Unit #{String(m.unit_number || m.id).padStart(3, '0')} - {m.name}
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Work Order Title</label>
                <input
                  type="text"
                  placeholder="e.g. Inspect LPT Stator Vanes"
                  value={createForm.title}
                  onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                  required
                  style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                />
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Target Subsystem</label>
                <input
                  type="text"
                  placeholder="e.g. Low Pressure Turbine"
                  value={createForm.affected_subsystem}
                  onChange={(e) => setCreateForm({ ...createForm, affected_subsystem: e.target.value })}
                  required
                  style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                />
              </div>

              <div style={{ marginBottom: '12px' }}>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Prescriptive Action</label>
                <textarea
                  placeholder="e.g. Perform borescope inspection on Low Pressure Turbine stator vanes."
                  value={createForm.recommended_action}
                  onChange={(e) => setCreateForm({ ...createForm, recommended_action: e.target.value })}
                  required
                  rows={2}
                  style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', marginBottom: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Priority</label>
                  <select
                    value={createForm.priority}
                    onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                    style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, marginBottom: '4px' }}>Assigned To (Optional)</label>
                  <input
                    type="text"
                    placeholder="Unassigned"
                    value={createForm.assigned_to}
                    onChange={(e) => setCreateForm({ ...createForm, assigned_to: e.target.value })}
                    style={{ width: '100%', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsCreateModalOpen(false)}>Cancel</button>
                <button type="submit" className="btn btn-primary btn-sm">Create Work Order</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Ground-Truth Maintenance Outcome Modal */}
      {isOutcomeModalOpen && selectedOrder && (
        <GroundTruthOutcomeModal
          workOrder={selectedOrder}
          onClose={() => setIsOutcomeModalOpen(false)}
          onSuccess={() => {
            setIsOutcomeModalOpen(false);
            fetchData();
          }}
        />
      )}
    </div>
  );
}

