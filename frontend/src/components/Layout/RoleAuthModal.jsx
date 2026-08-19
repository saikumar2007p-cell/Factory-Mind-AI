import React, { useState } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Wrench,
  Eye,
  UserCheck,
  Lock,
  CheckCircle2,
  X,
  Sparkles
} from 'lucide-react';
import { switchAuthRole, getUserSession } from '../../services/api';

export default function RoleAuthModal({ isOpen, onClose, currentRole, currentActor, onRoleAuthenticated }) {
  if (!isOpen) return null;

  const [selectedRole, setSelectedRole] = useState(currentRole || 'ADMIN');
  const [actorName, setActorName] = useState(currentActor || (currentRole === 'ADMIN' ? 'Chief Operations Admin' : (currentRole === 'OPERATOR' ? 'Lead Maintenance Engineer' : 'Read-Only Auditor')));
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    if (role === 'ADMIN') setActorName('Chief Operations Admin');
    else if (role === 'OPERATOR') setActorName('Lead Maintenance Engineer');
    else setActorName('Read-Only Auditor');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      // Call backend API /api/v1/auth/switch-role to validate & record security audit log
      const result = await switchAuthRole(selectedRole, actorName);
      setSuccessMsg(`Authenticated as ${selectedRole} (${actorName}). Backend RBAC permissions updated.`);
      
      if (onRoleAuthenticated) {
        onRoleAuthenticated(selectedRole, actorName);
      }
      
      setTimeout(() => {
        onClose();
      }, 800);
    } catch (err) {
      console.error('Role authentication failed', err);
      setErrorMsg(err.message || 'Failed to authenticate role with backend RBAC.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(15, 23, 42, 0.65)',
      backdropFilter: 'blur(4px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '20px'
    }}>
      <div style={{
        background: '#ffffff',
        borderRadius: '12px',
        maxWidth: '560px',
        width: '100%',
        boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)',
        border: '1px solid #cbd5e1',
        overflow: 'hidden'
      }}>
        {/* Modal Header */}
        <div style={{
          padding: '18px 24px',
          background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 100%)',
          color: '#ffffff',
          display: 'flex',
          justify: 'space-between',
          alignItems: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ padding: '6px', background: 'rgba(255, 255, 255, 0.1)', borderRadius: '6px' }}>
              <Lock size={18} color="#38bdf8" />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, color: '#ffffff' }}>
                Session Role Authentication & RBAC Login
              </h3>
              <p style={{ margin: 0, fontSize: '12px', color: '#94a3b8' }}>
                Select an authenticated role to enforce backend permissions.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '4px' }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSubmit} style={{ padding: '24px' }}>
          {errorMsg && (
            <div style={{ padding: '10px 14px', background: '#fef2f2', border: '1px solid #fca5a5', borderRadius: '8px', color: '#991b1b', fontSize: '12px', marginBottom: '16px', fontWeight: 600 }}>
              {errorMsg}
            </div>
          )}

          {successMsg && (
            <div style={{ padding: '10px 14px', background: '#f0fdf4', border: '1px solid #86efac', borderRadius: '8px', color: '#166534', fontSize: '12px', marginBottom: '16px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircle2 size={16} color="#16a34a" />
              {successMsg}
            </div>
          )}

          {/* Actor Name Input */}
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px' }}>
              Authenticated User / Technician Name:
            </label>
            <input
              type="text"
              value={actorName}
              onChange={(e) => setActorName(e.target.value)}
              placeholder="e.g. Chief Operations Admin"
              required
              style={{
                width: '100%',
                padding: '8px 12px',
                borderRadius: '6px',
                border: '1px solid #cbd5e1',
                fontSize: '13px',
                color: '#0f172a',
                outline: 'none'
              }}
            />
          </div>

          {/* Role Choice Cards */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
            {/* ADMIN CARD */}
            <div
              onClick={() => handleRoleSelect('ADMIN')}
              style={{
                padding: '14px 16px',
                borderRadius: '8px',
                border: `2px solid ${selectedRole === 'ADMIN' ? '#dc2626' : '#e2e8f0'}`,
                background: selectedRole === 'ADMIN' ? '#fef2f2' : '#ffffff',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '18px' }}>👑</span>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: '#991b1b' }}>ADMIN — Full System Access</span>
                </div>
                <span className="badge badge-critical" style={{ fontSize: '10px' }}>Full Authority</span>
              </div>
              <p style={{ margin: 0, fontSize: '12px', color: '#64748b', lineHeight: 1.4 }}>
                Unrestricted operations: Gemini AI diagnosis, data source connector settings, work order lifecycle, and security audit trail logs.
              </p>
            </div>

            {/* OPERATOR CARD */}
            <div
              onClick={() => handleRoleSelect('OPERATOR')}
              style={{
                padding: '14px 16px',
                borderRadius: '8px',
                border: `2px solid ${selectedRole === 'OPERATOR' ? '#2563eb' : '#e2e8f0'}`,
                background: selectedRole === 'OPERATOR' ? '#eff6ff' : '#ffffff',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '18px' }}>🔧</span>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: '#1e40af' }}>OPERATOR — Operations & Execution</span>
                </div>
                <span className="badge badge-ai" style={{ fontSize: '10px' }}>Maintenance Access</span>
              </div>
              <p style={{ margin: 0, fontSize: '12px', color: '#64748b', lineHeight: 1.4 }}>
                Authorized for maintenance work order operations (create, assign, start, complete, verify) and alarm acknowledgement. System settings restricted to Admin by backend.
              </p>
            </div>

            {/* VIEWER CARD */}
            <div
              onClick={() => handleRoleSelect('VIEWER')}
              style={{
                padding: '14px 16px',
                borderRadius: '8px',
                border: `2px solid ${selectedRole === 'VIEWER' ? '#475569' : '#e2e8f0'}`,
                background: selectedRole === 'VIEWER' ? '#f8fafc' : '#ffffff',
                cursor: 'pointer',
                transition: 'all 0.15s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '18px' }}>👁️</span>
                  <span style={{ fontSize: '14px', fontWeight: 700, color: '#334155' }}>VIEWER — Read Only</span>
                </div>
                <span className="badge badge-normal" style={{ fontSize: '10px' }}>Strict Read-Only</span>
              </div>
              <p style={{ margin: 0, fontSize: '12px', color: '#64748b', lineHeight: 1.4 }}>
                Read-only inspection of fleet telemetry, prognostics, alarms, and analytics. All state mutations and work order operations are disabled and rejected by backend HTTP 403 Forbidden.
              </p>
            </div>
          </div>

          {/* Action Buttons */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <UserCheck size={16} />
              {loading ? 'Authenticating...' : `Authenticate as ${selectedRole}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
