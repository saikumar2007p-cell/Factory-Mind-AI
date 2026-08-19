import React, { useState } from 'react';
import {
  BrainCircuit,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Wrench,
  Cpu,
  ArrowRight,
  Plus,
  Search,
  Loader2,
  RefreshCw,
  Activity
} from 'lucide-react';
import { createWorkOrder } from '../../services/api';

export default function InsightsView({
  machines = [],
  onSelectMachine,
  onRunDiagnostics,
  diagnosticsLoading,
  latestDiagnosis,
  userRole = 'ADMIN'
}) {
  const [search, setSearch] = useState('');
  const [filterStatus, setFilterStatus] = useState('ALL');
  const [activeMachineId, setActiveMachineId] = useState(latestDiagnosis?.machine_id || 1);

  // Filter machines based on search & status
  const filteredMachines = machines.filter(m => {
    const matchesSearch = search === '' || 
      String(m.unit_number || m.id).includes(search) || 
      `unit #${m.unit_number}`.toLowerCase().includes(search.toLowerCase());
    
    if (filterStatus === 'WARNING') return matchesSearch && (m.status === 'WARNING' || m.status === 'MONITORING' || m.risk_level === 'WARNING');
    if (filterStatus === 'CRITICAL') return matchesSearch && (m.status === 'CRITICAL' || m.risk_level === 'CRITICAL');
    if (filterStatus === 'OPERATIONAL') return matchesSearch && (m.status === 'OPERATIONAL' || m.risk_level === 'NORMAL');
    return matchesSearch;
  });

  const handleDiagnoseClick = (id) => {
    setActiveMachineId(id);
    onRunDiagnostics(id);
  };

  const getStatusBadge = (lvl) => {
    switch (lvl) {
      case 'CRITICAL': return <span className="badge badge-critical" style={{ fontSize: '10px' }}>Critical</span>;
      case 'WARNING':
      case 'MONITOR': return <span className="badge badge-warning" style={{ fontSize: '10px' }}>Warning</span>;
      default: return <span className="badge badge-normal" style={{ fontSize: '10px' }}>Normal</span>;
    }
  };

  return (
    <div>
      {/* Hero Intelligence Card */}
      <div 
        className="card" 
        style={{ 
          marginBottom: '24px', 
          borderLeft: '4px solid #2563eb',
          position: 'relative',
          overflow: 'hidden'
        }}
      >
        {diagnosticsLoading && (
          <div style={{
            position: 'absolute',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.75)',
            backdropFilter: 'blur(4px)',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10,
            gap: '12px'
          }}>
            <Loader2 size={32} color="#3b82f6" className="pulse" style={{ animation: 'spin 1s linear infinite' }} />
            <div style={{ fontWeight: 600, color: '#f8fafc', fontSize: '14px' }}>
              Executing Grounded AI Diagnostics for Unit #{String(activeMachineId).padStart(3, '0')}...
            </div>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>
              Constructing 21-channel thermodynamic evidence & evaluating prognostics
            </div>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <BrainCircuit size={22} color="var(--status-ai)" />
            <div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0 }}>Active Root Cause Diagnostic Assessment</h3>
              <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                Target: Turbofan Unit #{String(latestDiagnosis?.machine_id || activeMachineId || 1).padStart(3, '0')}
              </span>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button 
              className="btn btn-secondary btn-sm"
              onClick={() => handleDiagnoseClick(latestDiagnosis?.machine_id || activeMachineId || 1)}
              disabled={diagnosticsLoading}
              title="Refresh AI Analysis"
            >
              <RefreshCw size={13} className={diagnosticsLoading ? 'spin' : ''} />
              Re-Analyze
            </button>
            <span className="badge badge-ai">
              {latestDiagnosis?.model_used || 'Gemini 3.6 Flash'}
            </span>
          </div>
        </div>

        {latestDiagnosis ? (
          <div>
            <div style={{ 
              fontSize: '15px', 
              fontWeight: 700, 
              color: 'var(--text-primary)', 
              marginBottom: '12px',
              padding: '12px 14px',
              background: 'rgba(37, 99, 235, 0.08)',
              borderRadius: '6px',
              border: '1px solid rgba(37, 99, 235, 0.2)'
            }}>
              {latestDiagnosis.summary}
            </div>

            {/* 4 Pillars of Grounded AI */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', margin: '16px 0' }}>
              {/* 1. Observed Telemetry */}
              <div style={{ background: 'var(--bg-card-secondary)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Activity size={13} color="#3b82f6" /> 1. Observed Evidence
                </div>
                <ul style={{ paddingLeft: '16px', fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                  {latestDiagnosis.evidence?.map((ev, i) => (
                    <li key={i} style={{ marginBottom: '6px', lineHeight: 1.4 }}>{ev}</li>
                  ))}
                </ul>
              </div>

              {/* 2. Possible Cause */}
              <div style={{ background: 'var(--bg-card-secondary)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertTriangle size={13} color="#f59e0b" /> 2. Possible Subsystem Cause
                </div>
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  {latestDiagnosis.risk_explanation}
                </div>
              </div>

              {/* 3. Recommended Action */}
              <div style={{ background: 'rgba(37, 99, 235, 0.06)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid rgba(37, 99, 235, 0.2)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', gap: '12px' }}>
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Wrench size={13} /> 3. Recommended Work Order
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-primary)', fontWeight: 600, lineHeight: 1.4 }}>
                    {latestDiagnosis.recommended_action}
                  </div>
                </div>

                {userRole === 'VIEWER' ? (
                  <div style={{ padding: '4px 8px', background: 'rgba(0,0,0,0.2)', borderRadius: '4px', fontSize: '11px', color: '#94a3b8' }}>
                    👁️ Viewer Mode (Read-Only)
                  </div>
                ) : (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={async () => {
                      try {
                        const res = await createWorkOrder({
                          machine_id: latestDiagnosis.machine_id || activeMachineId || 1,
                          title: `Prescriptive RCA: ${latestDiagnosis.summary || 'Inspect Turbofan Core'}`,
                          recommended_action: latestDiagnosis.recommended_action,
                          affected_subsystem: 'Turbofan Core',
                          priority: 'HIGH',
                          risk_level: 'WARNING',
                          observed_evidence: { evidence: latestDiagnosis.evidence || [] },
                          source_recommendation_id: latestDiagnosis.id || null
                        });
                        alert(`Work Order ${res.work_order_code} successfully created and dispatched to maintenance queue!`);
                      } catch (err) {
                        const msg = err.status === 403 ? 'Permission denied — Operator or Admin authorization required.' : (err.detail || err.message);
                        alert(`Error creating work order: ${msg}`);
                      }
                    }}
                  >
                    <Plus size={14} /> Create Work Order
                  </button>
                )}
              </div>

              {/* 4. Confidence & Boundaries */}
              <div style={{ background: 'var(--bg-card-secondary)', padding: '14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <Sparkles size={13} color="#10b981" /> 4. Reliability & Boundaries
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                  <span className="badge badge-normal">Confidence: {latestDiagnosis.confidence}</span>
                  <span className="badge badge-ai">{latestDiagnosis.source}</span>
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', lineHeight: 1.4 }}>
                  {latestDiagnosis.limitations}
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="empty-state" style={{ padding: '32px' }}>
            <BrainCircuit size={40} className="empty-icon" />
            <div className="empty-title">Select a Machine to Generate Diagnostics</div>
            <div className="empty-desc">Run grounded Root Cause Analysis on any of the monitored turbofan engines below.</div>
          </div>
        )}
      </div>

      {/* Machine Diagnostics Selector */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
          <div>
            <h3 style={{ fontSize: '15px', fontWeight: 700, margin: 0 }}>Request Diagnostics on Monitored Engine Fleet</h3>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
              Click "Diagnose" on any machine to generate evidence-grounded AI prognostics.
            </span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            {/* Search Input */}
            <div className="search-input-wrapper" style={{ minWidth: '180px' }}>
              <Search size={14} className="search-icon" />
              <input
                type="text"
                className="search-input"
                placeholder="Search Unit #..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                style={{ fontSize: '12px', padding: '6px 10px 6px 30px' }}
              />
            </div>

            {/* Filter Buttons */}
            <div style={{ display: 'flex', gap: '4px' }}>
              {['ALL', 'CRITICAL', 'WARNING', 'OPERATIONAL'].map((f) => (
                <button
                  key={f}
                  className={`btn btn-xs ${filterStatus === f ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setFilterStatus(f)}
                  style={{ fontSize: '11px', padding: '4px 8px' }}
                >
                  {f.charAt(0) + f.slice(1).toLowerCase()}
                </button>
              ))}
            </div>
          </div>
        </div>

        {filteredMachines.length === 0 ? (
          <div className="empty-state" style={{ padding: '24px' }}>
            <div className="empty-title">No Matching Engines Found</div>
            <div className="empty-desc">No machines match the active search query or filter.</div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(210px, 1fr))', gap: '12px', maxHeight: '420px', overflowY: 'auto', paddingRight: '4px' }}>
            {filteredMachines.map((m) => {
              const uNum = m.unit_number || m.id;
              const isActive = (latestDiagnosis?.machine_id === m.id) || (activeMachineId === m.id);
              const cycleVal = m.current_cycle || m.time_in_cycles || m.cycle || 1;
              const statusLvl = m.risk_level || m.status || 'NORMAL';

              return (
                <div
                  key={m.id}
                  style={{
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    border: isActive ? '2px solid #3b82f6' : '1px solid var(--border-subtle)',
                    backgroundColor: isActive ? 'rgba(59, 130, 246, 0.08)' : 'var(--bg-card-secondary)',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    transition: 'all 0.15s ease'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                      <span className="mono" style={{ fontSize: '13px', fontWeight: 700 }}>
                        UNIT #{String(uNum).padStart(3, '0')}
                      </span>
                      {getStatusBadge(statusLvl)}
                    </div>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      Cycle {cycleVal} &bull; RUL: {m.current_rul != null ? m.current_rul : 'N/A'}
                    </div>
                  </div>

                  <button
                    className={`btn btn-sm ${isActive ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => handleDiagnoseClick(m.id)}
                    disabled={diagnosticsLoading}
                    style={{ fontSize: '11px', padding: '5px 10px' }}
                  >
                    {diagnosticsLoading && activeMachineId === m.id ? (
                      <Loader2 size={12} className="spin" />
                    ) : (
                      'Diagnose'
                    )}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
