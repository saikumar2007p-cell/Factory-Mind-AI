import React, { useState } from 'react';
import {
  FileCheck,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Sparkles,
  HelpCircle
} from 'lucide-react';
import { recordOutcome } from '../../services/api';

export default function GroundTruthOutcomeModal({ workOrder, onClose, onSuccess }) {
  const [outcomeType, setOutcomeType] = useState('COMPONENT_REPLACED');
  const [componentReplaced, setComponentReplaced] = useState('');
  const [actualFinding, setActualFinding] = useState('');
  const [predictionCorrect, setPredictionCorrect] = useState(true);
  const [falseAlarmReason, setFalseAlarmReason] = useState('');
  const [retrainingCandidate, setRetrainingCandidate] = useState(true);
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!workOrder) return;

    try {
      setSubmitting(true);
      await recordOutcome({
        work_order_id: workOrder.id,
        machine_id: workOrder.machine_id,
        outcome_type: outcomeType,
        recorded_by: 'Field Technician',
        component_replaced: componentReplaced.trim() || null,
        actual_finding: actualFinding.trim() || null,
        prediction_was_correct: predictionCorrect,
        false_alarm_reason: !predictionCorrect ? (falseAlarmReason.trim() || null) : null,
        retraining_candidate: retrainingCandidate,
        notes: notes.trim() || null
      });

      if (onSuccess) onSuccess();
      if (onClose) onClose();
    } catch (err) {
      alert(`Failed to record outcome: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-lg w-full shadow-2xl">
        <div className="flex items-center gap-2 text-indigo-400 mb-2">
          <FileCheck className="w-5 h-5" />
          <h3 className="text-lg font-bold text-white">Record Maintenance Outcome</h3>
        </div>
        <p className="text-xs text-gray-400 mb-4">
          Capture ground-truth physical findings for {workOrder.work_order_code} to evaluate model precision and train future iterations.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">
              Physical Outcome Type *
            </label>
            <select
              value={outcomeType}
              onChange={(e) => setOutcomeType(e.target.value)}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
            >
              <option value="COMPONENT_REPLACED">COMPONENT_REPLACED (Hardware replaced)</option>
              <option value="PREVENTIVE_MAINTENANCE">PREVENTIVE_MAINTENANCE (Lubrication, cleaning, calibration)</option>
              <option value="CORRECTIVE_MAINTENANCE">CORRECTIVE_MAINTENANCE (Repair executed)</option>
              <option value="NO_ISSUE_FOUND">NO_ISSUE_FOUND (Inspected, normal operation)</option>
              <option value="FALSE_ALARM">FALSE_ALARM (Model triggered alarm incorrectly)</option>
              <option value="MACHINE_FAILURE">MACHINE_FAILURE (Equipment failed in service)</option>
              <option value="OTHER">OTHER (Special case)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">
              Was the Predictive ML Alert Accurate? *
            </label>
            <div className="flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-200">
                <input
                  type="radio"
                  name="predictionAccuracy"
                  checked={predictionCorrect === true}
                  onChange={() => setPredictionCorrect(true)}
                  className="text-indigo-600 focus:ring-indigo-500 bg-gray-950"
                />
                <span className="flex items-center gap-1 text-emerald-400">
                  <CheckCircle2 className="w-4 h-4" /> Yes (True Positive)
                </span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-200">
                <input
                  type="radio"
                  name="predictionAccuracy"
                  checked={predictionCorrect === false}
                  onChange={() => setPredictionCorrect(false)}
                  className="text-indigo-600 focus:ring-indigo-500 bg-gray-950"
                />
                <span className="flex items-center gap-1 text-amber-400">
                  <AlertTriangle className="w-4 h-4" /> No (False Alarm / Inaccurate)
                </span>
              </label>
            </div>
          </div>

          {!predictionCorrect && (
            <div>
              <label className="block text-xs font-semibold text-amber-300 mb-1">
                False Alarm Reason
              </label>
              <input
                type="text"
                value={falseAlarmReason}
                onChange={(e) => setFalseAlarmReason(e.target.value)}
                placeholder="e.g. Transient electrical noise on sensor s_4"
                className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-amber-500"
              />
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">
              Component Replaced (if applicable)
            </label>
            <input
              type="text"
              value={componentReplaced}
              onChange={(e) => setComponentReplaced(e.target.value)}
              placeholder="e.g. High Pressure Compressor Stator Vanes"
              className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-300 mb-1">
              Physical Finding / Technician Inspection Notes
            </label>
            <textarea
              value={actualFinding}
              onChange={(e) => setActualFinding(e.target.value)}
              placeholder="e.g. Moderate thermal erosion confirmed on stage 2 blades; within expected limits but close to threshold"
              rows={2}
              className="w-full bg-gray-950 border border-gray-800 rounded-lg p-2.5 text-sm text-white focus:outline-none focus:border-indigo-500"
            />
          </div>

          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="retrainCandidate"
              checked={retrainingCandidate}
              onChange={(e) => setRetrainingCandidate(e.target.checked)}
              className="rounded border-gray-700 text-indigo-600 focus:ring-indigo-500 bg-gray-950"
            />
            <label htmlFor="retrainCandidate" className="text-xs text-indigo-300 font-medium">
              Flag as valuable ground-truth example for next model retraining cycle
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg text-sm font-medium"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-sm font-medium transition"
            >
              {submitting ? 'Recording...' : 'Record Outcome'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
