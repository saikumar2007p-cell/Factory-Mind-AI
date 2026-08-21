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
  Smartphone
} from 'lucide-react';
import { getWhatsAppSettings, updateWhatsAppSettings, testWhatsAppAlert, openWhatsAppDirect } from '../../services/api';

export default function WhatsAppSettingsPanel() {
  const [settings, setSettings] = useState({
    admin_phone_number: '+1 (555) 019-2834',
    admin_name: 'Factory Administrator',
    whatsapp_enabled: true,
    notify_on_critical: true,
    notify_on_warning: true,
    webhook_url: '',
    total_alerts_dispatched: 0,
    last_alert_sent_at: null
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [testResult, setTestResult] = useState(null);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const res = await getWhatsAppSettings();
      if (res) {
        setSettings(prev => ({ ...prev, ...res }));
      }
    } catch (err) {
      console.warn('Failed to load WhatsApp settings:', err);
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
        // Automatically open WhatsApp direct link in new window
        if (res.click_url) {
          window.open(res.click_url, '_blank', 'noopener,noreferrer');
        }
      }
    } catch (err) {
      alert('Failed to send test alert: ' + (err.message || 'Network error'));
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div className="card" style={{ padding: '40px', textAlign: 'center' }}>
        <RefreshCw size={28} className="spin" color="#3b82f6" style={{ margin: '0 auto 12px auto' }} />
        <div style={{ color: '#64748b', fontSize: '13px' }}>Loading WhatsApp Alert Settings...</div>
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
                  Admin WhatsApp Alert Notifications
                </h3>
                <span className="badge badge-normal" style={{ fontSize: '10px', background: '#059669', color: '#ffffff' }}>
                  ACTIVE & READY
                </span>
              </div>
              <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: '#a7f3d0' }}>
                Send instant failure alerts, critical safety warnings, and prescriptive repair instructions directly to the Admin's phone.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              className="btn btn-sm"
              onClick={handleSendTest}
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
              <Send size={14} />
              {testing ? 'Dispatching...' : '📲 Send Test Alert'}
            </button>
          </div>
        </div>
      </div>

      {/* Main Form & Mobile Preview Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        
        {/* Left: Configuration Form */}
        <div className="card" style={{ background: '#ffffff', borderRadius: '12px', padding: '22px', border: '1px solid #e2e8f0' }}>
          <h4 style={{ margin: '0 0 16px 0', fontSize: '15px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Phone size={16} color="#059669" />
            Admin Phone & Notification Rules
          </h4>

          <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {/* Master Toggle */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 14px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
              <div>
                <div style={{ fontSize: '13px', fontWeight: 700, color: '#0f172a' }}>Enable WhatsApp Alerts</div>
                <div style={{ fontSize: '11px', color: '#64748b' }}>Master switch to broadcast machine failure alerts to WhatsApp</div>
              </div>
              <input
                type="checkbox"
                checked={settings.whatsapp_enabled}
                onChange={(e) => setSettings({ ...settings, whatsapp_enabled: e.target.checked })}
                style={{ width: '18px', height: '18px', cursor: 'pointer', accentColor: '#10b981' }}
              />
            </div>

            {/* Admin Phone Number */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px' }}>
                Admin WhatsApp Phone Number (with Country Code)
              </label>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="text"
                  value={settings.admin_phone_number}
                  onChange={(e) => setSettings({ ...settings, admin_phone_number: e.target.value })}
                  placeholder="e.g. +1 (555) 019-2834 or +91 9876543210"
                  className="input mono"
                  style={{ flex: 1, padding: '9px 12px', fontSize: '14px', fontWeight: 600 }}
                  required
                />
              </div>
              <div style={{ fontSize: '11px', color: '#64748b', marginTop: '4px' }}>
                Include standard country code prefix (e.g. <code>+1</code>, <code>+91</code>, <code>+44</code>). Alerts are sent to this WhatsApp number.
              </div>
            </div>

            {/* Admin Name */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '6px' }}>
                Recipient Admin Name
              </label>
              <input
                type="text"
                value={settings.admin_name}
                onChange={(e) => setSettings({ ...settings, admin_name: e.target.value })}
                placeholder="e.g. Chief Plant Admin"
                className="input"
                style={{ width: '100%', padding: '9px 12px', fontSize: '13px' }}
              />
            </div>

            {/* Notification Triggers */}
            <div>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 700, color: '#334155', marginBottom: '8px' }}>
                Trigger Conditions
              </label>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', color: '#0f172a', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.notify_on_critical}
                    onChange={(e) => setSettings({ ...settings, notify_on_critical: e.target.checked })}
                    style={{ accentColor: '#ef4444' }}
                  />
                  <span>🔴 <strong>Critical Safety Alerts</strong> (RUL &lt; 30 cycles or severe anomaly)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '12px', color: '#0f172a', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={settings.notify_on_warning}
                    onChange={(e) => setSettings({ ...settings, notify_on_warning: e.target.checked })}
                    style={{ accentColor: '#f59e0b' }}
                  />
                  <span>🟡 <strong>Maintenance Warnings</strong> (RUL &lt; 60 cycles or thermal drift)</span>
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
                {saving ? 'Saving...' : 'Save WhatsApp Settings'}
              </button>

              {saveSuccess && (
                <span style={{ fontSize: '12px', color: '#16a34a', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <CheckCircle2 size={16} /> Saved!
                </span>
              )}
            </div>
          </form>

          {/* Stats Bar */}
          <div style={{ marginTop: '20px', paddingTop: '14px', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#64748b' }}>
            <span>Total Alerts Sent: <strong className="mono" style={{ color: '#0f172a' }}>{settings.total_alerts_dispatched || 0}</strong></span>
            <span>Last Dispatched: <strong style={{ color: '#0f172a' }}>{settings.last_alert_sent_at ? new Date(settings.last_alert_sent_at).toLocaleTimeString() : 'None yet'}</strong></span>
          </div>
        </div>

        {/* Right: Live Mobile WhatsApp Alert Preview */}
        <div className="card" style={{ background: '#ffffff', borderRadius: '12px', padding: '22px', border: '1px solid #e2e8f0' }}>
          <h4 style={{ margin: '0 0 14px 0', fontSize: '15px', fontWeight: 700, color: '#0f172a', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Smartphone size={16} color="#059669" />
            Live WhatsApp Message Preview
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
                <div style={{ fontSize: '10px', color: '#25d366' }}>● Online | Verified Industrial Alerts</div>
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

            {/* Test Link Button */}
            <div style={{ marginTop: '14px', textAlign: 'center' }}>
              <button
                onClick={handleSendTest}
                className="btn btn-sm"
                style={{
                  background: 'rgba(37, 211, 102, 0.15)',
                  color: '#25d366',
                  border: '1px solid #25d366',
                  fontSize: '11px',
                  fontWeight: 700,
                  padding: '6px 14px',
                  borderRadius: '6px',
                  cursor: 'pointer'
                }}
              >
                <ExternalLink size={12} style={{ display: 'inline', marginRight: '4px' }} />
                Open in WhatsApp Web / App
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
