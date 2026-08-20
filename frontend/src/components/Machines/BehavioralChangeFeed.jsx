import React, { useState, useEffect } from 'react';
import {
  Activity,
  AlertCircle,
  CheckCircle2,
  HelpCircle,
  Search,
  Sliders,
  Radio,
  FileCheck,
  Clock,
  ArrowRight,
  TrendingDown
} from 'lucide-react';
import {
  getBehavioralChanges,
  investigateBehavioralChange
} from '../../services/api';

export default function BehavioralChangeFeed({ machineId = 1, userRole = 'OPERATOR' }) {
  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Investigation Modal State
  const [investigateModalChange, setInvestigateModalChange] = useState(null);
  const [changeType, setChangeType] = useState('MACHINE_ANOMALY');
  const [rootCause, setRootCause] = useState('');
  const [notes, setNotes] = useState('');
  const [closeStatus, setCloseStatus] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  const fetchChanges = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getBehavioralChanges(machineId);
      setChanges(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load behavioral changes');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChanges();
  }, [machineId]);

  const handleInvestigateSubmit = async (e) => {
    e.preventDefault();
    if (!investigateModalChange) return;
    if (!rootCause.trim()) {
      alert('Root cause description is required.');
      return;
    }
    try {
      setSubmitting(true);
      await investigateBehavioralChange(investigateModalChange.id, {
        change_type: changeType,
        root_cause: rootCause.trim(),
        investigator: 'Field Engineer',
        notes: notes.trim() || null,
        close: closeStatus
      });
      setInvestigateModalChange(null);
      setRootCause('');
      setNotes('');
      setActionSuccess('Investigation recorded. Change classification updated.');
      fetchChanges();
    } catch (err) {
      alert(`Failed to record investigation: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const pendingCount = changes.filter(c => c.investigation_status === 'PENDING').length;

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
        <div>
          <div className="flex items-center gap-2">
            <Activity className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-bold text-white tracking-wide">
              Behavioral Change & Drift Detection
            </h2>
            {pendingCount > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                {pendingCount} Pending Review
              </span>
            )}
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Statistically detected sensor shifts. Causally neutral until verified by engineering investigation.
          </p>
        </div>
      </div>

      {actionSuccess && (
        <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {actionSuccess}
        </div>
      )}

      {/* Changes Feed */}
      <div className="mt-6 space-y-3">
        {loading ? (
          <div className="p-8 text-center text-gray-500 text-sm">Loading behavioral observations...</div>
        ) : changes.length === 0 ? (
          <div className="p-8 bg-gray-900/30 border border-gray-800/80 rounded-xl text-center text-gray-400 text-sm">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto mb-2 opacity-60" />
            No behavioral shifts detected. Sensor signals match trained nominal distribution.
          </div>
        ) : (
          changes.map((ch) => (
            <div
              key={ch.id}
              className={`p-4 rounded-xl border transition ${
                ch.investigation_status === 'PENDING'
                  ? 'bg-gray-900/70 border-cyan-500/30'
                  : 'bg-gray-950/40 border-gray-800'
              }`}
            >
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${
                      ch.investigation_status === 'PENDING'
                        ? 'bg-cyan-500/10 text-cyan-400 border border-cyan-500/30'
                        : 'bg-gray-800 text-gray-400'
                    }`}
                  >
                    <Sliders className="w-4 h-4" />
                  </div>

                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-white text-sm">
                        {ch.drift_method} Drift Detected (Magnitude: {ch.drift_magnitude?.toFixed(2)})
                      </span>
                      {ch.investigation_status === 'PENDING' ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30 font-medium">
                          PENDING INVESTIGATION
                        </span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 font-medium">
                          {ch.change_type || 'INVESTIGATED'}
                        </span>
                      )}
                    </div>

                    <p className="text-xs text-gray-400 mt-1">
                      Affected Sensors: <span className="text-gray-300">{ch.affected_sensors?.join(', ') || 'N/A'}</span> • Cycle: {ch.cycle || '—'} • Detected: {new Date(ch.detected_at).toLocaleString()}
                    </p>

                    {ch.root_cause && (
                      <div className="mt-2 text-xs bg-gray-900/80 p-2 rounded border border-gray-800 text-gray-300">
                        <span className="text-cyan-400 font-semibold">Root Cause:</span> {ch.root_cause} (Investigated by {ch.investigator})
                      </div>
                    )}
                  </div>
                </div>

                <div>
                  {ch.investigation_status === 'PENDING' && userRole !== 'VIEWER' && (
                    <button
                      onClick={() => setInvestigateModalChange(ch)}
                      className="px-3.5 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-medium transition shadow flex items-center gap-1.5"
                    >
                      <Search className="w-3.5 h-3.5" />
                      Investigate
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Investigation Modal */}
      {investigateModalChange && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-2 text-cyan-400 mb-2">
              <Search className="w-5 h-5" />
              <h3 className="text-lg font-bold text-white">Record Drift Investigation</h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Classify the causal root of this sensor shift to prevent treating environmental or sensor changes as machine wear.
            </p>

            <form onSubmit={handleInvestigateSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Causal Classification *
                </label>
                <select
                  value={changeType}
                  onChange={(e) => setChangeType(e.target.value)}
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="MACHINE_ANOMALY">MACHINE_ANOMALY (Genuine physical degradation)</option>
                  <option value="SENSOR_ISSUE">SENSOR_ISSUE (Sensor drift, calibration error, dropout)</option>
                  <option value="OPERATING_CONDITION">OPERATING_CONDITION (Load, speed, or ambient weather shift)</option>
                  <option value="DATA_QUALITY">DATA_QUALITY (Transmission glitch, timestamp misalignment)</option>
                  <option value="UNKNOWN">UNKNOWN (Further observation required)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Root Cause Finding *
                </label>
                <textarea
                  value={rootCause}
                  onChange={(e) => setRootCause(e.target.value)}
                  placeholder="e.g. Ambient temperature increased by 15°C under high summer load"
                  rows={3}
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Extended Engineering Notes
                </label>
                <input
                  type="text"
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="e.g. Scheduled sensor recalibration for next maintenance cycle"
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="closeChange"
                  checked={closeStatus}
                  onChange={(e) => setCloseStatus(e.target.checked)}
                  className="rounded border-gray-700 text-cyan-600 focus:ring-cyan-500 bg-gray-950"
                />
                <label htmlFor="closeChange" className="text-xs text-gray-300">
                  Mark investigation as CLOSED
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setInvestigateModalChange(null)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-sm font-medium transition"
                >
                  {submitting ? 'Recording...' : 'Record Finding'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
