/**
 * frontend/src/components/Datasets/DatasetSelector.jsx
 *
 * Multi-machine dataset/equipment selector for FactoryMind AI.
 * Shows all available datasets with real source attribution and ML capabilities.
 * Zero Fabrication: Shows only actual sensors and supported tasks per dataset.
 */

import React, { useState, useEffect } from 'react';
import {
  Database, Server, Cpu, Activity, AlertCircle, CheckCircle2,
  Download, ExternalLink, Settings2, Gauge, Waves, Cog
} from 'lucide-react';
import { getDatasets, getDatasetStatus, getDatasetSensors, getDatasetTasks } from '../../services/api';

const EQUIPMENT_ICONS = {
  TURBOFAN_ENGINE: <Cpu size={28} />,
  INDUSTRIAL_GEARBOX: <Cog size={28} />,
  VALVE_PRESSURE_SYSTEM: <Gauge size={28} />,
  CUSTOM: <Server size={28} />,
};

const EQUIPMENT_COLORS = {
  TURBOFAN_ENGINE: { bg: '#eff6ff', border: '#3b82f6', text: '#1e40af', icon: '#3b82f6' },
  INDUSTRIAL_GEARBOX: { bg: '#fef3c7', border: '#f59e0b', text: '#92400e', icon: '#f59e0b' },
  VALVE_PRESSURE_SYSTEM: { bg: '#f0fdf4', border: '#22c55e', text: '#166534', icon: '#22c55e' },
  CUSTOM: { bg: '#f8fafc', border: '#64748b', text: '#334155', icon: '#64748b' },
};

