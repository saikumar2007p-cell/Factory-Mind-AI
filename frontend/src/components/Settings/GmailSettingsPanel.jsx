import React, { useState, useEffect } from 'react';
import {
  Mail,
  Send,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  Clock,
  Shield,
  ExternalLink,
  Info,
  Sliders,
  Zap,
  Server,
  Key,
  Globe,
  Inbox
} from 'lucide-react';
import {
  getEmailSettings,
  updateEmailSettings,
  sendEmailAlert,
  testEmailAlert,
  getEmailLogs,
  openEmailDirect,
  triggerAutomatedCycleAlert
} from '../../services/api';

export default function GmailSettingsPanel() {
  const [settings, setSettings] = useState({
    admin_email: 'admin@factorymind.ai',
    admin_name: 'Factory Administrator',
    email_enabled: true,
    auto_send_enabled: true,
    notify_on_critical: true,
    notify_on_warning: true,
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    sender_name: 'FactoryMind AI Alert Bot'
  });

  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [successMsg, setSuccessMsg] = useState('');
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      setLoading(true);
      const [sRes, lRes] = await Promise.all([
        getEmailSettings(),
        getEmailLogs().catch(() => ({ logs: [] }))
      ]);
      if (sRes) setSettings(sRes);
      if (lRes && lRes.logs) setLogs(lRes.logs);
    } catch (err) {
      console.error('Failed to load Gmail settings:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    if (e) e.preventDefault();
    try {
      setSaving(true);
      setSuccessMsg('');
      const res = await updateEmailSettings(settings);
      if (res && res.success) {
        setSuccessMsg('Gmail settings saved and alert channels updated successfully!');
        setTimeout(() => setSuccessMsg(''), 4000);
      }
    } catch (err) {
      alert('Failed to save settings: ' + (err.message || 'Error'));
    } finally {
      setSaving(false);
    }
  };

  const handleSendTestEmail = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      const res = await testEmailAlert(settings.admin_email);
      setTestResult(res);
      await loadAll();
    } catch (err) {
      alert('Test Email failed: ' + (err.message || 'Error'));
    } finally {
      setTesting(false);
    }
  };

  const handleTriggerAutomatedPipeline = async () => {
    try {
      setTesting(true);
      const res = await triggerAutomatedCycleAlert(1);
      if (res && res.success) {
        setTestResult(res.email_result || res.result);
        await loadAll();
        alert(`🚀 Automated Pipeline Executed! Critical anomaly diagnosed and alert dispatched directly to ${settings.admin_email}.`);
      }
    } catch (err) {
      alert('Pipeline execution error: ' + (err.message || 'Network error'));
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
        <RefreshCw size={28} className="spin" color="#3b82f6" style={{ margin: '0 auto 12px auto' }} />
        <div style={{ color: '#64748b', fontSize: '13px' }}>Loading Gmail & Email Settings...</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header Banner */}
      <div className="card" style={{
        background: 'linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%)',
        border: '1px solid #4338ca',
        borderRadius: '12px',
        padding: '20px 24px',
        color: '#ffffff',
        boxShadow: '0 4px 16px rgba(67, 56, 202, 0.2)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '46px',
              height: '46px',
              borderRadius: '12px',
              background: '#4f46e5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 10px rgba(79, 70, 229, 0.4)'
            }}>
              <Mail size={24} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#ffffff' }}>
                  Gmail & Email Alert Gateway
                </h3>
                <span className="badge badge-normal" style={{ fontSize: '10px', background: '#4f46e5', color: '#ffffff' }}>
                  GMAIL INTEGRATION ACTIVE
                </span>
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#c7d2fe' }}>
                Dispatches high-priority failure reports, remaining life estimates, and prescriptive repair steps directly to <strong>{settings.admin_email}</strong>.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <button
              className="btn btn-sm"
              onClick={handleTriggerAutomatedPipeline}
              disabled={testing}
              style={{
                background: '#3b82f6',
                color: '#ffffff',
                border: 'none',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                borderRadius: '8px',
                cursor: 'pointer'
              }}
            >
              <Zap size={14} />
              {testing ? 'Evaluating...' : '🚀 Run Automated Email Alert'}
            </button>

            <button
              className="btn btn-sm"
              onClick={handleSendTestEmail}
              disabled={testing}
              style={{
                background: '#4f46e5',
                color: '#ffffff',
                border: 'none',
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                borderRadius: '8px',
                cursor: 'pointer'
              }}
            >
              <Send size={14} />
              {testing ? 'Sending...' : '📧 Send Test Email to Gmail'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Configuration Form & Live HTML Email Preview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        
        {/* Left: Configuration Form */}
        <div className="card" style={{ background: '#ffffff', borderRadius: '12px', padding: '22px', border: '1px solid #e2e8f0' }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '15px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Inbox size={16} color="#4f46e5" />
            Destination Gmail & SMTP Credentials
          </h4>

          {successMsg && (
            <div style={{ padding: '10px 14px', background: '#f0fdf4', color: '#166534', borderRadius: '8px', border: '1px solid #bbf7d0', fontSize: '12px', fontWeight: 600, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle size={15} /> {successMsg}
            </div>
          )}

          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            
            {/* Toggles */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#0f172a' }}>Master Toggle</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Enable email alerts</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.email_enabled}
                  onChange={(e) => setSettings({ ...settings, email_enabled: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: '#4f46e5' }}
                />
              </div>

              <div style={{ padding: '12px', background: '#eef2ff', borderRadius: '8px', border: '1px solid #c7d2fe', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#3730a3' }}>⚡ Automated Send</div>
                  <div style={{ fontSize: '10px', color: '#4338ca' }}>Auto-dispatch on alarms</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.auto_send_enabled}
                  onChange={(e) => setSettings({ ...settings, auto_send_enabled: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: '#4f46e5' }}
                />
              </div>
            </div>

            {/* Destination Email */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px' }}>
                Admin Destination Gmail Address
              </label>
              <input
                type="email"
                value={settings.admin_email}
                onChange={(e) => setSettings({ ...settings, admin_email: e.target.value })}
                placeholder="admin@factorymind.ai"
                className="input mono"
                style={{ width: '100%', padding: '9px 12px', fontSize: '14px', fontWeight: 700, color: '#0f172a' }}
                required
              />
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                Target Gmail inbox where critical failure alerts & diagnostic reports will be delivered.
              </div>
            </div>

            {/* SMTP Server Configuration */}
            <div style={{ padding: '14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Server size={14} color="#4f46e5" /> Gmail / SMTP Outbound Server Settings
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '8px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#475569', marginBottom: '2px' }}>
                    SMTP Host
                  </label>
                  <input
                    type="text"
                    value={settings.smtp_host || 'smtp.gmail.com'}
                    onChange={(e) => setSettings({ ...settings, smtp_host: e.target.value })}
                    placeholder="smtp.gmail.com"
                    className="input mono"
                    style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#475569', marginBottom: '2px' }}>
                    Port
                  </label>
                  <input
                    type="number"
                    value={settings.smtp_port || 587}
                    onChange={(e) => setSettings({ ...settings, smtp_port: parseInt(e.target.value) || 587 })}
                    placeholder="587"
                    className="input mono"
                    style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
                  />
                </div>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#475569', marginBottom: '2px' }}>
                  Gmail Username / Sender Address
                </label>
                <input
                  type="text"
                  value={settings.smtp_user || ''}
                  onChange={(e) => setSettings({ ...settings, smtp_user: e.target.value })}
                  placeholder="your-factory-alerts@gmail.com"
                  className="input mono"
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#475569', marginBottom: '2px' }}>
                  Gmail App Password (16 characters)
                </label>
                <input
                  type="password"
                  value={settings.smtp_password || ''}
                  onChange={(e) => setSettings({ ...settings, smtp_password: e.target.value })}
                  placeholder="•••• •••• •••• ••••"
                  className="input mono"
                  style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
                />
                <div style={{ fontSize: '10.5px', color: '#64748b', marginTop: '4px', lineHeight: 1.4 }}>
                  💡 <strong>How to get Google App Password</strong>: Go to <strong>Google Account → Security → 2-Step Verification → App passwords</strong>, generate a password for "FactoryMind AI", and paste here.
                </div>
              </div>
            </div>

            {/* Severity Triggers */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px' }}>
                Alert Triggers
              </label>
              <div style={{ display: 'flex', gap: '14px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#dc2626', fontWeight: 600, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.notify_on_critical}
                    onChange={(e) => setSettings({ ...settings, notify_on_critical: e.target.checked })}
                    style={{ accentColor: '#dc2626' }}
                  />
                  🚨 Critical Failure Alarms
                </label>

                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', color: '#d97706', fontWeight: 600, cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.notify_on_warning}
                    onChange={(e) => setSettings({ ...settings, notify_on_warning: e.target.checked })}
                    style={{ accentColor: '#d97706' }}
                  />
                  ⚠️ Degradation Warnings
                </label>
              </div>
            </div>

            {/* Save Button */}
            <button
              type="submit"
              disabled={saving}
              className="btn btn-primary"
              style={{
                marginTop: '8px',
                padding: '10px 16px',
                fontWeight: 700,
                fontSize: '13px',
                background: '#4f46e5',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px'
              }}
            >
              <CheckCircle size={16} />
              {saving ? 'Saving...' : 'Save Gmail Settings & Activate Alerts'}
            </button>
          </form>
        </div>

        {/* Right: Live HTML Email Preview */}
        <div className="card" style={{ background: '#ffffff', borderRadius: '12px', padding: '22px', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Mail size={16} color="#4f46e5" />
              Live HTML Email Template Preview
            </h4>
            <span className="badge badge-normal" style={{ fontSize: '10px', background: '#eef2ff', color: '#4338ca' }}>
              RESPONSIVE
            </span>
          </div>

          <div style={{
            border: '1px solid #cbd5e1',
            borderRadius: '8px',
            overflow: 'hidden',
            background: '#ffffff',
            boxShadow: '0 4px 12px rgba(0,0,0,0.05)',
            fontSize: '12px'
          }}>
            {/* Email Header */}
            <div style={{ background: '#0f172a', padding: '16px 20px', color: '#ffffff', textAlign: 'center', borderBottom: '3px solid #dc2626' }}>
              <div style={{ display: 'inline-block', padding: '3px 10px', borderRadius: '12px', background: '#dc2626', color: '#ffffff', fontWeight: 800, fontSize: '10px', marginBottom: '4px' }}>
                🚨 CRITICAL ALERT
              </div>
              <h5 style={{ margin: 0, fontSize: '14px', fontWeight: 800 }}>FactoryMind AI — Machine Health Alert</h5>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>Real-Time Industrial Prognostics Engine</div>
            </div>

            {/* Email Body */}
            <div style={{ padding: '16px' }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a', marginBottom: '12px' }}>
                Industrial Asset: <span style={{ color: '#2563eb' }}>Unit #001 (Turbofan CF6-80C2)</span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', marginBottom: '14px' }}>
                <div style={{ background: '#f8fafc', padding: '8px', borderRadius: '6px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '9px', color: '#64748b', fontWeight: 700 }}>LIFE LEFT</div>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#dc2626' }}>24.5 cycles</div>
                </div>
                <div style={{ background: '#f8fafc', padding: '8px', borderRadius: '6px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '9px', color: '#64748b', fontWeight: 700 }}>HEALTH</div>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#0f172a' }}>52.4%</div>
                </div>
                <div style={{ background: '#f8fafc', padding: '8px', borderRadius: '6px', border: '1px solid #e2e8f0', textAlign: 'center' }}>
                  <div style={{ fontSize: '9px', color: '#64748b', fontWeight: 700 }}>SEVERITY</div>
                  <div style={{ fontSize: '13px', fontWeight: 800, color: '#dc2626' }}>CRITICAL</div>
                </div>
              </div>

              <div style={{ marginBottom: '10px' }}>
                <div style={{ fontSize: '10px', fontWeight: 800, color: '#475569', textTransform: 'uppercase', marginBottom: '4px' }}>🔍 Diagnosed Root Cause</div>
                <div style={{ background: '#f1f5f9', borderLeft: '3px solid #3b82f6', padding: '8px 10px', borderRadius: '4px', fontSize: '11px', color: '#1e293b', lineHeight: 1.4 }}>
                  High thermal degradation observed across HPC stage 1 and LPT turbine blades (+38°R drift).
                </div>
              </div>

              <div style={{ marginBottom: '14px' }}>
                <div style={{ fontSize: '10px', fontWeight: 800, color: '#475569', textTransform: 'uppercase', marginBottom: '4px' }}>🛠️ Recommended Action Plan</div>
                <div style={{ background: '#f0fdf4', borderLeft: '3px solid #10b981', padding: '8px 10px', borderRadius: '4px', fontSize: '11px', color: '#166534', lineHeight: 1.4 }}>
                  Immediate bore-scope inspection & schedule thermal seal replacement.
                </div>
              </div>

              <a
                href="http://localhost:3000"
                target="_blank"
                rel="noreferrer"
                style={{
                  display: 'block',
                  textAlign: 'center',
                  background: '#2563eb',
                  color: '#ffffff',
                  textDecoration: 'none',
                  padding: '9px 0',
                  borderRadius: '6px',
                  fontWeight: 700,
                  fontSize: '12px'
                }}
              >
                Open Live FactoryMind Dashboard →
              </a>
            </div>

            {/* Email Footer */}
            <div style={{ background: '#f8fafc', padding: '10px', textAlign: 'center', fontSize: '9.5px', color: '#94a3b8', borderTop: '1px solid #e2e8f0' }}>
              Delivered directly to {settings.admin_email} • FactoryMind AI
            </div>
          </div>

          <div style={{ marginTop: '14px', display: 'flex', gap: '8px' }}>
            <button
              type="button"
              className="btn btn-sm"
              onClick={() => openEmailDirect(settings.admin_email, '🚨 [CRITICAL] FactoryMind AI Alert: Unit #001', 'High thermal degradation detected on Unit #001.\nEstimated Life Left: 24.5 cycles.\nHealth: 52.4%.\nDashboard: http://localhost:3000')}
              style={{
                flex: 1,
                background: '#f1f5f9',
                color: '#334155',
                border: '1px solid #cbd5e1',
                padding: '8px',
                borderRadius: '6px',
                fontWeight: 700,
                fontSize: '11px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                cursor: 'pointer'
              }}
            >
              <ExternalLink size={12} /> Open in Email Client (Mailto)
            </button>
          </div>
        </div>
      </div>

      {/* Automated Email Dispatch History & Audit Log */}
      <div className="card" style={{ background: '#ffffff', borderRadius: '12px', padding: '22px', border: '1px solid #e2e8f0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={16} color="#4f46e5" />
            Automated Email Dispatch History & Gateway Audit Log
          </h4>
          <button
            className="btn btn-sm"
            onClick={loadAll}
            style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', padding: '4px 10px' }}
          >
            <RefreshCw size={12} /> Refresh Logs
          </button>
        </div>

        {logs.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center', color: '#94a3b8', fontSize: '12px' }}>
            No emails dispatched yet. Click <strong>"🚀 Run Automated Email Alert"</strong> or <strong>"📧 Send Test Email"</strong> above to record your first dispatch.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="table" style={{ width: '100%', fontSize: '12px' }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '8px 10px' }}>Timestamp</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px' }}>Machine / Subject</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px' }}>Destination</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px' }}>Severity</th>
                  <th style={{ textAlign: 'left', padding: '8px 10px' }}>Status</th>
                  <th style={{ textAlign: 'center', padding: '8px 10px' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #f1f5f9' }}>
                    <td style={{ padding: '8px 10px', whiteSpace: 'nowrap', color: '#64748b', fontSize: '11px' }}>
                      {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : 'Just now'}
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <div style={{ fontWeight: 700, color: '#0f172a' }}>{log.subject || `Machine Unit #${String(log.machine_id).padStart(3, '0')}`}</div>
                      <div style={{ fontSize: '10px', color: '#64748b', maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {log.preview || 'Alert notification'}
                      </div>
                    </td>
                    <td style={{ padding: '8px 10px', fontFamily: 'monospace', fontWeight: 600, color: '#4f46e5' }}>
                      {log.dest_email}
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <span className={`badge ${log.severity === 'CRITICAL' ? 'badge-critical' : log.severity === 'TEST' ? 'badge-normal' : 'badge-warning'}`} style={{ fontSize: '10px' }}>
                        {log.severity || 'ALERT'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px' }}>
                      <span className="badge badge-normal" style={{ fontSize: '10px', background: log.status?.includes('DELIVERED') || log.status?.includes('SUCCESS') ? '#10b981' : '#6366f1', color: '#ffffff' }}>
                        ✓ {log.status || 'QUEUED'}
                      </span>
                    </td>
                    <td style={{ padding: '8px 10px', textAlign: 'center' }}>
                      <button
                        className="btn btn-sm"
                        onClick={() => window.location.href = log.mailto_url || `mailto:${log.dest_email}?subject=${encodeURIComponent(log.subject || '')}`}
                        style={{ fontSize: '10px', padding: '3px 8px', background: '#eef2ff', color: '#4338ca', border: '1px solid #c7d2fe', borderRadius: '4px', cursor: 'pointer' }}
                      >
                        Open Email
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}
