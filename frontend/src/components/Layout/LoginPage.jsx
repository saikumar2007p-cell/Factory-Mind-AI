import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  Factory,
  Lock,
  Wrench,
  Eye,
  Crown,
  UserPlus,
  LogIn,
  AlertCircle,
  CheckCircle2,
  Mail,
  KeyRound,
  Zap,
  Flame,
  Database,
  ArrowRight
} from 'lucide-react';
import { isFirebaseConfigured } from '../../firebase/config';
import { signIn, registerUser, getCurrentUserRole, getCurrentUserOrg, refreshIdToken } from '../../firebase/auth';
import { authLogin, authRegister, switchAuthRole } from '../../services/api';

const SAVED_EMAIL_KEY = 'factorymind_saved_email';

export default function LoginPage({ onLogin }) {
  // Mode: 'db_login' | 'db_register' | 'firebase'
  const [authMode, setAuthMode] = useState('db_login');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [errorDetails, setErrorDetails] = useState(null);
  const [success, setSuccess] = useState(null);

  // Form fields
  const [email, setEmail] = useState(() => localStorage.getItem(SAVED_EMAIL_KEY) || 'admin@factorymind.ai');
  const [password, setPassword] = useState('admin123');
  const [displayName, setDisplayName] = useState('');
  const [selectedRole, setSelectedRole] = useState('ADMIN');

  // Firebase submode
  const [firebaseSubMode, setFirebaseSubMode] = useState('login');

  useEffect(() => {
    const saved = localStorage.getItem(SAVED_EMAIL_KEY);
    if (saved) {
      setEmail(saved);
    }
  }, []);

  // ── Database Login ──
  const handleDatabaseLogin = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Please enter both email/username and password.');
      return;
    }
    setLoading(true);
    setError(null);
    setErrorDetails(null);

    try {
      const resp = await authLogin(email.trim(), password.trim());
      localStorage.setItem(SAVED_EMAIL_KEY, resp.email || email.trim());
      setSuccess(`Welcome back, ${resp.display_name}! Loading dashboard...`);

      setTimeout(() => {
        onLogin(resp.role, resp.display_name, {
          userId: resp.user_id,
          email: resp.email,
          dbUserId: resp.db_user_id
        });
      }, 400);
    } catch (err) {
      console.error('[Auth] Database login error:', err);
      setError(err.detail || err.message || 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  // ── Database Registration ──
  const handleDatabaseRegister = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.');
      return;
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters.');
      return;
    }
    setLoading(true);
    setError(null);
    setErrorDetails(null);

    try {
      const name = displayName.trim() || email.split('@')[0].replace('.', ' ').toUpperCase();
      const resp = await authRegister(email.trim(), password.trim(), name, selectedRole);

      localStorage.setItem(SAVED_EMAIL_KEY, resp.email || email.trim());
      setSuccess(`Account created & registered for ${resp.display_name}! Entering platform...`);

      setTimeout(() => {
        onLogin(resp.role, resp.display_name, {
          userId: resp.user_id,
          email: resp.email,
          dbUserId: resp.db_user_id
        });
      }, 600);
    } catch (err) {
      console.error('[Auth] Database registration error:', err);
      setError(err.detail || err.message || 'Registration failed.');
    } finally {
      setLoading(false);
    }
  };

  // ── Firebase Login / Register ──
  const handleFirebaseSubmit = async (e) => {
    e.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.');
      return;
    }
    setLoading(true);
    setError(null);
    setErrorDetails(null);

    try {
      if (firebaseSubMode === 'login') {
        const user = await signIn(email.trim(), password.trim());
        await refreshIdToken();
        const role = await getCurrentUserRole() || 'ADMIN';
        const orgId = await getCurrentUserOrg() || '';
        const name = user.displayName || user.email;

        localStorage.setItem(SAVED_EMAIL_KEY, user.email);
        setSuccess(`Welcome back, ${name}! Entering FactoryMind AI...`);
        setTimeout(() => onLogin(role, name, { uid: user.uid, email: user.email, orgId }), 400);
      } else {
        const name = displayName.trim() || email.split('@')[0].replace('.', ' ').toUpperCase();
        const user = await registerUser(email.trim(), password.trim(), name);
        const role = selectedRole || 'ADMIN';
        const orgId = await getCurrentUserOrg() || '';

        localStorage.setItem(SAVED_EMAIL_KEY, user.email);
        setSuccess(`Firebase account created for ${name}! Entering FactoryMind AI...`);
        setTimeout(() => onLogin(role, name, { uid: user.uid, email: user.email, orgId }), 600);
      }
    } catch (err) {
      const code = err?.code || '';
      if (code === 'auth/configuration-not-found') {
        setError('Firebase Email/Password Auth Provider Not Enabled Yet');
        setErrorDetails({
          text: 'In your Firebase Console (Project: factory-mind-ai-4ea36), go to Build → Authentication → Sign-in method → Click "Email/Password" and enable it.',
          action: 'You can also use the "Database Sign In" or "Register Account" tabs above to log in instantly without waiting for Firebase setup.'
        });
      } else if (code === 'auth/email-already-in-use') {
        setError('This email is already registered in Firebase. Switch to Firebase Sign In tab.');
      } else if (code === 'auth/invalid-credential' || code === 'auth/wrong-password' || code === 'auth/user-not-found') {
        setError('Invalid Firebase email or password. Please verify your credentials or register.');
      } else {
        setError(err.message || 'Firebase authentication failed.');
      }
    } finally {
      setLoading(false);
    }
  };

  // ── Instant Preset ──
  const handleInstantPreset = async (role, actor) => {
    setLoading(true);
    setError(null);
    setErrorDetails(null);
    try {
      await switchAuthRole(role, actor);
    } catch (_) {}
    setSuccess(`Instant Access as ${role}!`);
    setTimeout(() => onLogin(role, actor), 300);
  };

  return (
    <div style={styles.bg}>
      <div style={styles.grid} />

      <div style={styles.card}>
        {/* Brand Header */}
        <div style={styles.brand}>
          <div style={styles.logoBox}>
            <Factory size={28} color="#38bdf8" />
          </div>
          <div>
            <div style={styles.logoTitle}>FactoryMind AI</div>
            <div style={styles.logoSub}>Industrial Predictive Health & Prognostics Platform</div>
          </div>
        </div>

        {/* Primary Mode Tabs */}
        <div style={styles.tabBar}>
          <button
            type="button"
            onClick={() => { setAuthMode('db_login'); setError(null); setErrorDetails(null); }}
            style={{
              ...styles.tabBtn,
              ...(authMode === 'db_login' ? styles.tabBtnActive : {})
            }}
          >
            <Database size={14} color={authMode === 'db_login' ? '#0f172a' : '#64748b'} />
            Database Sign In
          </button>
          <button
            type="button"
            onClick={() => { setAuthMode('db_register'); setError(null); setErrorDetails(null); }}
            style={{
              ...styles.tabBtn,
              ...(authMode === 'db_register' ? styles.tabBtnActive : {})
            }}
          >
            <UserPlus size={14} color={authMode === 'db_register' ? '#0f172a' : '#64748b'} />
            Register Account
          </button>
          <button
            type="button"
            onClick={() => { setAuthMode('firebase'); setError(null); setErrorDetails(null); }}
            style={{
              ...styles.tabBtn,
              ...(authMode === 'firebase' ? styles.tabBtnActive : {})
            }}
          >
            <Flame size={14} color={authMode === 'firebase' ? '#f59e0b' : '#64748b'} />
            Firebase
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={styles.errorBox}>
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8 }}>
              <AlertCircle size={18} color="#dc2626" style={{ flexShrink: 0, marginTop: 2 }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 13, color: '#991b1b' }}>{error}</div>
                {errorDetails && (
                  <div style={{ fontSize: 12, color: '#7f1d1d', marginTop: 4, lineHeight: 1.4 }}>
                    {errorDetails.text}
                    {errorDetails.action && (
                      <div style={{ marginTop: 6, fontWeight: 500, color: '#450a0a', background: 'rgba(254, 226, 226, 0.9)', padding: '6px 8px', borderRadius: 6 }}>
                        💡 {errorDetails.action}
                      </div>
                    )}
                  </div>
                )}
                {authMode === 'firebase' && (
                  <button
                    type="button"
                    onClick={() => { setAuthMode('db_login'); setError(null); }}
                    style={styles.quickFixBtn}
                  >
                    <Database size={13} /> Switch to Database Sign In
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Success Alert */}
        {success && (
          <div style={styles.successBox}>
            <CheckCircle2 size={16} color="#16a34a" />
            <span style={{ fontSize: 13, fontWeight: 600 }}>{success}</span>
          </div>
        )}

        {/* ═══════════════════════════════════════════════════════════ */}
        {/* MODE 1: DATABASE SIGN IN                                    */}
        {/* ═══════════════════════════════════════════════════════════ */}
        {authMode === 'db_login' && (
          <form onSubmit={handleDatabaseLogin} style={{ marginTop: 12 }}>
            <div style={styles.field}>
              <label style={styles.label}>Email Address or Username *</label>
              <div style={{ position: 'relative' }}>
                <Mail size={16} style={{ position: 'absolute', left: 10, top: 10, color: '#94a3b8' }} />
                <input
                  style={{ ...styles.input, paddingLeft: 34 }}
                  type="text"
                  placeholder="admin@factorymind.ai"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="username"
                />
              </div>
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Password *</label>
              <div style={{ position: 'relative' }}>
                <KeyRound size={16} style={{ position: 'absolute', left: 10, top: 10, color: '#94a3b8' }} />
                <input
                  style={{ ...styles.input, paddingLeft: 34 }}
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </div>
            </div>

            <button type="submit" disabled={loading} style={styles.primaryBtn}>
              <LogIn size={16} />
              {loading ? 'Authenticating...' : 'Sign In to FactoryMind'}
            </button>

            <div style={{ textAlign: 'center', marginTop: 12 }}>
              <button
                type="button"
                onClick={() => { setAuthMode('db_register'); setError(null); }}
                style={styles.linkBtn}
              >
                Don't have an account? Register new user <ArrowRight size={12} style={{ display: 'inline', verticalAlign: 'middle' }} />
              </button>
            </div>
          </form>
        )}

        {/* ═══════════════════════════════════════════════════════════ */}
        {/* MODE 2: DATABASE REGISTER                                  */}
        {/* ═══════════════════════════════════════════════════════════ */}
        {authMode === 'db_register' && (
          <form onSubmit={handleDatabaseRegister} style={{ marginTop: 12 }}>
            <div style={styles.field}>
              <label style={styles.label}>Full Name / Identifier *</label>
              <input
                style={styles.input}
                type="text"
                placeholder="e.g. Chief Operations Admin"
                value={displayName}
                onChange={e => setDisplayName(e.target.value)}
                required
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Email Address *</label>
              <input
                style={styles.input}
                type="email"
                placeholder="you@factorymind.ai"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Password * (min 6 characters)</label>
              <input
                style={styles.input}
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete="new-password"
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Initial Role Assignment *</label>
              <select
                style={{ ...styles.input, cursor: 'pointer', fontWeight: 600 }}
                value={selectedRole}
                onChange={e => setSelectedRole(e.target.value)}
              >
                <option value="ADMIN">👑 System Administrator (Full Access & Configuration)</option>
                <option value="OPERATOR">🔧 Operations Engineer (Monitoring & Maintenance Actions)</option>
              </select>
            </div>

            <button type="submit" disabled={loading} style={styles.primaryBtn}>
              <UserPlus size={16} />
              {loading ? 'Creating Account in Database...' : 'Register & Log In'}
            </button>

            <div style={{ textAlign: 'center', marginTop: 12 }}>
              <button
                type="button"
                onClick={() => { setAuthMode('db_login'); setError(null); }}
                style={styles.linkBtn}
              >
                Already have an account? Sign In
              </button>
            </div>
          </form>
        )}

        {/* ═══════════════════════════════════════════════════════════ */}
        {/* MODE 3: FIREBASE AUTHENTICATION                             */}
        {/* ═══════════════════════════════════════════════════════════ */}
        {authMode === 'firebase' && (
          <form onSubmit={handleFirebaseSubmit} style={{ marginTop: 12 }}>
            <div style={styles.subToggle}>
              <button
                type="button"
                onClick={() => setFirebaseSubMode('login')}
                style={{
                  ...styles.subToggleBtn,
                  ...(firebaseSubMode === 'login' ? styles.subToggleBtnActive : {})
                }}
              >
                Firebase Sign In
              </button>
              <button
                type="button"
                onClick={() => setFirebaseSubMode('register')}
                style={{
                  ...styles.subToggleBtn,
                  ...(firebaseSubMode === 'register' ? styles.subToggleBtnActive : {})
                }}
              >
                Firebase Register
              </button>
            </div>

            {firebaseSubMode === 'register' && (
              <div style={styles.field}>
                <label style={styles.label}>Full Name / Identifier *</label>
                <input
                  style={styles.input}
                  type="text"
                  placeholder="e.g. Chief Operations Admin"
                  value={displayName}
                  onChange={e => setDisplayName(e.target.value)}
                  required
                />
              </div>
            )}

            <div style={styles.field}>
              <label style={styles.label}>Firebase Email *</label>
              <input
                style={styles.input}
                type="email"
                placeholder="user@firebase.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
              />
            </div>

            <div style={styles.field}>
              <label style={styles.label}>Firebase Password *</label>
              <input
                style={styles.input}
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={6}
              />
            </div>

            {firebaseSubMode === 'register' && (
              <div style={styles.field}>
                <label style={styles.label}>Assigned Role *</label>
                <select
                  style={{ ...styles.input, cursor: 'pointer', fontWeight: 600 }}
                  value={selectedRole}
                  onChange={e => setSelectedRole(e.target.value)}
                >
                  <option value="ADMIN">👑 System Administrator (Full Access)</option>
                  <option value="OPERATOR">🔧 Operations Engineer (Operations Access)</option>
                </select>
              </div>
            )}

            <button type="submit" disabled={loading} style={styles.primaryBtn}>
              <Flame size={16} color="#f59e0b" />
              {loading ? 'Authenticating with Firebase...' : (firebaseSubMode === 'login' ? 'Sign In (Firebase)' : 'Register (Firebase)')}
            </button>
          </form>
        )}

        {/* ═══════════════════════════════════════════════════════════ */}
        {/* INSTANT ONE-CLICK DEMO ACCESS PRESETS                       */}
        {/* ═══════════════════════════════════════════════════════════ */}
        <div style={styles.presetSection}>
          <div style={styles.presetTitle}>
            <Zap size={13} color="#f59e0b" />
            <span>Instant One-Click Demo Access:</span>
          </div>
          <div style={styles.presetRow}>
            <button
              type="button"
              onClick={() => handleInstantPreset('ADMIN', 'Chief Operations Admin')}
              style={{ ...styles.presetBtn, borderColor: '#fca5a5', background: '#fef2f2', color: '#dc2626' }}
            >
              <Crown size={14} /> 👑 Admin
            </button>
            <button
              type="button"
              onClick={() => handleInstantPreset('OPERATOR', 'Lead Maintenance Engineer')}
              style={{ ...styles.presetBtn, borderColor: '#93c5fd', background: '#eff6ff', color: '#2563eb' }}
            >
              <Wrench size={14} /> 🔧 Operator
            </button>
          </div>
        </div>

        {/* Footer */}
        <div style={styles.footer}>
          <ShieldCheck size={13} color="#94a3b8" />
          <span>Persistent Database Auth & RBAC Security Enabled</span>
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
    position: 'absolute',
    inset: 0,
    backgroundImage: 'linear-gradient(rgba(56,189,248,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(56,189,248,0.05) 1px, transparent 1px)',
    backgroundSize: '40px 40px',
    pointerEvents: 'none',
  },
  card: {
    background: '#ffffff',
    borderRadius: 16,
    width: '100%',
    maxWidth: 480,
    padding: '28px 28px 20px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.1)',
    position: 'relative',
    zIndex: 1,
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: 14,
    marginBottom: 18
  },
  logoBox: {
    width: 48,
    height: 48,
    borderRadius: 12,
    background: 'linear-gradient(135deg, #0f172a, #1e3a5f)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 4px 12px rgba(0,0,0,0.25)'
  },
  logoTitle: {
    fontSize: 20,
    fontWeight: 800,
    color: '#0f172a',
    letterSpacing: '-0.5px'
  },
  logoSub: {
    fontSize: 11,
    color: '#64748b',
    marginTop: 2,
    fontWeight: 500
  },
  tabBar: {
    display: 'flex',
    background: '#f1f5f9',
    borderRadius: 10,
    padding: 3,
    marginBottom: 16,
    gap: 3
  },
  tabBtn: {
    flex: 1,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    padding: '8px 8px',
    border: 'none',
    background: 'transparent',
    borderRadius: 8,
    fontSize: 12,
    fontWeight: 600,
    color: '#64748b',
    cursor: 'pointer',
    transition: 'all 0.15s ease'
  },
  tabBtnActive: {
    background: '#ffffff',
    color: '#0f172a',
    fontWeight: 700,
    boxShadow: '0 2px 6px rgba(0,0,0,0.06)'
  },
  subToggle: {
    display: 'flex',
    background: '#f8fafc',
    borderRadius: 8,
    border: '1px solid #e2e8f0',
    padding: 2,
    gap: 2,
    marginBottom: 12
  },
  subToggleBtn: {
    flex: 1,
    padding: '6px 10px',
    border: 'none',
    background: 'transparent',
    borderRadius: 6,
    fontSize: 12,
    fontWeight: 600,
    color: '#64748b',
    cursor: 'pointer',
  },
  subToggleBtnActive: {
    background: '#0f172a',
    color: '#ffffff',
    fontWeight: 700,
  },
  field: {
    marginBottom: 14
  },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 700,
    color: '#334155',
    marginBottom: 5
  },
  input: {
    width: '100%',
    padding: '9px 12px',
    borderRadius: 8,
    border: '1px solid #cbd5e1',
    fontSize: 13,
    color: '#0f172a',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.15s ease',
  },
  primaryBtn: {
    width: '100%',
    padding: '11px 20px',
    borderRadius: 8,
    background: 'linear-gradient(135deg, #0f172a, #1e3a5f)',
    color: '#fff',
    border: 'none',
    cursor: 'pointer',
    fontSize: 14,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    boxShadow: '0 4px 12px rgba(15,23,42,0.3)',
    transition: 'opacity 0.15s',
  },
  linkBtn: {
    background: 'none',
    border: 'none',
    color: '#0284c7',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 600,
  },
  errorBox: {
    padding: '12px 14px',
    background: '#fef2f2',
    border: '1px solid #fca5a5',
    borderRadius: 10,
    marginBottom: 14,
  },
  quickFixBtn: {
    marginTop: 8,
    padding: '6px 10px',
    background: '#0f172a',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: 5
  },
  successBox: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 14px',
    background: '#f0fdf4',
    border: '1px solid #86efac',
    borderRadius: 8,
    color: '#166534',
    marginBottom: 14,
  },
  presetSection: {
    marginTop: 16,
    paddingTop: 14,
    borderTop: '1px dashed #e2e8f0',
  },
  presetTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    fontSize: 11,
    fontWeight: 700,
    color: '#64748b',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: '0.3px'
  },
  presetRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 8
  },
  presetBtn: {
    padding: '7px 8px',
    borderRadius: 8,
    border: '1px solid',
    cursor: 'pointer',
    fontSize: 12,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 5,
    transition: 'transform 0.1s ease',
  },
  footer: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    justifyContent: 'center',
    marginTop: 18,
    fontSize: 11,
    color: '#94a3b8',
    borderTop: '1px solid #f1f5f9',
    paddingTop: 12
  }
};
