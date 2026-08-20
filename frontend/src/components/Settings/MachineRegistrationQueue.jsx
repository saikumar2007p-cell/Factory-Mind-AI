import React, { useState, useEffect } from 'react';
import {
  Inbox,
  CheckCircle2,
  XCircle,
  FileSpreadsheet,
  AlertCircle,
  Eye,
  Building,
  Cpu,
  Clock,
  ShieldCheck
} from 'lucide-react';
import {
  getMachineRegistrations,
  approveMachineRegistration,
  rejectMachineRegistration
} from '../../services/api';

export default function MachineRegistrationQueue({ userRole = 'ADMIN', onMachineCreated }) {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState(null);

  // Approve Modal State
  const [approveModalReq, setApproveModalReq] = useState(null);
  const [machineName, setMachineName] = useState('');
  const [machineType, setMachineType] = useState('Industrial Turbofan');
  const [location, setLocation] = useState('Plant 4 - Bay B');
  const [submitting, setSubmitting] = useState(false);

  // Reject Modal State
  const [rejectModalReq, setRejectModalReq] = useState(null);
  const [rejectNotes, setRejectNotes] = useState('');

  // Preview Modal State
  const [previewReq, setPreviewReq] = useState(null);

  const fetchRequests = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getMachineRegistrations();
      setRequests(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load registration requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRequests();
  }, []);

  const openApproveModal = (req) => {
    setApproveModalReq(req);
    setMachineName(`Turbofan ${req.requested_machine_id}`);
    setMachineType('Industrial Equipment');
    setLocation('Production Floor - Line 1');
  };

  const handleApprove = async (e) => {
    e.preventDefault();
    if (!approveModalReq) return;
    try {
      setSubmitting(true);
      await approveMachineRegistration(approveModalReq.id, {
        machine_name: machineName.trim(),
        machine_type: machineType.trim(),
        location: location.trim(),
        reviewed_by: 'Administrator'
      });
      setApproveModalReq(null);
      setActionSuccess(`Machine "${machineName}" approved and registered! Staged data is now active.`);
      fetchRequests();
      if (onMachineCreated) onMachineCreated();
    } catch (err) {
      alert(`Approval failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async (e) => {
    e.preventDefault();
    if (!rejectModalReq) return;
    if (!rejectNotes.trim()) {
      alert('A rejection reason is required.');
      return;
    }
    try {
      setSubmitting(true);
      await rejectMachineRegistration(rejectModalReq.id, {
        reviewed_by: 'Administrator',
        review_notes: rejectNotes.trim()
      });
      setRejectModalReq(null);
      setRejectNotes('');
      setActionSuccess('Registration rejected. Staged data removed.');
      fetchRequests();
    } catch (err) {
      alert(`Rejection failed: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const pendingRequests = requests.filter(r => r.status === 'PENDING_REVIEW');
  const pastRequests = requests.filter(r => r.status !== 'PENDING_REVIEW');

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 shadow-xl">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-gray-800">
        <div>
          <div className="flex items-center gap-2">
            <Inbox className="w-5 h-5 text-amber-400" />
            <h2 className="text-lg font-bold text-white tracking-wide">Machine Registration Review Queue</h2>
            {pendingRequests.length > 0 && (
              <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                {pendingRequests.length} Pending
              </span>
            )}
          </div>
          <p className="text-sm text-gray-400 mt-1">
            Uploaded telemetry with unknown machine IDs is held in review to prevent automatic ghost machine creation.
          </p>
        </div>
      </div>

      {actionSuccess && (
        <div className="mt-4 p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-300 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          {actionSuccess}
        </div>
      )}

      {/* Pending Reviews Section */}
      <div className="mt-6">
        <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
          Pending Administrator Review
        </h3>

        {loading ? (
          <div className="p-8 text-center text-gray-500 text-sm">Loading registration queue...</div>
        ) : pendingRequests.length === 0 ? (
          <div className="p-8 bg-gray-900/30 border border-gray-800/80 rounded-xl text-center text-gray-400 text-sm">
            <CheckCircle2 className="w-6 h-6 text-emerald-400 mx-auto mb-2 opacity-60" />
            No pending machine registrations. All uploaded files reference registered machines.
          </div>
        ) : (
          <div className="space-y-3">
            {pendingRequests.map((req) => (
              <div
                key={req.id}
                className="p-4 bg-gray-900/60 border border-amber-500/30 rounded-xl flex flex-col md:flex-row md:items-center justify-between gap-4"
              >
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-lg bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 shrink-0">
                    <FileSpreadsheet className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-bold text-white text-base">{req.requested_machine_id}</span>
                      <span className="text-xs px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                        {req.source_row_count} Telemetry Rows
                      </span>
                    </div>
                    <p className="text-xs text-gray-400 mt-1">
                      File: {req.source_filename} • Detected Columns: {req.detected_columns?.length || 0} • Uploaded: {new Date(req.requested_at).toLocaleString()}
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPreviewReq(req)}
                    className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-xs font-medium transition flex items-center gap-1.5"
                  >
                    <Eye className="w-3.5 h-3.5" />
                    Preview Data
                  </button>

                  {userRole === 'ADMIN' ? (
                    <>
                      <button
                        onClick={() => openApproveModal(req)}
                        className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-medium transition flex items-center gap-1.5 shadow"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Approve & Create
                      </button>
                      <button
                        onClick={() => setRejectModalReq(req)}
                        className="px-3 py-1.5 bg-red-500/10 border border-red-500/30 text-red-300 hover:bg-red-500/20 rounded-lg text-xs font-medium transition flex items-center gap-1.5"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                        Reject
                      </button>
                    </>
                  ) : (
                    <span className="text-xs text-gray-500 italic">Admin Approval Required</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Past Decisions Table */}
      {pastRequests.length > 0 && (
        <div className="mt-8">
          <h3 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-3">
            Review History
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-gray-800 text-gray-400">
                  <th className="py-2.5 px-3">Requested ID</th>
                  <th className="py-2.5 px-3">Source File</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Reviewed By</th>
                  <th className="py-2.5 px-3">Reviewed At</th>
                  <th className="py-2.5 px-3">Notes</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 text-gray-300">
                {pastRequests.map((r) => (
                  <tr key={r.id}>
                    <td className="py-2.5 px-3 font-semibold text-white">{r.requested_machine_id}</td>
                    <td className="py-2.5 px-3 text-gray-400">{r.source_filename}</td>
                    <td className="py-2.5 px-3">
                      {r.status === 'APPROVED' ? (
                        <span className="px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                          Approved
                        </span>
                      ) : (
                        <span className="px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30">
                          Rejected
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3">{r.reviewed_by || '—'}</td>
                    <td className="py-2.5 px-3 text-gray-400">
                      {r.reviewed_at ? new Date(r.reviewed_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-2.5 px-3 text-gray-400">{r.review_notes || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Approve Modal */}
      {approveModalReq && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-2 text-emerald-400 mb-2">
              <CheckCircle2 className="w-5 h-5" />
              <h3 className="text-lg font-bold text-white">Approve Machine Registration</h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Approving will create a new machine in the fleet and ingest the staged {approveModalReq.source_row_count} telemetry rows.
            </p>

            <form onSubmit={handleApprove} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Assigned Machine Name *</label>
                <input
                  type="text"
                  value={machineName}
                  onChange={(e) => setMachineName(e.target.value)}
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Machine Type *</label>
                <input
                  type="text"
                  value={machineType}
                  onChange={(e) => setMachineType(e.target.value)}
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Plant Location *</label>
                <input
                  type="text"
                  value={location}
                  onChange={(e) => setLocation(e.target.value)}
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setApproveModalReq(null)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-sm font-medium transition"
                >
                  {submitting ? 'Creating...' : 'Approve & Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {rejectModalReq && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <div className="flex items-center gap-2 text-red-400 mb-2">
              <XCircle className="w-5 h-5" />
              <h3 className="text-lg font-bold text-white">Reject Machine Registration</h3>
            </div>
            <p className="text-xs text-gray-400 mb-4">
              Rejecting will safely delete the quarantined data file. Provide a justification.
            </p>

            <form onSubmit={handleReject} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-gray-300 mb-1">Rejection Reason *</label>
                <textarea
                  value={rejectNotes}
                  onChange={(e) => setRejectNotes(e.target.value)}
                  placeholder="e.g. Unrecognized test bench data — not production equipment"
                  rows={3}
                  required
                  className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-red-500"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setRejectModalReq(null)}
                  className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg text-sm font-medium transition"
                >
                  {submitting ? 'Rejecting...' : 'Reject Registration'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewReq && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-2xl w-full shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-gray-800 mb-4">
              <h3 className="text-base font-bold text-white">
                Sample Data Preview: {previewReq.requested_machine_id}
              </h3>
              <button
                onClick={() => setPreviewReq(null)}
                className="text-gray-400 hover:text-white"
              >
                ✕
              </button>
            </div>

            <div className="mb-3 text-xs text-gray-400">
              Columns detected: <span className="text-gray-200">{previewReq.detected_columns?.join(', ')}</span>
            </div>

            <div className="overflow-x-auto max-h-64 bg-gray-950 rounded-lg border border-gray-800 p-3">
              <pre className="text-xs text-emerald-300 font-mono">
                {JSON.stringify(previewReq.sample_data, null, 2)}
              </pre>
            </div>

            <div className="mt-4 flex justify-end">
              <button
                onClick={() => setPreviewReq(null)}
                className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
