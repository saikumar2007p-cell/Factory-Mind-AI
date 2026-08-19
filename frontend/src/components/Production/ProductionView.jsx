import React from 'react';
import { Activity, Gauge, TrendingUp, Info } from 'lucide-react';

export default function ProductionView() {
  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">Production & Test Cell Operations</h2>
        <p className="page-description">Operational throughput across test cells executing continuous NASA C-MAPSS degradation simulations.</p>
      </div>

      <div
        style={{
          backgroundColor: '#eff6ff',
          border: '1px solid #bfdbfe',
          borderRadius: '8px',
          padding: '12px 16px',
          marginBottom: '20px',
          display: 'flex',
          gap: '12px',
          alignItems: 'center'
        }}
      >
        <Info size={18} color="#2563eb" style={{ flexShrink: 0 }} />
        <div style={{ fontSize: '12px', color: '#1e3a8a', lineHeight: 1.4 }}>
          <strong>Data Source Mode:</strong> "NASA C-MAPSS FD001 — Simulation". Real-time plant floor OEE requires active industrial MQTT or REST connectors.
        </div>
      </div>

      <div className="metrics-row">
        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Active Test Engine</span>
            <Activity size={18} color="var(--status-normal)" />
          </div>
          <div className="metric-value">Unit #001</div>
          <div className="metric-sub">NASA C-MAPSS FD001 Active Simulation</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Overall Equipment Effectiveness (OEE)</span>
            <Gauge size={18} color="var(--text-muted)" />
          </div>
          <div className="metric-value" style={{ fontSize: '18px', color: 'var(--text-muted)', fontWeight: 600, padding: '4px 0' }}>Not Configured</div>
          <div className="metric-sub">Real Industrial Data: Not Configured</div>
        </div>

        <div className="card metric-card">
          <div className="metric-header">
            <span className="metric-title">Dataset Throughput</span>
            <TrendingUp size={18} color="var(--status-ai)" />
          </div>
          <div className="metric-value">20,631</div>
          <div className="metric-sub">Total training cycle rows</div>
        </div>
      </div>
    </div>
  );
}