export default function DatasetSelector({ onSelectDataset, activeDatasetId, userRole }) {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [sensorCache, setSensorCache] = useState({});

  useEffect(() => {
    loadDatasets();
  }, []);

  const loadDatasets = async () => {
    try {
      setLoading(true);
      const data = await getDatasets();
      setDatasets(data || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleExpand = async (datasetId) => {
    if (expandedId === datasetId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(datasetId);
    if (!sensorCache[datasetId]) {
      try {
        const sensors = await getDatasetSensors(datasetId);
        setSensorCache(prev => ({ ...prev, [datasetId]: sensors }));
      } catch (e) {
        console.warn('Failed to load sensors:', e);
      }
    }
  };

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center', color: '#64748b' }}>
        <Database size={32} style={{ opacity: 0.3, marginBottom: 12 }} />
        <div>Loading datasets...</div>
      </div>
    );
  }

  return (
    <div style={{ padding: '0' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20,
        padding: '14px 18px', background: '#f8fafc', borderRadius: 10,
        border: '1px solid #e2e8f0'
      }}>
        <Database size={18} color="#3b82f6" />
        <div>
          <div style={{ fontWeight: 700, fontSize: 14, color: '#0f172a' }}>
            Dataset / Equipment Registry
          </div>
          <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>
            {datasets.length} registered datasets • Select one to view its data
          </div>
        </div>
      </div>

      {error && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          padding: '10px 14px', background: '#fef2f2', borderRadius: 8,
          border: '1px solid #fca5a5', marginBottom: 16,
          fontSize: 12, color: '#991b1b'
        }}>
          <AlertCircle size={14} /> {error}
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {datasets.map(ds => {
          const colors = EQUIPMENT_COLORS[ds.equipmentType] || EQUIPMENT_COLORS.CUSTOM;
          const icon = EQUIPMENT_ICONS[ds.equipmentType] || EQUIPMENT_ICONS.CUSTOM;
          const isActive = activeDatasetId === ds.datasetId;
          const isExpanded = expandedId === ds.datasetId;
          const isReady = ds.downloadStatus === 'READY';

          return (
            <div key={ds.datasetId} style={{
              border: `2px solid ${isActive ? colors.border : '#e2e8f0'}`,
              borderRadius: 12,
              background: isActive ? colors.bg : '#fff',
              overflow: 'hidden',
              transition: 'all 0.2s ease',
              boxShadow: isActive ? `0 4px 12px ${colors.border}25` : '0 1px 3px rgba(0,0,0,0.06)',
            }}>
              {/* Header */}
              <div
                onClick={() => handleExpand(ds.datasetId)}
                style={{
                  padding: '16px 18px',
                  display: 'flex', alignItems: 'center', gap: 14,
                  cursor: 'pointer',
                }}
              >
                <div style={{
                  width: 52, height: 52, borderRadius: 10,
                  background: `${colors.border}15`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: colors.icon, flexShrink: 0,
                }}>
                  {icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 700, fontSize: 14, color: '#0f172a' }}>{ds.datasetName}</span>
                    {isReady && <CheckCircle2 size={14} color="#22c55e" />}
                    {!isReady && <Download size={14} color="#94a3b8" />}
                  </div>
                  <div style={{ fontSize: 12, color: '#64748b', marginTop: 3 }}>
                    <strong>{ds.machineType}</strong> — {ds.equipmentType.replace(/_/g, ' ')}
                  </div>
                  <div style={{ display: 'flex', gap: 8, marginTop: 6, flexWrap: 'wrap' }}>
                    <span style={tagStyle('#e0f2fe', '#0369a1')}>{ds.sourceType.replace(/_/g, ' ')}</span>
                    <span style={tagStyle('#f0fdf4', '#166534')}>{ds.dataMode}</span>
                    <span style={tagStyle(isReady ? '#dcfce7' : '#fef3c7', isReady ? '#166534' : '#92400e')}>
                      {isReady ? 'READY' : ds.downloadStatus.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
                {isReady && (
                  <button
                    onClick={(e) => { e.stopPropagation(); onSelectDataset?.(ds.datasetId); }}
                    disabled={isActive}
                    style={{
                      padding: '8px 16px', borderRadius: 8,
                      background: isActive ? '#94a3b8' : colors.border,
                      color: '#fff', border: 'none', cursor: isActive ? 'default' : 'pointer',
                      fontSize: 12, fontWeight: 700, flexShrink: 0,
                    }}
                  >
                    {isActive ? 'Active' : 'Select'}
                  </button>
                )}
              </div>

              {/* Expanded details */}
              {isExpanded && (
                <div style={{
                  padding: '0 18px 16px',
                  borderTop: '1px solid #e2e8f0',
                  paddingTop: 14,
                }}>
                  <div style={{ fontSize: 12, color: '#475569', marginBottom: 10, lineHeight: 1.5 }}>
                    {ds.description}
                  </div>

                  {/* Source */}
                  <div style={sectionTitle}>Data Source</div>
                  <div style={{ fontSize: 12, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                    <ExternalLink size={12} />
                    <span>{ds.sourceName}</span> —
                    <a href={ds.sourceUrl} target="_blank" rel="noopener noreferrer"
                       style={{ color: '#3b82f6', textDecoration: 'underline' }}>
                      Official Source
                    </a>
                  </div>
                  <div style={{ fontSize: 11, color: '#94a3b8', marginBottom: 14 }}>
                    License: {ds.license}
                  </div>

                  {/* Sensors */}
                  <div style={sectionTitle}>Available Sensors</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
                    {(sensorCache[ds.datasetId] || ds.availableSensors || []).map((s, i) => {
                      const name = typeof s === 'string' ? s : s.name;
                      const unit = typeof s === 'object' ? s.unit : '';
                      return (
                        <span key={i} style={{
                          fontSize: 10, padding: '3px 8px', borderRadius: 4,
                          background: '#f1f5f9', color: '#334155', border: '1px solid #e2e8f0',
                          fontFamily: 'monospace',
                        }}>
                          {name}{unit ? ` (${unit})` : ''}
                        </span>
                      );
                    })}
                  </div>

                  {/* Supported ML Tasks */}
                  <div style={sectionTitle}>Supported ML Tasks</div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
                    {(ds.supportedTasks || []).map((task, i) => (
                      <span key={i} style={{
                        fontSize: 10, padding: '3px 8px', borderRadius: 4,
                        background: '#ede9fe', color: '#5b21b6', fontWeight: 600,
                        border: '1px solid #ddd6fe',
                      }}>
                        {task.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>

                  {/* Fault Labels */}
                  {ds.faultLabels && ds.faultLabels.length > 0 && (
                    <>
                      <div style={sectionTitle}>Fault / Target Labels</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                        {ds.faultLabels.map((label, i) => (
                          <span key={i} style={{
                            fontSize: 10, padding: '3px 8px', borderRadius: 4,
                            background: '#fef2f2', color: '#991b1b', fontWeight: 600,
                            border: '1px solid #fca5a5',
                          }}>
                            {label.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </>
                  )}

                  {/* Not Downloaded Warning */}
                  {!isReady && (
                    <div style={{
                      marginTop: 14, padding: '10px 14px',
                      background: '#fef3c7', borderRadius: 8,
                      border: '1px solid #fbbf24',
                      fontSize: 11, color: '#92400e',
                      display: 'flex', alignItems: 'center', gap: 8,
                    }}>
                      <Download size={14} />
                      <div>
                        <strong>Manual download required.</strong> Download from the official source
                        and place files in the appropriate <code>data/raw/</code> directory.
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

const tagStyle = (bg, color) => ({
  fontSize: 9, fontWeight: 700, padding: '2px 7px', borderRadius: 4,
  background: bg, color: color, textTransform: 'uppercase', letterSpacing: '0.3px',
});

const sectionTitle = {
  fontSize: 11, fontWeight: 700, color: '#475569', marginBottom: 6,
  textTransform: 'uppercase', letterSpacing: '0.5px',
};
