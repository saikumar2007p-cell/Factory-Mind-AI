import React, { useState } from 'react';
import { FileText, Eye, X, BookOpen, Layers, Cpu, CheckCircle2 } from 'lucide-react';

export default function DocumentsView() {
  const [selectedDoc, setSelectedDoc] = useState(null);

  const docs = [
    {
      id: 'cmapss-spec',
      title: 'NASA C-MAPSS Turbofan Simulation Specification (FD001)',
      type: 'Specification',
      size: '2.4 MB',
      date: '2026-08-18',
      content: {
        summary: 'Modular Aero-Propulsion System Simulation (C-MAPSS) Sub-dataset FD001 reference standard.',
        sections: [
          {
            heading: 'Dataset Characteristics',
            body: 'NASA C-MAPSS FD001 simulates run-to-failure degradation trajectories for 100 high-bypass turbofan engines (CF6-80C2 class). Operational conditions: Sea Level (1 condition), single fault mode (High Pressure Compressor degradation).'
          },
          {
            heading: 'Channel Taxonomy & Format',
            body: '26 space-delimited floating-point columns: unit_number, time_in_cycles, 3 operational settings (altitude, mach number, sea-level bleed), and 21 continuous sensor readings (s_1 to s_21).'
          },
          {
            heading: 'Degradation Model',
            body: 'Piecewise linear Remaining Useful Life (RUL) with early-life plateau clipped at 125 cycles to prevent premature alarm escalation before active degradation initiation.'
          }
        ]
      }
    },
    {
      id: 'architecture-blueprint',
      title: 'FactoryMind AI Architecture & Closed-Loop ML Blueprint',
      type: 'Architecture',
      size: '184 KB',
      date: '2026-08-18',
      content: {
        summary: 'End-to-end industrial intelligence architecture with closed-loop maintenance state machine.',
        sections: [
          {
            heading: 'Core Prognostic Pipeline',
            body: 'MONITOR → PREDICT → DIAGNOSE → PRIORITIZE → PLAN → EXECUTE → VERIFY → LEARN → SECURE → RELEASE'
          },
          {
            heading: 'Model Invariants',
            body: 'LightGBM Regressor (RUL prediction, RMSE 13.41) + Scikit-Learn Isolation Forest (200 trees, 5% contamination). Enforces strict 21-channel physical sensor validation.'
          },
          {
            heading: 'Maintenance Lifecycle State Machine',
            body: 'Strict 5-stage transition path: OPEN → ASSIGNED → IN_PROGRESS → VERIFICATION_REQUIRED → VERIFIED. State jumps return HTTP 422 Unprocessable Entity. Verified records are permanently immutable.'
          }
        ]
      }
    },
    {
      id: 'sensor-metadata',
      title: 'Turbofan CF6-80C2 Sensor Metadata & Operational Baselines',
      type: 'Telemetry Schema',
      size: '8.2 KB',
      date: '2026-08-18',
      content: {
        summary: 'Canonical 21-channel turbofan sensor metadata, engineering units, and baseline nominal values.',
        sections: [
          {
            heading: 'Thermal Sensors',
            body: 'T24 (LPC Outlet, 642.0 °R), T30 (HPC Outlet, 1587.0 °R), T50 (LPT Outlet, 1403.2 °R). Key prognostic indicators for thermal degradation and hot-section distress.'
          },
          {
            heading: 'Pressure & Flow Sensors',
            body: 'P30 (HPC Outlet, 554.0 psia), Ps30 (Static HPC Pressure, 47.4 psia), phi (Fuel Flow Ratio, 521.8 pps/psi), BPR (Bypass Ratio, 8.41).'
          },
          {
            heading: 'Rotor Speeds & Coolant Bleed',
            body: 'Nf (Physical Fan, 2388.0 rpm), Nc (Physical Core, 9046.0 rpm), W31 (HPT Coolant Bleed, 39.0 lbm/s), W32 (LPT Coolant Bleed, 23.4 lbm/s).'
          }
        ]
      }
    }
  ];

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">Technical Documentation & Schematics</h2>
        <p className="page-description">Turbofan reference standards, model validation metrics, and operational guidelines.</p>
      </div>

      <div className="card">
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Document Title</th>
                <th>Format</th>
                <th>File Size</th>
                <th>Updated</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {docs.map((doc) => (
                <tr key={doc.id}>
                  <td style={{ fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <FileText size={16} color="#2563eb" />
                    {doc.title}
                  </td>
                  <td><span className="badge badge-offline">{doc.type}</span></td>
                  <td className="mono" style={{ color: 'var(--text-muted)' }}>{doc.size}</td>
                  <td className="mono" style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{doc.date}</td>
                  <td>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => setSelectedDoc(doc)}
                    >
                      <Eye size={12} /> View
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Document Viewer Modal */}
      {selectedDoc && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, padding: '20px' }}>
          <div className="card" style={{ width: '680px', maxWidth: '100%', maxHeight: '85vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <BookOpen size={18} color="var(--brand-primary)" />
                  <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0 }}>{selectedDoc.title}</h3>
                </div>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                  Format: <strong>{selectedDoc.type}</strong> &bull; Size: {selectedDoc.size} &bull; Updated: {selectedDoc.date}
                </span>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => setSelectedDoc(null)}>
                <X size={14} /> Close
              </button>
            </div>

            <div style={{ padding: '10px 14px', background: 'var(--bg-card-secondary)', borderRadius: '6px', marginBottom: '16px', fontSize: '13px', color: 'var(--text-secondary)' }}>
              {selectedDoc.content.summary}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {selectedDoc.content.sections.map((sec, idx) => (
                <div key={idx} style={{ background: 'var(--bg-main)', padding: '14px', borderRadius: '6px', border: '1px solid var(--border-subtle)' }}>
                  <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <CheckCircle2 size={14} color="#10b981" />
                    {sec.heading}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                    {sec.body}
                  </div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '18px' }}>
              <button className="btn btn-primary btn-sm" onClick={() => setSelectedDoc(null)}>
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
