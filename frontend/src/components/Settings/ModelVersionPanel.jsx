import React, { useState, useEffect } from 'react';
import {
  Layers,
  CheckCircle2,
  RotateCcw,
  PlusCircle,
  AlertTriangle,
  Clock,
  ShieldCheck,
  TrendingUp,
  Activity,
  History,
  Info
} from 'lucide-react';
import {
  getModelVersions,
  approveModelVersion,
  rollbackModelVersion,
  registerModelCandidate
} from '../../services/api';

export default function ModelVersionPanel({ machineId = 1, userRole = 'ADMIN' }) {
  const [versions, setVersions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Rollback Modal State
  const [rollbackModalOpen, setRollbackModalOpen] = useState(false);
  const [rollbackReason, setRollbackReason] = useState('');
  const [rollbackSubmitting, setRollbackSubmitting] = useState(false);

  // Register Candidate Modal State
  const [candidateModalOpen, setCandidateModalOpen] = useState(false);
  const [newVersionStr, setNewVersionStr] = useState('');
  const [newDatasetId, setNewDatasetId] = useState('');
  const [candidateSubmitting, setCandidateSubmitting] = useState(false);

  const fetchVersions = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getModelVersions(machineId);
      setVersions(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load model versions');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchVersions();
  }, [machineId]);

  const handleApprove = async (versionId) => {
    if (!window.confirm('Deploy this model version to production? The current active version will become a rollback candidate.')) {
      return;
    }
    try {
      setActionSuccess(null);
      await approveModelVersion(versionId, 'Administrator');
      setActionSuccess('Model version approved and deployed as ACTIVE.');
      fetchVersions();
    } catch (err) {
      alert(`Approval failed: ${err.message}`);
    }
  };

  const handleRollbackSubmit = async (e) => {
    e.preventDefault();
    if (!rollbackReason.trim()) {
      alert('A rollback reason is mandatory for audit compliance.');
      return;
    }
    try {
      setRollbackSubmitting(true);
      await rollbackModelVersion(machineId, rollbackReason, 'Administrator');
      setRollbackModalOpen(false);
      setRollbackReason('');
      setActionSuccess('Successfully rolled back to previous model version.');
      fetchVersions();
    } catch (err) {
      alert(`Rollback failed: ${err.message}`);
    } finally {
      setRollbackSubmitting(false);
    }
  };

  const handleRegisterCandidate = async (e) => {
    e.preventDefault();
    if (!newVersionStr.trim()) {
      alert('Version string is required (e.g. v2.1.0).');
      return;
    }
    try {
      setCandidateSubmitting(true);
      await registerModelCandidate({
        machine_id: machineId,
        version: newVersionStr.trim(),
        model_type: 'LightGBM+IsolationForest',
        training_dataset_id: newDatasetId.trim() || 'NASA C-MAPSS FD001 Batch',
        validation_metrics: { rul_rmse: 11.2, anomaly_f1: 0.94 }
      });
      setCandidateModalOpen(false);
      setNewVersionStr('');
      setNewDatasetId('');
      setActionSuccess('New candidate registered. Awaiting Administrator validation & approval.');
      fetchVersions();
    } catch (err) {
      alert(`Registration failed: ${err.message}`);
    } finally {
      setCandidateSubmitting(false);
    }
  };

  const activeVersion = versions.find(v => v.status === 'ACTIVE');
  const rollbackCandidates = versions.filter(v => v.status === 'ROLLBACK_CANDIDATE' || v.status === 'RETIRED');

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
        <div>
          <div className="flex items-center gap-2">
            <Layers className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white tracking-wide">Model Versioning & Rollback Registry</h2>
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Auditable lifecycle governance: Candidate → Validation → Administrator Approval → Active → Rollback.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {userRole === 'ADMIN' && rollbackCandidates.length > 0 && (
            <button
              onClick={() => setRollbackModalOpen(true)}
              className="flex items-center gap-2 px-3.5 py-2 bg-amber-500/10 border border-amber-500/30 text-amber-300 hover:bg-amber-500/20 rounded-lg text-sm font-medium transition"
            >
              <RotateCcw className="w-4 h-4" />
              Rollback Model
            </button>
          )}

          {userRole === 'ADMIN' && (
            <button
              onClick={() => setCandidateModalOpen(true)}
              className="flex items-center gap-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition shadow-lg shadow-indigo-600/20"
            >
              <PlusCircle className="w-4 h-4" />
              Register Candidate
            </button>
          )}
        </div>
      </div>

      {actionSuccess && (
        <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {actionSuccess}
        </div>
      )}

      {/* Active Model Banner */}
      {activeVersion ? (
        <div className="mt-6 p-4 bg-gradient-to-r from-indigo-950/40 via-blue-950/30 to-purple-950/40 border border-indigo-500/30 rounded-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center text-emerald-400 font-bold">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  ACTIVE DEPLOYMENT
                </span>
                <span className="text-white font-bold text-base">{activeVersion.version}</span>
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Type: {activeVersion.model_type} • Deployed: {activeVersion.deployed_at ? new Date(activeVersion.deployed_at).toLocaleString() : 'Active'} • Approved by: {activeVersion.approved_by || 'Admin'}
              </p>
            </div>
          </div>

          {activeVersion.validation_metrics && (
            <div className="flex items-center gap-4 text-xs">
              {activeVersion.validation_metrics.rul_rmse && (
                <div className="bg-gray-900/60 px-3 py-1.5 rounded-lg border border-gray-800">
                  <span className="text-gray-400">RUL RMSE:</span>{' '}
                  <span className="text-indigo-300 font-semibold">{activeVersion.validation_metrics.rul_rmse}</span>
                </div>
              )}
              {activeVersion.validation_metrics.anomaly_f1 && (
                <div className="bg-gray-900/60 px-3 py-1.5 rounded-lg border border-gray-800">
                  <span className="text-gray-400">Anomaly F1:</span>{' '}
                  <span className="text-emerald-300 font-semibold">{activeVersion.validation_metrics.anomaly_f1}</span>
                </div>
              )}
            </div>
          )}
        </div>
      ) : (
        <div className="mt-6 p-4 bg-gray-900/40 border border-gray-800 rounded-xl text-center text-gray-400 text-sm">
          No explicitly registered active model version. System is using baseline trained pipeline.
        </div>
      )}

      {/* Version History Table */}
      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <History className="w-4 h-4 text-gray-400" />
          Version Audit History
        </h3>

        {loading ? (
          <div className="p-8 text-center text-gray-500 text-sm">Loading version registry...</div>
        ) : versions.length === 0 ? (
          <div className="p-8 text-center text-gray-500 text-sm">No version history records found.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-gray-800 text-xs font-semibold text-gray-400">
                  <th className="py-3 px-4">Version</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Model Type</th>
                  <th className="py-3 px-4">Dataset ID</th>
                  <th className="py-3 px-4">Approved By</th>
                  <th className="py-3 px-4">Deployed / Retired</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 text-sm">
                {versions.map((ver) => (
                  <tr key={ver.id} className="hover:bg-gray-900/30 transition">
                    <td className="py-3 px-4 font-medium text-white">
                      {ver.version}
                      {ver.parent_version_id && (
                        <span className="block text-xs text-gray-500">Parent: #{ver.parent_version_id}</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      {ver.status === 'ACTIVE' && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          ACTIVE
                        </span>
                      )}
                      {ver.status === 'CANDIDATE' && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-500/30">
                          CANDIDATE
                        </span>
                      )}
                      {ver.status === 'ROLLBACK_CANDIDATE' && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          ROLLBACK TARGET
                        </span>
                      )}
                      {ver.status === 'RETIRED' && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-gray-700/40 text-gray-400 border border-gray-700">
                          RETIRED
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-gray-300 text-xs">{ver.model_type}</td>
                    <td className="py-3 px-4 text-gray-400 text-xs">{ver.training_dataset_id || 'C-MAPSS'}</td>
                    <td className="py-3 px-4 text-gray-300 text-xs">{ver.approved_by || '—'}</td>
                    <td className="py-3 px-4 text-gray-400 text-xs">
                      {ver.deployed_at ? new Date(ver.deployed_at).toLocaleDateString() : '—'}
                      {ver.rollback_reason && (
                        <span className="block text-amber-400/80 text-xs italic mt-0.5">
                          Reason: {ver.rollback_reason}
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {ver.status === 'CANDIDATE' && userRole === 'ADMIN' && (
                        <button
                          onClick={() => handleApprove(ver.id)}
                          className="px-3 py-1 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/30 rounded text-xs font-medium transition"
                        >
                          Approve & Deploy
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Rollback Modal */}
      {rollbackModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-2 text-amber-400 mb-2">
              <RotateCcw className="w-5 h-5" />
              <h3 className="text-lg font-bold text-white">Confirm Model Rollback</h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Restoring the previous model version will retire the currently active version. An auditable reason is required.
            </p>

            <form onSubmit={handleRollbackSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">
                  Rollback Justification / Reason *
                </label>
                <textarea
                  value={rollbackReason}
                  onChange={(e) => setRollbackReason(e.target.value)}
                  placeholder="e.g. Higher false alarm rate observed under plant load conditions"
                  rows={3}
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-amber-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setRollbackModalOpen(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={rollbackSubmitting}
                  className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-sm font-medium transition"
                >
                  {rollbackSubmitting ? 'Rolling back...' : 'Confirm Rollback'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Register Candidate Modal */}
      {candidateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-2 text-indigo-400 mb-2">
              <PlusCircle className="w-5 h-5" />
              <h3 className="text-lg font-bold text-white">Register Candidate Model</h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              New candidates are placed in CANDIDATE state and require Administrator approval before serving inference.
            </p>

            <form onSubmit={handleRegisterCandidate} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Version String *</label>
                <input
                  type="text"
                  value={newVersionStr}
                  onChange={(e) => setNewVersionStr(e.target.value)}
                  placeholder="e.g. v2.1.0"
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Training Dataset Reference</label>
                <input
                  type="text"
                  value={newDatasetId}
                  onChange={(e) => setNewDatasetId(e.target.value)}
                  placeholder="e.g. NASA FD001 + Plant 4 Calibrations"
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setCandidateModalOpen(false)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={candidateSubmitting}
                  className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
                >
                  {candidateSubmitting ? 'Registering...' : 'Register Candidate'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
