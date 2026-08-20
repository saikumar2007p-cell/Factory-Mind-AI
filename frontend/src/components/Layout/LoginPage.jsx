import React, { useState, useEffect } from 'react';
import { ShieldCheck, Factory, Lock, User, Wrench, Eye, Crown, UserPlus, LogIn, AlertCircle, CheckCircle2 } from 'lucide-react';
import { switchAuthRole } from '../../services/api';

const API = 'http://localhost:8000/api/v1';

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState('login'); // default to login UI
  const [adminExists, setAdminExists] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  // Login state
  const [selectedRole, setSelectedRole] = useState('ADMIN');
  const [actorName, setActorName] = useState('');

  // Register state
  const [regName, setRegName] = useState('');
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');





  const handleRoleSelect = (role) => {
    setSelectedRole(role);
    if (!actorName || ['Chief Operations Admin', 'Lead Maintenance Engineer', 'Read-Only Auditor'].includes(actorName)) {
      if (role === 'ADMIN') setActorName('Chief Operations Admin');
      else if (role === 'OPERATOR') setActorName('Lead Maintenance Engineer');
      else setActorName('Read-Only Auditor');
    }
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!actorName.trim()) { setError('Please enter your name.'); return; }
    setLoading(true); setError(null);
    try {
      const result = await switchAuthRole(selectedRole, actorName.trim());
      setSuccess(`Welcome, ${actorName}!`);
      setTimeout(() => onLogin(selectedRole, actorName.trim()), 700);
    } catch (err) {
      setError(err.message || 'Login failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (!regName.trim() || !regUsername.trim()) { setError('Name and username are required.'); return; }
    setLoading(true); setError(null);
    try {
      const res = await fetch(`${API}/users/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-User-Role': 'ADMIN', 'X-Actor-Name': regName },
        body: JSON.stringify({ username: regUsername.trim(), full_name: regName.trim(), role: 'ADMIN', email: regEmail.trim() || null })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Registration failed');
      }
      setSuccess(`Admin account created! Logging you in...`);
      setAdminExists(true);
      // Auto-login as this admin
      await switchAuthRole('ADMIN', regName.trim());
      setTimeout(() => onLogin('ADMIN', regName.trim()), 800);
    } catch (err) {
      setError(err.message || 'Registration failed. Try again.');
    } finally {
      setLoading(false);
    }
  };

  const roles = [
    { id: 'ADMIN', icon: <Crown size={20} />, label: 'Administrator', desc: 'Full system access — settings, model governance, users, security', color: '#dc2626', bg: '#fef2f2', border: '#fca5a5', badge: 'Full Authority' },
    { id: 'OPERATOR', icon: <Wrench size={20} />, label: 'Operator / Engineer', desc: 'Create & manage work orders, acknowledge alerts, run maintenance', color: '#2563eb', bg: '#eff6ff', border: '#93c5fd', badge: 'Maintenance Access' },
    { id: 'VIEWER', icon: <Eye size={20} />, label: 'Viewer (Read Only)', desc: 'View dashboards, telemetry, and predictions — no changes allowed', color: '#475569', bg: '#f8fafc', border: '#cbd5e1', badge: 'Read Only' },
  ];

  if (mode === 'checking') {
    return (
      <div style={styles.bg}>
        <div style={{ color: '#94a3b8', fontSize: 14 }}>Connecting to FactoryMind...</div>
      </div>
    );
  }

  return (
    <div style={styles.bg}>
      {/* Background grid decoration */}
      <div style={styles.grid} />

      <div style={styles.card}>
        {/* Logo / Brand */}
        <div style={styles.brand}>
          <div style={styles.logoBox}>
            <Factory size={28} color="#38bdf8" />
          </div>
          <div>
            <div style={styles.logoTitle}>FactoryMind AI</div>
            <div style={styles.logoSub}>Industrial Predictive Intelligence Platform</div>
          </div>
        </div>

        <div style={styles.divider} />

        {/* Mode: Register First Admin */}
        {mode === 'register' && (
          <>
            <div style={styles.sectionHeader}>
              <UserPlus size={18} color="#f59e0b" />
              <div>
                <div style={{ fontWeight: 700, fontSize: 15, color: '#0f172a' }}>Set Up Administrator Account</div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>No admin found — register the first administrator to continue</div>
              </div>
            </div>

            <form onSubmit={handleRegister} style={{ marginTop: 20 }}>
              <div style={styles.field}>
                <label style={styles.label}>Full Name *</label>
                <input style={styles.input} type="text" placeholder="e.g. Ravi Kumar" value={regName} onChange={e => setRegName(e.target.value)} required />
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Username *</label>
                <input style={styles.input} type="text" placeholder="e.g. ravi.kumar" value={regUsername} onChange={e => setRegUsername(e.target.value)} required />
              </div>
              <div style={styles.field}>
                <label style={styles.label}>Email (optional)</label>
                <input style={styles.input} type="email" placeholder="e.g. ravi@factory.com" value={regEmail} onChange={e => setRegEmail(e.target.value)} />
              </div>

              {error && <div style={styles.errorBox}><AlertCircle size={14} />{error}</div>}
              {success && <div style={styles.successBox}><CheckCircle2 size={14} />{success}</div>}

              <button type="submit" disabled={loading} style={styles.primaryBtn}>
                <UserPlus size={16} />
                {loading ? 'Creating Account...' : 'Create Admin Account & Enter'}
              </button>
            </form>

            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <button onClick={() => setMode('login')} style={styles.linkBtn}>Already have an account? Login</button>
            </div>
          </>
        )}

        {/* Mode: Login */}
        {mode === 'login' && (
          <>
            <div style={styles.sectionHeader}>
              <Lock size={18} color="#38bdf8" />
              <div>
                <div style={{ fontWeight: 700, fontSize: 15, color: '#0f172a' }}>Sign In</div>
                <div style={{ fontSize: 12, color: '#64748b', marginTop: 2 }}>Select your role and enter your name to continue</div>
              </div>
            </div>

            <form onSubmit={handleLogin} style={{ marginTop: 20 }}>
              {/* Name input */}
              <div style={styles.field}>
                <label style={styles.label}>Your Name / Identifier *</label>
                <input
                  style={styles.input}
                  type="text"
                  placeholder="Enter your name"
                  value={actorName}
                  onChange={e => setActorName(e.target.value)}
                  required
                />
              </div>

              {/* Role selection */}
              <div style={{ marginBottom: 20 }}>
                <label style={styles.label}>Select Role *</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 6 }}>
                  {roles.map(r => (
                    <div
                      key={r.id}
                      onClick={() => handleRoleSelect(r.id)}
                      style={{
                        padding: '12px 14px',
                        borderRadius: 8,
                        border: `2px solid ${selectedRole === r.id ? r.color : '#e2e8f0'}`,
                        background: selectedRole === r.id ? r.bg : '#fff',
                        cursor: 'pointer',
                        transition: 'all 0.15s ease',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 12
                      }}
                    >
                      <div style={{ color: selectedRole === r.id ? r.color : '#94a3b8', flexShrink: 0 }}>{r.icon}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: 13, color: selectedRole === r.id ? r.color : '#334155' }}>{r.label}</div>
                        <div style={{ fontSize: 11, color: '#64748b', marginTop: 2 }}>{r.desc}</div>
                      </div>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
                        background: selectedRole === r.id ? r.color : '#e2e8f0',
                        color: selectedRole === r.id ? '#fff' : '#64748b',
                        flexShrink: 0
                      }}>{r.badge}</span>
                    </div>
                  ))}
                </div>
              </div>

              {error && <div style={styles.errorBox}><AlertCircle size={14} />{error}</div>}
              {success && <div style={styles.successBox}><CheckCircle2 size={14} />{success}</div>}

              <button type="submit" disabled={loading} style={styles.primaryBtn}>
                <LogIn size={16} />
                {loading ? 'Signing In...' : `Sign In as ${selectedRole}`}
              </button>
            </form>

            {!adminExists && (
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <button onClick={() => setMode('register')} style={styles.linkBtn}>Register first admin account</button>
              </div>
            )}
          </>
        )}

        <div style={styles.footer}>
          <ShieldCheck size={12} color="#94a3b8" />
          Role-based access control enforced by backend • All actions logged to security audit trail
        </div>
      </div>
    </div>
  );
}

const styles = {
  bg: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #0f172a 0%, #1e293b 60%, #0c4a6e 100%)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '20px',
    position: 'relative',
    overflow: 'hidden',
  },
  grid: {
    position: 'absolute', inset: 0,
    backgroundImage: 'linear-gradient(rgba(56,189,248,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(56,189,248,0.05) 1px, transparent 1px)',
    backgroundSize: '40px 40px',
    pointerEvents: 'none',
  },
  card: {
    background: '#ffffff',
    borderRadius: 16,
    width: '100%',
    maxWidth: 480,
    padding: '32px 32px 24px',
    boxShadow: '0 25px 50px rgba(0,0,0,0.4)',
    position: 'relative',
    zIndex: 1,
  },
  brand: {
    display: 'flex', alignItems: 'center', gap: 14, marginBottom: 24
  },
  logoBox: {
    width: 52, height: 52, borderRadius: 12,
    background: 'linear-gradient(135deg, #0f172a, #1e3a5f)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
  },
  logoTitle: { fontSize: 20, fontWeight: 800, color: '#0f172a', letterSpacing: '-0.5px' },
  logoSub: { fontSize: 11, color: '#64748b', marginTop: 2, fontWeight: 500 },
  divider: { height: 1, background: '#e2e8f0', marginBottom: 24 },
  sectionHeader: {
    display: 'flex', alignItems: 'flex-start', gap: 10,
    padding: '12px 14px', background: '#f8fafc', borderRadius: 8, border: '1px solid #e2e8f0'
  },
  field: { marginBottom: 16 },
  label: { display: 'block', fontSize: 12, fontWeight: 700, color: '#334155', marginBottom: 6 },
  input: {
    width: '100%', padding: '9px 12px', borderRadius: 8, border: '1px solid #cbd5e1',
    fontSize: 13, color: '#0f172a', outline: 'none', boxSizing: 'border-box',
    transition: 'border-color 0.15s ease',
  },
  primaryBtn: {
    width: '100%', padding: '11px 20px', borderRadius: 8,
    background: 'linear-gradient(135deg, #0f172a, #1e3a5f)',
    color: '#fff', border: 'none', cursor: 'pointer',
    fontSize: 14, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
    boxShadow: '0 4px 12px rgba(15,23,42,0.3)',
    transition: 'opacity 0.15s',
  },
  linkBtn: {
    background: 'none', border: 'none', color: '#38bdf8', cursor: 'pointer',
    fontSize: 12, fontWeight: 600, textDecoration: 'underline'
  },
  errorBox: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 12px', background: '#fef2f2', border: '1px solid #fca5a5',
    borderRadius: 8, color: '#991b1b', fontSize: 12, fontWeight: 600, marginBottom: 14
  },
  successBox: {
    display: 'flex', alignItems: 'center', gap: 6,
    padding: '9px 12px', background: '#f0fdf4', border: '1px solid #86efac',
    borderRadius: 8, color: '#166534', fontSize: 12, fontWeight: 600, marginBottom: 14
  },
  footer: {
    display: 'flex', alignItems: 'center', gap: 6, justifyContent: 'center',
    marginTop: 24, fontSize: 11, color: '#94a3b8', borderTop: '1px solid #e2e8f0', paddingTop: 16
  }
};
