import React, { useState, useEffect } from 'react';
import {
  MessageSquare,
  Phone,
  ShieldCheck,
  Send,
  CheckCircle2,
  AlertTriangle,
  Bell,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Sliders,
  Smartphone,
  Zap,
  Radio,
  Server,
  Key,
  Globe
} from 'lucide-react';
import {
  getWhatsAppSettings,
  updateWhatsAppSettings,
  testWhatsAppAlert,
  getWhatsAppLogs,
  sendWhatsAppAlert,
  openWhatsAppDirect
} from '../../services/api';

export default function WhatsAppSettingsPanel() {
  const [settings, setSettings] = useState({
    admin_phone_number: '+91 6303736452',
    admin_name: 'Factory Administrator',
    whatsapp_enabled: true,
    auto_send_enabled: true,
    notify_on_critical: true,
    notify_on_warning: true,
    provider: 'callmebot',
    callmebot_api_key: '',
    webhook_url: '',
    twilio_account_sid: '',
    twilio_auth_token: '',
    twilio_from_number: 'whatsapp:+14155238886',
    meta_phone_number_id: '',
    meta_access_token: '',
    total_alerts_dispatched: 0,
    last_alert_sent_at: null
  });

  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    loadAll();
  }, []);

  const loadAll = async () => {
    try {
      setLoading(true);
      const [settRes, logsRes] = await Promise.allSettled([
        getWhatsAppSettings(),
        getWhatsAppLogs()
      ]);
      if (settRes.status === 'fulfilled' && settRes.value) {
        setSettings(prev => ({ ...prev, ...settRes.value }));
      }
      if (logsRes.status === 'fulfilled' && logsRes.value && logsRes.value.logs) {
        setLogs(logsRes.value.logs);
      }
    } catch (err) {
      console.warn('Failed to load WhatsApp data:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (e) => {
    if (e) e.preventDefault();
    try {
      setSaving(true);
      setSaveSuccess(false);
      const res = await updateWhatsAppSettings(settings);
      if (res && res.success) {
        setSaveSuccess(true);
        setTimeout(() => setSaveSuccess(false), 4000);
        await loadAll();
      }
    } catch (err) {
      alert('Error saving WhatsApp settings: ' + (err.message || 'Unknown error'));
    } finally {
      setSaving(false);
    }
  };

  const handleSendTest = async () => {
    try {
      setTesting(true);
      setTestResult(null);
      const res = await testWhatsAppAlert(settings.admin_phone_number);
      if (res && res.success) {
        setTestResult(res);
        await loadAll();
      }
    } catch (err) {
      alert('Failed to send test alert: ' + (err.message || 'Network error'));
    } finally {
      setTesting(false);
    }
  };

  const handleTriggerSimulatedAlert = async () => {
    try {
      setTesting(true);
      const res = await sendWhatsAppAlert({
        machine_id: 1,
        machine_type: 'Industrial Turbofan Engine',
        severity: 'CRITICAL',
        reason: 'Automated Alert: HPC temperature drift exceeds safe baseline limits by +34°R',
        action: 'Immediate bore-scope inspection & schedule HPC seal replacement',
        rul: 24.5,
        health: 54.0
      });
      if (res && res.success) {
        setTestResult(res);
        await loadAll();
      }
    } catch (err) {
      alert('Failed to dispatch automated alert: ' + (err.message || 'Error'));
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
        <RefreshCw size={28} className="spin" color="#3b82f6" style={{ margin: '0 auto 12px auto' }} />
        <div style={{ color: '#64748b', fontSize: '13px' }}>Loading Automated WhatsApp Settings...</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      
      {/* Header Banner */}
      <div className="card" style={{
        background: 'linear-gradient(135deg, #064e3b 0%, #0f172a 100%)',
        border: '1px solid #059669',
        borderRadius: '12px',
        padding: '20px 24px',
        color: '#ffffff',
        boxShadow: '0 4px 16px rgba(5, 150, 105, 0.15)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{
              width: '46px',
              height: '46px',
              borderRadius: '12px',
              background: '#10b981',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 2px 10px rgba(16, 185, 129, 0.4)'
            }}>
              <MessageSquare size={24} color="#ffffff" />
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 800, color: '#ffffff' }}>
                  Automated WhatsApp Notification Bot
                </h3>
                <span className="badge badge-normal" style={{ fontSize: '10px', background: '#059669', color: '#ffffff' }}>
                  AUTOMATED DISPATCH ACTIVE
                </span>
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#a7f3d0' }}>
                Sends automated WhatsApp messages to <strong>{settings.admin_phone_number}</strong> whenever critical machine alarms or degradation anomalies occur.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              className="btn btn-sm"
              onClick={handleTriggerSimulatedAlert}
              disabled={testing}
              style={{
                background: '#10b981',
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
              {testing ? 'Dispatching...' : '⚡ Test Automated Message'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Settings & Mobile Preview */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        
        {/* Left: Configuration Form */}
        <div className="card" style={{ background: '#ffffff', borderRadius: '12px', padding: '22px', border: '1px solid #e2e8f0' }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '15px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Phone size={16} color="#059669" />
            Admin Phone & Automated Gateway Setup
          </h4>

          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            
            {/* Auto-Send Master Toggles */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#0f172a' }}>WhatsApp Alerts</div>
                  <div style={{ fontSize: '10px', color: '#64748b' }}>Master Enable</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.whatsapp_enabled}
                  onChange={(e) => setSettings({ ...settings, whatsapp_enabled: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: '#10b981' }}
                />
              </div>

              <div style={{ padding: '12px', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#166534' }}>⚡ Automated Send</div>
                  <div style={{ fontSize: '10px', color: '#15803d' }}>Auto-dispatch on alarms</div>
                </div>
                <input
                  type="checkbox"
                  checked={settings.auto_send_enabled}
                  onChange={(e) => setSettings({ ...settings, auto_send_enabled: e.target.checked })}
                  style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: '#16a34a' }}
                />
              </div>
            </div>

            {/* Admin Phone Number */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px' }}>
                Admin WhatsApp Phone Number
              </label>
              <input
                type="text"
                value={settings.admin_phone_number}
                onChange={(e) => setSettings({ ...settings, admin_phone_number: e.target.value })}
                placeholder="+91 6303736452"
                className="input mono"
                style={{ width: '100%', padding: '9px 12px', fontSize: '14px', fontWeight: 700, color: '#0f172a' }}
                required
              />
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                Your destination WhatsApp number for all failure broadcasts & diagnostic plans.
              </div>
            </div>

            {/* Gateway Provider Selection */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px' }}>
                Automated Gateway Provider
              </label>
              <select
                className="input"
                value={settings.provider}
                onChange={(e) => setSettings({ ...settings, provider: e.target.value })}
                style={{ width: '100%', padding: '9px 12px', fontSize: '13px', fontWeight: 600 }}
              >
                <option value="exotel">🇮🇳 Exotel SMS Gateway (Connected — India Telecom Automated SMS)</option>
                <option value="callmebot">CallMeBot Free API (Instant Zero-Config WhatsApp)</option>
                <option value="webhook">Custom Webhook / UltraMsg / Green-API / n8n</option>
                <option value="twilio">Twilio WhatsApp Business API</option>
                <option value="meta_cloud">Meta WhatsApp Cloud API (Graph API)</option>
                <option value="direct_whatsapp">Direct WhatsApp Web / Mobile Deep Linking</option>
              </select>
            </div>

            {/* Provider-Specific Fields */}
            {settings.provider === 'exotel' && (
              <div style={{ padding: '14px', background: '#f0fdf4', borderRadius: '8px', border: '1px solid #86efac', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: '12px', fontWeight: 700, color: '#166534', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Server size={14} color="#16a34a" /> Exotel India SMS Gateway Credentials
                  </div>
                  <span className="badge badge-normal" style={{ fontSize: '10px', background: '#16a34a', color: '#ffffff' }}>
                    ACTIVE
                  </span>
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#14532d', marginBottom: '2px' }}>
                    Exotel API Key
                  </label>
                  <input
                    type="text"
                    value={settings.exotel_api_key}
                    onChange={(e) => setSettings({ ...settings, exotel_api_key: e.target.value })}
                    placeholder="1a8b86a55a41a3f8936fd8e6eed1dbed4e969de265670307"
                    className="input mono"
                    style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#14532d', marginBottom: '2px' }}>
                    Exotel API Token
                  </label>
                  <input
                    type="password"
                    value={settings.exotel_api_token}
                    onChange={(e) => setSettings({ ...settings, exotel_api_token: e.target.value })}
                    placeholder="f6dad415da3eaec7d0539622ef4943d90d303490d4cf62ef"
                    className="input mono"
                    style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
                  />
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#14532d', marginBottom: '2px' }}>
                      Account SID / Subdomain
                    </label>
                    <input
                      type="text"
                      value={settings.exotel_subdomain || 'api.exotel.com'}
                      onChange={(e) => setSettings({ ...settings, exotel_subdomain: e.target.value })}
                      placeholder="api.exotel.com"
                      className="input mono"
                      style={{ width: '100%', padding: '6px 10px', fontSize: '11px' }}
                    />
                  </div>

                  <div>
                    <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#14532d', marginBottom: '2px' }}>
                      Sender / Virtual Number
                    </label>
                    <input
                      type="text"
                      value={settings.exotel_sender_id || '08047104710'}
                      onChange={(e) => setSettings({ ...settings, exotel_sender_id: e.target.value })}
                      placeholder="08047104710"
                      className="input mono"
                      style={{ width: '100%', padding: '6px 10px', fontSize: '11px' }}
                    />
                  </div>
                </div>
              </div>
            )}

            {settings.provider === 'callmebot' && (
              <div style={{ padding: '12px', background: '#eff6ff', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
                <div style={{ fontSize: '12px', fontWeight: 700, color: '#1e40af', marginBottom: '4px' }}>
                  CallMeBot API Key (Free Automated WhatsApp)
                </div>
                <input
                  type="text"
                  value={settings.callmebot_api_key}
                  onChange={(e) => setSettings({ ...settings, callmebot_api_key: e.target.value })}
                  placeholder="Paste CallMeBot API Key (e.g. 1234567)"
                  className="input mono"
                  style={{ width: '100%', padding: '7px 10px', fontSize: '12px' }}
                />
                <div style={{ fontSize: '10.5px', color: '#3b82f6', marginTop: '6px', lineHeight: 1.4 }}>
                  💡 <strong>How to get free key</strong>: Add <code>+34 644 76 66 43</code> on WhatsApp and send <code>I allow callmebot to send me messages</code> to get your free API key in 5 seconds.
                </div>
              </div>
            )}

            {settings.provider === 'webhook' && (
              <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#334155', marginBottom: '4px' }}>
                  Webhook URL (POST payload endpoint)
                </label>
                <input
                  type="url"
                  value={settings.webhook_url}
                  onChange={(e) => setSettings({ ...settings, webhook_url: e.target.value })}
                  placeholder="https://api.ultramsg.com/... or https://hook.eu1.make.com/..."
                  className="input mono"
                  style={{ width: '100%', padding: '7px 10px', fontSize: '12px' }}
                />
              </div>
            )}

            {settings.provider === 'twilio' && (
              <div style={{ padding: '12px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#334155', marginBottom: '2px' }}>
                    Twilio Account SID
                  </label>
                  <input
                    type="text"
                    value={settings.twilio_account_sid}
                    onChange={(e) => setSettings({ ...settings, twilio_account_sid: e.target.value })}
                    placeholder="ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
                    className="input mono"
                    style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
                  />
                </div>
                <div>
                  <label style={{ display: 'block', fontSize: '11px', fontWeight: 700, color: '#334155', marginBottom: '2px' }}>
                    Twilio Auth Token
                  </label>
                  <input
                    type="password"
                    value={settings.twilio_auth_token}
                    onChange={(e) => setSettings({ ...settings, twilio_auth_token: e.target.value })}
                    placeholder="••••••••••••••••••••••••"
                    className="input mono"
                    style={{ width: '100%', padding: '6px 10px', fontSize: '12px' }}
                  />
                </div>
              </div>
            )}

            {/* Notification Triggers */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '8px' }}>
                Automated Triggers
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#0f172a', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.notify_on_critical}
                    onChange={(e) => setSettings({ ...settings, notify_on_critical: e.target.checked })}
                    style={{ accentColor: '#ef4444' }}
                  />
                  <span>🔴 <strong>Critical Alarms</strong> (RUL &lt; 30 cycles or severe anomaly)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: '#0f172a', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.notify_on_warning}
                    onChange={(e) => setSettings({ ...settings, notify_on_warning: e.target.checked })}
                    style={{ accentColor: '#f59e0b' }}
                  />
                  <span>🟡 <strong>Maintenance Warnings</strong> (RUL &lt; 60 cycles)</span>
                </label>
              </div>
            </div>

            {/* Save Button */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '10px' }}>
              <button
                type="submit"
                className="btn btn-primary"
                disabled={saving}
                style={{ flex: 1, padding: '10px', fontSize: '13px', fontWeight: 700 }}
              >
                {saving ? 'Saving...' : 'Save Settings & Activate Bot'}
              </button>

              {saveSuccess && (
                <span style={{ fontSize: '12px', color: '#16a34a', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CheckCircle2 size={16} /> Saved!
                </span>
              )}
            </div>
          </form>
        </div>

        {/* Right: Live Mobile WhatsApp Alert Preview & Test Response */}
        <div className="card" style={{ background: '#ffffff', borderRadius: '12px', padding: '22px', border: '1px solid #e2e8f0' }}>
          <h4 style={{ margin: '0 0 14px 0', fontSize: '15px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Smartphone size={16} color="#059669" />
            Live WhatsApp Alert Mobile Preview
          </h4>

          {/* Mock Mobile Phone Screen */}
          <div style={{
            background: '#0b141a',
            borderRadius: '16px',
            padding: '16px',
            border: '2px solid #1f2c34',
            boxShadow: '0 8px 24px rgba(0,0,0,0.15)',
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
          }}>
            {/* Phone Header Bar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', paddingBottom: '12px', borderBottom: '1px solid #1f2c34', marginBottom: '14px' }}>
              <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#25d366', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, color: '#ffffff', fontSize: '14px' }}>
                FM
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#e9edef' }}>FactoryMind AI Bot</div>
                <div style={{ fontSize: '10px', color: '#25d366' }}>● Automated Gateway: {settings.provider.toUpperCase()}</div>
              </div>
            </div>

            {/* WhatsApp Chat Bubble */}
            <div style={{
              background: '#005c4b',
              borderRadius: '8px',
              borderTopLeftRadius: '2px',
              padding: '12px 14px',
              color: '#e9edef',
              fontSize: '12.5px',
              lineHeight: 1.5,
              position: 'relative'
            }}>
              <div style={{ fontWeight: 800, color: '#ffb703', marginBottom: '4px', fontSize: '13px' }}>
                🚨 FactoryMind AI — URGENT CRITICAL ALERT 🚨
              </div>
              <div style={{ color: '#8696a0', fontSize: '10px', marginBottom: '8px' }}>
                ━━━━━━━━━━━━━━━━━━━━
              </div>
              <div>🏭 <strong>Machine</strong>: Unit #001 (Turbofan Engine)</div>
              <div>⚠️ <strong>Severity</strong>: <span style={{ color: '#ff6b6b', fontWeight: 800 }}>CRITICAL</span></div>
              <div>📉 <strong>Estimated Life Left</strong>: 35.0 cycles</div>
              <div>🩺 <strong>Machine Health</strong>: 64.2%</div>
              <div style={{ color: '#8696a0', fontSize: '10px', margin: '4px 0' }}>
                ━━━━━━━━━━━━━━━━━━━━
              </div>
              <div>🔍 <strong>Diagnosed Cause</strong>:</div>
              <div style={{ color: '#d1d7db', fontSize: '11.5px', marginLeft: '4px' }}>
                High thermal degradation & abnormal friction on LPT turbine blades.
              </div>
              <div style={{ marginTop: '6px' }}>🛠️ <strong>Recommended Action</strong>:</div>
              <div style={{ color: '#d1d7db', fontSize: '11.5px', marginLeft: '4px' }}>
                Immediate bore-scope inspection & schedule thermal seal replacement.
              </div>
              <div style={{ color: '#8696a0', fontSize: '10px', margin: '4px 0' }}>
                ━━━━━━━━━━━━━━━━━━━━
              </div>
              <div style={{ color: '#53bdeb', textDecoration: 'underline', cursor: 'pointer', fontSize: '11px', marginTop: '4px' }}>
                🔗 http://localhost:3000 (Open Dashboard)
              </div>

              <div style={{ textAlign: 'right', fontSize: '10px', color: '#8696a0', marginTop: '6px' }}>
                Just now <span style={{ color: '#53bdeb' }}>✓✓</span>
              </div>
            </div>

            {/* Direct Open Button */}
            <div style={{ marginTop: '14px', textAlign: 'center' }}>
              <a
                href={testResult?.click_url || `https://wa.me/916303736452`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-sm"
                style={{
                  background: 'rgba(37, 211, 102, 0.15)',
                  color: '#25d366',
                  border: '1px solid #25d366',
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '6px 14px',
                  borderRadius: '6px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                  textDecoration: 'none'
                }}
              >
                <ExternalLink size={12} />
                Open in WhatsApp Web / App
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Automated Dispatch Audit Trail Table */}
      <div className="card" style={{ background: '#ffffff', borderRadius: '12px', padding: '20px', border: '1px solid #e2e8f0' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={16} color="#059669" />
            <h4 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: '#0f172a' }}>
              Automated Dispatch History & Gateway Audit Log
            </h4>
          </div>
          <button className="btn btn-secondary btn-sm" onClick={loadAll} style={{ fontSize: '11px', padding: '4px 10px' }}>
            <RefreshCw size={12} style={{ display: 'inline', marginRight: '4px' }} /> Refresh Logs
          </button>
        </div>

        {logs.length === 0 ? (
          <div style={{ padding: '30px', textAlign: 'center', color: '#64748b', fontSize: '12px' }}>
            No automated WhatsApp messages dispatched yet. Click <strong>"⚡ Test Automated Message"</strong> above to dispatch the first alert!
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table" style={{ fontSize: '12px' }}>
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Machine</th>
                  <th>Severity</th>
                  <th>Destination Phone</th>
                  <th>Gateway Provider</th>
                  <th>Delivery Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((l, idx) => (
                  <tr key={idx}>
                    <td className="mono" style={{ fontSize: '11px' }}>
                      {l.timestamp ? new Date(l.timestamp).toLocaleTimeString() : 'Recent'}
                    </td>
                    <td>{l.machine_id ? `Unit #${String(l.machine_id).padStart(3, '0')}` : 'System Test'}</td>
                    <td>
                      <span className={`badge ${l.severity === 'CRITICAL' ? 'badge-critical' : (l.severity === 'WARNING' ? 'badge-warning' : 'badge-normal')}`}>
                        {l.severity}
                      </span>
                    </td>
                    <td className="mono" style={{ fontWeight: 600 }}>{l.phone_number}</td>
                    <td style={{ textTransform: 'uppercase', fontSize: '11px', fontWeight: 700 }}>{l.provider}</td>
                    <td>
                      <span className="badge badge-normal" style={{ fontSize: '10px', background: '#f0fdf4', color: '#166534', border: '1px solid #bbf7d0' }}>
                        ✓ {l.status}
                      </span>
                    </td>
                    <td>
                      <a
                        href={l.click_url || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="btn btn-secondary btn-sm"
                        style={{ padding: '2px 8px', fontSize: '11px', display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                      >
                        <ExternalLink size={10} /> View in WhatsApp
                      </a>
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
