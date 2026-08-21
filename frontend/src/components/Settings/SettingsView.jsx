import React, { useState, useEffect } from 'react';
import {
  Settings,
  ShieldCheck,
  Database,
  Radio,
  Sparkles,
  Server,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock,
  Key,
  Wifi,
  FileText,
  Layers,
  ArrowRight,
  Info,
  Lock,
  Smartphone,
  MessageSquare
} from 'lucide-react';
import {
  getDataSources,
  getActiveDataSource,
  setActiveDataSource,
  configureDataSource,
  testDataSourceConnection,
  uploadTelemetryFile,
  getSensorMappings,
  getSecurityLogs
} from '../../services/api';

import ModelVersionPanel from './ModelVersionPanel';
import UserManagementPanel from './UserManagementPanel';
import MachineRegistrationQueue from './MachineRegistrationQueue';
import DatasetSelector from '../Datasets/DatasetSelector';
import WhatsAppSettingsPanel from './WhatsAppSettingsPanel';

export default function SettingsView({ userRole = 'ADMIN' }) {
  if (userRole !== 'ADMIN') {
    return (
      <div className="card" style={{ padding: '60px 40px', textAlign: 'center', maxWidth: '580px', margin: '60px auto', borderTop: '4px solid #dc2626' }}>
        <div style={{ width: '64px', height: '64px', borderRadius: '50%', background: '#fef2f2', border: '2px solid #fca5a5', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px auto' }}>
          <Lock size={32} color="#dc2626" />
        </div>
        <h2 style={{ fontSize: '20px', fontWeight: 800, color: '#991b1b', marginBottom: '8px' }}>
          Administrator Access Required
        </h2>
        <p style={{ fontSize: '14px', color: '#64748b', lineHeight: 1.6, marginBottom: '24px' }}>
          Platform Settings, Data Connectors, User Management, Model Deployments, and Machine Registration Queues are strictly restricted to <strong>Administrator</strong> accounts.
        </p>
        <div style={{ display: 'inline-block', padding: '6px 14px', borderRadius: '6px', background: '#f1f5f9', border: '1px solid #cbd5e1', fontSize: '12px', fontWeight: 600, color: '#334155' }}>
          Current Role: <strong>{userRole}</strong> (Access Denied)
        </div>
      </div>
    );
  }

  const [activeTab, setActiveTab] = useState('datasets'); // 'datasets' | 'connectors' | 'models' | 'registrations' | 'users' | 'security'
  const [sources, setSources] = useState([]);
  const [activeSource, setActiveSource] = useState(null);
  const [selectedConnector, setSelectedConnector] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionMessage, setActionMessage] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [testingConnection, setTestingConnection] = useState(false);
  const [securityLogs, setSecurityLogs] = useState([]);
  const [loadingLogs, setLoadingLogs] = useState(false);


  // REST Config State
  const [restEndpoint, setRestEndpoint] = useState('');
  const [restInterval, setRestInterval] = useState(5.0);
  const [restAuthType, setRestAuthType] = useState('none');
  const [restApiKey, setRestApiKey] = useState('');
  const [restBearerToken, setRestBearerToken] = useState('');
  const [restEnabled, setRestEnabled] = useState(false);

  // MQTT Config State
  const [mqttBroker, setMqttBroker] = useState('');
  const [mqttPort, setMqttPort] = useState(1883);
  const [mqttTopic, setMqttTopic] = useState('factory/telemetry/#');
  const [mqttClientId, setMqttClientId] = useState('factorymind-edge-client');
  const [mqttQos, setMqttQos] = useState(1);
  const [mqttTls, setMqttTls] = useState(false);
  const [mqttUsername, setMqttUsername] = useState('');
  const [mqttPassword, setMqttPassword] = useState('');
  const [mqttEnabled, setMqttEnabled] = useState(false);

  // CSV File Ingest State
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadLoading, setUploadLoading] = useState(false);
  const [uploadResult, setUploadResult] = useState(null);
  const [uploadError, setUploadError] = useState(null);

  const fetchSources = async () => {
    try {
      setLoading(true);
      const [srcList, active] = await Promise.allSettled([
        getDataSources(),
        getActiveDataSource()
      ]);
      if (srcList.status === 'fulfilled') setSources(srcList.value || []);
      if (active.status === 'fulfilled') {
        setActiveSource(active.value);
        // Pre-fill REST & MQTT if available
        const rest = srcList.value?.find(s => s.source_id === 'rest_api_connector');
        if (rest?.details) {
          setRestEndpoint(rest.details.endpoint_url === 'Not Configured' ? '' : rest.details.endpoint_url || '');
          setRestInterval(rest.details.polling_interval_seconds || 5.0);
          setRestAuthType(rest.details.auth_type || 'none');
          setRestApiKey(rest.details.api_key || '');
          setRestBearerToken(rest.details.bearer_token || '');
          setRestEnabled(rest.details.is_enabled || false);
        }
        const mqtt = srcList.value?.find(s => s.source_id === 'mqtt_iot_connector');
        if (mqtt?.details) {
          setMqttBroker(mqtt.details.broker_url === 'Not Configured' ? '' : mqtt.details.broker_url || '');
          setMqttPort(mqtt.details.port || 1883);
          setMqttTopic(mqtt.details.topic || 'factory/telemetry/#');
          setMqttClientId(mqtt.details.client_id || 'factorymind-edge-client');
          setMqttQos(mqtt.details.qos !== undefined ? mqtt.details.qos : 1);
          setMqttTls(mqtt.details.tls_enabled || false);
          setMqttEnabled(mqtt.details.is_enabled || false);
        }
      }
    } catch (e) {
      console.error('Failed to load data sources', e);
    } finally {
      setLoading(false);
    }
  };

  const fetchSecurityLogs = async () => {
    if (userRole !== 'ADMIN') return;
    try {
      setLoadingLogs(true);
      const res = await getSecurityLogs(50);
      setSecurityLogs(res?.logs || []);
    } catch (e) {
      console.warn('Could not load security logs:', e);
    } finally {
      setLoadingLogs(false);
    }
  };

  useEffect(() => {
    fetchSources();
    fetchSecurityLogs();
  }, [userRole]);

  const handleTestConnection = async (sourceId) => {
    setTestingConnection(true);
    setTestResult(null);
    try {
      const res = await testDataSourceConnection(sourceId);
      setTestResult(res);
    } catch (err) {
      setTestResult({ success: false, message: err.message });
    } finally {
      setTestingConnection(false);
    }
  };

  const handleSaveRestConfig = async (e) => {
    e.preventDefault();
    setActionMessage(null);
    try {
      const res = await configureDataSource('rest_api_connector', {
        endpoint_url: restEndpoint,
        polling_interval_seconds: parseFloat(restInterval) || 5.0,
        auth_type: restAuthType,
        api_key: restApiKey,
        bearer_token: restBearerToken,
        is_enabled: restEnabled
      });
      setActionMessage({ type: 'success', text: res.message || 'REST configuration saved successfully.' });
      await fetchSources();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleSaveMqttConfig = async (e) => {
    e.preventDefault();
    setActionMessage(null);
    try {
      const res = await configureDataSource('mqtt_iot_connector', null, {
        broker_url: mqttBroker,
        port: parseInt(mqttPort, 10) || 1883,
        topic: mqttTopic,
        client_id: mqttClientId,
        qos: parseInt(mqttQos, 10) || 1,
        tls_enabled: mqttTls,
        username: mqttUsername,
        password: mqttPassword,
        is_enabled: mqttEnabled
      });
      setActionMessage({ type: 'success', text: res.message || 'MQTT configuration saved successfully.' });
      await fetchSources();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  const handleFileUpload = async (e) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploadLoading(true);
    setUploadError(null);
    setUploadResult(null);
    try {
      const res = await uploadTelemetryFile(uploadFile);
      setUploadResult(res);
    } catch (err) {
      setUploadError(err.message);
    } finally {
      setUploadLoading(false);
    }
  };

  const handleSwitchActiveSource = async (sourceId) => {
    try {
      const res = await setActiveDataSource(sourceId);
      setActionMessage({ type: 'success', text: res.message });
      await fetchSources();
    } catch (err) {
      setActionMessage({ type: 'error', text: err.message });
    }
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto' }}>
      {/* Page Header */}
      <div className="page-header">
        <h2 className="page-title">Platform & Data Source Architecture</h2>
        <p className="page-description">
          Unified industrial telemetry adapters, canonical schema mappings, data quality validation, and ML prognostic compatibility.
        </p>
      </div>

      {/* Settings Navigation Tabs */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '24px', borderBottom: '1px solid #1f2937', paddingBottom: '12px', flexWrap: 'wrap' }}>
      <button
          onClick={() => setActiveTab('datasets')}
          className={`btn btn-sm ${activeTab === 'datasets' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Server size={15} />
          Datasets & Equipment
        </button>

        <button
          onClick={() => setActiveTab('connectors')}
          className={`btn btn-sm ${activeTab === 'connectors' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Database size={15} />
          Data Sources & Connectors
        </button>

        <button
          onClick={() => setActiveTab('models')}
          className={`btn btn-sm ${activeTab === 'models' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Layers size={15} />
          Model Governance & Rollback
        </button>

        <button
          onClick={() => setActiveTab('registrations')}
          className={`btn btn-sm ${activeTab === 'registrations' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <Radio size={15} />
          Machine Review Queue
        </button>

        {userRole === 'ADMIN' && (
          <button
            onClick={() => setActiveTab('whatsapp')}
            className={`btn btn-sm ${activeTab === 'whatsapp' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '6px', background: activeTab === 'whatsapp' ? '#059669' : undefined, borderColor: activeTab === 'whatsapp' ? '#059669' : undefined }}
          >
            <Smartphone size={15} color={activeTab === 'whatsapp' ? '#ffffff' : '#10b981'} />
            WhatsApp Alerts
          </button>
        )}

        {userRole === 'ADMIN' && (
          <button
            onClick={() => setActiveTab('users')}
            className={`btn btn-sm ${activeTab === 'users' ? 'btn-primary' : 'btn-secondary'}`}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <ShieldCheck size={15} />
            User Identity & Multi-Admin
          </button>
        )}

        <button
          onClick={() => setActiveTab('security')}
          className={`btn btn-sm ${activeTab === 'security' ? 'btn-primary' : 'btn-secondary'}`}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <ShieldCheck size={15} />
          Security Audit Trail
        </button>
      </div>

      {activeTab === 'whatsapp' && (
        <div style={{ marginBottom: '24px' }}>
          <WhatsAppSettingsPanel />
        </div>
      )}

      {activeTab === 'datasets' && (
        <div style={{ marginBottom: '24px' }}>
          <DatasetSelector
            onSelectDataset={(id) => console.log('Selected dataset:', id)}
            activeDatasetId="NASA_CMAPSS_FD001"
            userRole={userRole}
          />
        </div>
      )}

      {activeTab === 'models' && (
        <div style={{ marginBottom: '24px' }}>
          <ModelVersionPanel machineId={1} userRole={userRole} />
        </div>
      )}

      {activeTab === 'registrations' && (
        <div style={{ marginBottom: '24px' }}>
          <MachineRegistrationQueue userRole={userRole} onMachineCreated={fetchSources} />
        </div>
      )}

      {activeTab === 'users' && (
        <div style={{ marginBottom: '24px' }}>
          <UserManagementPanel userRole={userRole} />
        </div>
      )}

      {activeTab === 'connectors' && (
        <>
          {/* Mandatory Source Transparency Alert */}
          <div
            style={{
              backgroundColor: '#eff6ff',
              border: '1px solid #bfdbfe',
              borderRadius: '8px',
              padding: '14px 18px',
              marginBottom: '24px',
              display: 'flex',
              gap: '12px',
              alignItems: 'flex-start'
            }}
          >
            <Info size={20} color="#2563eb" style={{ flexShrink: 0, marginTop: '2px' }} />
            <div style={{ fontSize: '13px', color: '#1e3a8a', lineHeight: 1.5 }}>
              <strong>Source Transparency & Architectural Contract:</strong>
              <p style={{ marginTop: '4px', marginBottom: 0 }}>
                "The current demonstration uses NASA C-MAPSS FD001 as its simulation data source. The platform is architected to accept real industrial telemetry through REST APIs, MQTT/IoT, or validated file ingestion. The predictive model only produces results when the incoming telemetry is compatible with the model's required feature schema."
              </p>
            </div>
          </div>

          {/* Action Notification */}
          {actionMessage && (
            <div
              style={{
                padding: '12px 16px',
                borderRadius: '6px',
                marginBottom: '20px',
                backgroundColor: actionMessage.type === 'success' ? '#ecfdf5' : '#fef2f2',
                border: `1px solid ${actionMessage.type === 'success' ? '#a7f3d0' : '#fecaca'}`,
                color: actionMessage.type === 'success' ? '#065f46' : '#991b1b',
                fontSize: '13px',
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              {actionMessage.type === 'success' ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
              <span>{actionMessage.text}</span>
            </div>
          )}

          {/* Admin Privilege Lock Banner */}
          {userRole !== 'ADMIN' && (
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.08)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: '8px',
                padding: '12px 16px',
                marginBottom: '20px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px'
              }}
            >
              <ShieldCheck size={18} color="#f87171" />
              <span style={{ fontSize: '12px', color: '#f87171', fontWeight: 500 }}>
                <strong>Administrative Configuration Locked:</strong> You are viewing platform settings in <strong>{userRole}</strong> mode. Connector and data source modifications require Administrator privileges.
              </span>
            </div>
          )}

          {/* Section 1: Active Telemetry Data Source Card */}
          <div className="card" style={{ marginBottom: '24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Database size={20} color="var(--brand-primary)" />
                <h3 style={{ fontSize: '16px', fontWeight: 600 }}>Active Telemetry Source</h3>
              </div>
              <span
                style={{
                  padding: '4px 10px',
                  borderRadius: '20px',
                  fontSize: '12px',
                  fontWeight: 600,
                  backgroundColor: activeSource?.status === 'CONNECTED' ? '#d1fae5' : '#fee2e2',
                  color: activeSource?.status === 'CONNECTED' ? '#065f46' : '#991b1b',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px'
                }}
              >
                <span
                  style={{
                    width: '7px',
                    height: '7px',
                    borderRadius: '50%',
                    backgroundColor: activeSource?.status === 'CONNECTED' ? '#10b981' : '#ef4444'
                  }}
                />
                {activeSource?.status || 'UNKNOWN'}
              </span>
            </div>


        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '16px', fontSize: '13px' }}>
          <div>
            <div style={{ color: 'var(--text-muted)', marginBottom: '2px' }}>Source Name:</div>
            <strong style={{ fontSize: '14px' }}>{activeSource?.name || 'NASA C-MAPSS FD001'}</strong>
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)', marginBottom: '2px' }}>Operational Mode:</div>
            <span
              style={{
                padding: '2px 8px',
                borderRadius: '4px',
                backgroundColor: activeSource?.is_simulation ? '#f1f5f9' : '#ecfdf5',
                color: activeSource?.is_simulation ? '#475569' : '#065f46',
                fontWeight: 600
              }}
            >
              {activeSource?.is_simulation ? 'Simulation / Demo' : 'Real Industrial Telemetry'}
            </span>
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)', marginBottom: '2px' }}>Telemetry Schema:</div>
            <strong>21 Canonical Turbofan Channels (Compatible)</strong>
          </div>
          <div>
            <div style={{ color: 'var(--text-muted)', marginBottom: '2px' }}>Data Freshness:</div>
            <span style={{ color: activeSource?.is_stale ? '#d97706' : '#059669', fontWeight: 600 }}>
              {activeSource?.is_stale ? 'STALE (Heartbeat delayed)' : 'GOOD (Live telemetry)'}
            </span>
          </div>
        </div>
      </div>

      {/* Section 2: Available Industrial Connectors */}
      <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '14px' }}>Available Industrial Connectors</h3>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(270px, 1fr))', gap: '16px', marginBottom: '28px' }}>
        {/* C-MAPSS Simulation */}
        <div
          className="card"
          style={{
            border: activeSource?.source_id === 'cmapss_fd001' ? '2px solid var(--brand-primary)' : '1px solid var(--border-subtle)',
            position: 'relative'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Layers size={18} color="var(--brand-primary)" />
              <strong style={{ fontSize: '14px' }}>C-MAPSS Simulation</strong>
            </div>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#059669', backgroundColor: '#ecfdf5', padding: '2px 6px', borderRadius: '4px' }}>
              Connected
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', minHeight: '36px', marginBottom: '12px' }}>
            Working demonstration source based on 100 run-to-failure turbofan degradation trajectories.
          </p>
          <button
            className="btn btn-secondary"
            style={{ width: '100%', fontSize: '12px' }}
            disabled={activeSource?.source_id === 'cmapss_fd001'}
            onClick={() => handleSwitchActiveSource('cmapss_fd001')}
          >
            {activeSource?.source_id === 'cmapss_fd001' ? 'Active Demo Source' : 'Set as Active Source'}
          </button>
        </div>

        {/* REST API */}
        <div
          className="card"
          style={{
            border: activeSource?.source_id === 'rest_api_connector' ? '2px solid var(--brand-primary)' : '1px solid var(--border-subtle)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Server size={18} color="#0284c7" />
              <strong style={{ fontSize: '14px' }}>REST API Connector</strong>
            </div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: restEndpoint ? '#059669' : '#64748b',
                backgroundColor: restEndpoint ? '#ecfdf5' : '#f1f5f9',
                padding: '2px 6px',
                borderRadius: '4px'
              }}
            >
              {restEndpoint ? 'Configured' : 'Not Configured'}
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', minHeight: '36px', marginBottom: '12px' }}>
            HTTP polling and webhook ingest boundary for plant SCADA and historian servers.
          </p>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-secondary"
              style={{ flex: 1, fontSize: '12px' }}
              onClick={() => {
                setSelectedConnector(selectedConnector === 'rest_api_connector' ? null : 'rest_api_connector');
                setTestResult(null);
              }}
            >
              {selectedConnector === 'rest_api_connector' ? 'Close Config' : 'Configure'}
            </button>
            {restEndpoint && (
              <button
                className="btn btn-primary"
                style={{ fontSize: '12px' }}
                disabled={activeSource?.source_id === 'rest_api_connector'}
                onClick={() => handleSwitchActiveSource('rest_api_connector')}
              >
                Set Active
              </button>
            )}
          </div>
        </div>

        {/* MQTT / IoT */}
        <div
          className="card"
          style={{
            border: activeSource?.source_id === 'mqtt_iot_connector' ? '2px solid var(--brand-primary)' : '1px solid var(--border-subtle)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Wifi size={18} color="#8b5cf6" />
              <strong style={{ fontSize: '14px' }}>MQTT / Industrial IoT</strong>
            </div>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: mqttBroker ? '#059669' : '#64748b',
                backgroundColor: mqttBroker ? '#ecfdf5' : '#f1f5f9',
                padding: '2px 6px',
                borderRadius: '4px'
              }}
            >
              {mqttBroker ? 'Configured' : 'Not Configured'}
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', minHeight: '36px', marginBottom: '12px' }}>
            Pub/sub broker connector for edge PLCs, IoT gateways, and machine telemetry topics.
          </p>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button
              className="btn btn-secondary"
              style={{ flex: 1, fontSize: '12px' }}
              onClick={() => {
                setSelectedConnector(selectedConnector === 'mqtt_iot_connector' ? null : 'mqtt_iot_connector');
                setTestResult(null);
              }}
            >
              {selectedConnector === 'mqtt_iot_connector' ? 'Close Config' : 'Configure'}
            </button>
            {mqttBroker && (
              <button
                className="btn btn-primary"
                style={{ fontSize: '12px' }}
                disabled={activeSource?.source_id === 'mqtt_iot_connector'}
                onClick={() => handleSwitchActiveSource('mqtt_iot_connector')}
              >
                Set Active
              </button>
            )}
          </div>
        </div>

        {/* CSV File Import */}
        <div
          className="card"
          style={{
            border: activeSource?.source_id === 'csv_file_import' ? '2px solid var(--brand-primary)' : '1px solid var(--border-subtle)'
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} color="#ea580c" />
              <strong style={{ fontSize: '14px' }}>CSV / File Ingestion</strong>
            </div>
            <span style={{ fontSize: '11px', fontWeight: 600, color: '#059669', backgroundColor: '#ecfdf5', padding: '2px 6px', borderRadius: '4px' }}>
              Available
            </span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', minHeight: '36px', marginBottom: '12px' }}>
            Batch upload and schema validation for CSV/TSV telemetry files with ML compatibility checks.
          </p>
          <button
            className="btn btn-secondary"
            style={{ width: '100%', fontSize: '12px' }}
            onClick={() => setSelectedConnector(selectedConnector === 'csv_file_import' ? null : 'csv_file_import')}
          >
            {selectedConnector === 'csv_file_import' ? 'Close Ingestion' : 'Upload & Validate CSV'}
          </button>
        </div>
      </div>

      {/* Section 3: Advanced Connector Configuration Panels */}

      {/* REST API Configuration */}
      {selectedConnector === 'rest_api_connector' && (
        <div className="card" style={{ marginBottom: '24px', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Server size={18} color="#0284c7" />
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Industrial REST API Configuration (Admin Only)</h3>
          </div>
          <form onSubmit={handleSaveRestConfig} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  REST Endpoint URL
                </label>
                <input
                  type="url"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  placeholder="https://scada-gateway.plant.corp/api/telemetry"
                  value={restEndpoint}
                  onChange={(e) => setRestEndpoint(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Polling Interval (seconds)
                </label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  value={restInterval}
                  onChange={(e) => setRestInterval(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Authentication Type
                </label>
                <select
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  value={restAuthType}
                  onChange={(e) => setRestAuthType(e.target.value)}
                >
                  <option value="none">None / Public Webhook</option>
                  <option value="api_key">API Key (Header / Query)</option>
                  <option value="bearer_token">Bearer Token (JWT)</option>
                  <option value="basic">Basic Auth</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  API Key (Secret Masked)
                </label>
                <input
                  type="password"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  placeholder="••••••••••"
                  value={restApiKey}
                  onChange={(e) => setRestApiKey(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Bearer Token (Secret Masked)
                </label>
                <input
                  type="password"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  placeholder="••••••••••"
                  value={restBearerToken}
                  onChange={(e) => setRestBearerToken(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '4px' }}>
              <input
                type="checkbox"
                id="restEnabled"
                checked={restEnabled}
                onChange={(e) => setRestEnabled(e.target.checked)}
              />
              <label htmlFor="restEnabled" style={{ fontSize: '13px', cursor: 'pointer' }}>
                Enable REST API polling and webhook ingestion
              </label>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button type="submit" className="btn btn-primary" style={{ fontSize: '13px' }}>
                Save REST Configuration
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '13px' }}
                disabled={testingConnection || !restEndpoint}
                onClick={() => handleTestConnection('rest_api_connector')}
              >
                {testingConnection ? 'Testing Connection...' : 'Test Connection'}
              </button>
            </div>
          </form>

          {/* Test Connection Output */}
          {testResult && (
            <div
              style={{
                marginTop: '14px',
                padding: '10px 14px',
                borderRadius: '6px',
                backgroundColor: testResult.success ? '#ecfdf5' : '#fef2f2',
                border: `1px solid ${testResult.success ? '#a7f3d0' : '#fecaca'}`,
                color: testResult.success ? '#065f46' : '#991b1b',
                fontSize: '12px'
              }}
            >
              <strong>{testResult.success ? 'Success: ' : 'Connection Failed: '}</strong>
              {testResult.message}
            </div>
          )}
        </div>
      )}

      {/* MQTT Configuration */}
      {selectedConnector === 'mqtt_iot_connector' && (
        <div className="card" style={{ marginBottom: '24px', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Wifi size={18} color="#8b5cf6" />
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Industrial MQTT / IoT Broker Configuration (Admin Only)</h3>
          </div>
          <form onSubmit={handleSaveMqttConfig} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 2fr', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Broker URL / IP
                </label>
                <input
                  type="text"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  placeholder="mqtt.plant.corp or 10.0.1.50"
                  value={mqttBroker}
                  onChange={(e) => setMqttBroker(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Port
                </label>
                <input
                  type="number"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  value={mqttPort}
                  onChange={(e) => setMqttPort(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Topic Subscription
                </label>
                <input
                  type="text"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  placeholder="factory/telemetry/#"
                  value={mqttTopic}
                  onChange={(e) => setMqttTopic(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: '14px' }}>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Client ID
                </label>
                <input
                  type="text"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  value={mqttClientId}
                  onChange={(e) => setMqttClientId(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  QoS Level
                </label>
                <select
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  value={mqttQos}
                  onChange={(e) => setMqttQos(e.target.value)}
                >
                  <option value={0}>0 — At most once</option>
                  <option value={1}>1 — At least once</option>
                  <option value={2}>2 — Exactly once</option>
                </select>
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Username
                </label>
                <input
                  type="text"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  placeholder="edge_gateway_user"
                  value={mqttUsername}
                  onChange={(e) => setMqttUsername(e.target.value)}
                />
              </div>
              <div>
                <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                  Password (Masked)
                </label>
                <input
                  type="password"
                  className="search-input"
                  style={{ width: '100%', padding: '8px 12px', backgroundColor: '#fff' }}
                  placeholder="••••••••••"
                  value={mqttPassword}
                  onChange={(e) => setMqttPassword(e.target.value)}
                />
              </div>
            </div>

            <div style={{ display: 'flex', gap: '20px', alignItems: 'center', marginTop: '4px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="mqttTls"
                  checked={mqttTls}
                  onChange={(e) => setMqttTls(e.target.checked)}
                />
                <label htmlFor="mqttTls" style={{ fontSize: '13px', cursor: 'pointer' }}>
                  Enable TLS / SSL
                </label>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <input
                  type="checkbox"
                  id="mqttEnabled"
                  checked={mqttEnabled}
                  onChange={(e) => setMqttEnabled(e.target.checked)}
                />
                <label htmlFor="mqttEnabled" style={{ fontSize: '13px', cursor: 'pointer' }}>
                  Enable MQTT Connector
                </label>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button type="submit" className="btn btn-primary" style={{ fontSize: '13px' }}>
                Save MQTT Configuration
              </button>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ fontSize: '13px' }}
                disabled={testingConnection || !mqttBroker}
                onClick={() => handleTestConnection('mqtt_iot_connector')}
              >
                {testingConnection ? 'Testing Connection...' : 'Test Connection'}
              </button>
            </div>
          </form>

          {/* Test Connection Output */}
          {testResult && (
            <div
              style={{
                marginTop: '14px',
                padding: '10px 14px',
                borderRadius: '6px',
                backgroundColor: testResult.success ? '#ecfdf5' : '#fef2f2',
                border: `1px solid ${testResult.success ? '#a7f3d0' : '#fecaca'}`,
                color: testResult.success ? '#065f46' : '#991b1b',
                fontSize: '12px'
              }}
            >
              <strong>{testResult.success ? 'Success: ' : 'Connection Failed: '}</strong>
              {testResult.message}
            </div>
          )}
        </div>
      )}

      {/* CSV File Ingestion Panel */}
      {selectedConnector === 'csv_file_import' && (
        <div className="card" style={{ marginBottom: '24px', backgroundColor: '#f8fafc', border: '1px solid #cbd5e1' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <UploadCloud size={18} color="#ea580c" />
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Validated CSV / TSV Telemetry Ingestion</h3>
          </div>
          <form onSubmit={handleFileUpload} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, display: 'block', marginBottom: '4px' }}>
                Select Telemetry Dataset (.csv, .tsv, .txt)
              </label>
              <input
                type="file"
                accept=".csv,.tsv,.txt"
                onChange={(e) => setUploadFile(e.target.files[0])}
                style={{ fontSize: '13px' }}
              />
            </div>
            <div>
              <button
                type="submit"
                className="btn btn-primary"
                style={{ fontSize: '13px' }}
                disabled={uploadLoading || !uploadFile}
              >
                {uploadLoading ? 'Parsing & Validating Telemetry...' : 'Upload, Normalize & Check Compatibility'}
              </button>
            </div>
          </form>

          {uploadError && (
            <div
              style={{
                marginTop: '14px',
                padding: '10px 14px',
                borderRadius: '6px',
                backgroundColor: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#991b1b',
                fontSize: '12px'
              }}
            >
              <strong>Upload Error:</strong> {uploadError}
            </div>
          )}

          {uploadResult && (
            <div style={{ marginTop: '16px', borderTop: '1px solid #e2e8f0', paddingTop: '16px' }}>
              <h4 style={{ fontSize: '14px', fontWeight: 600, marginBottom: '10px' }}>Ingestion & Compatibility Report</h4>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '12px', marginBottom: '14px' }}>
                <div style={{ padding: '8px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                  <span style={{ color: '#64748b' }}>Total Rows:</span> <strong>{uploadResult.total_rows}</strong>
                </div>
                <div style={{ padding: '8px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                  <span style={{ color: '#64748b' }}>Valid Normalized Rows:</span> <strong style={{ color: '#059669' }}>{uploadResult.valid_rows}</strong>
                </div>
                <div style={{ padding: '8px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                  <span style={{ color: '#64748b' }}>Quarantined Rows:</span> <strong style={{ color: uploadResult.invalid_rows > 0 ? '#dc2626' : '#64748b' }}>{uploadResult.invalid_rows}</strong>
                </div>
                <div style={{ padding: '8px', backgroundColor: '#fff', borderRadius: '4px', border: '1px solid #e2e8f0' }}>
                  <span style={{ color: '#64748b' }}>Mapped Channels:</span> <strong>{Object.keys(uploadResult.mapped_channels || {}).length} / 21</strong>
                </div>
              </div>

              {/* ML Compatibility Badge */}
              <div
                style={{
                  padding: '12px 14px',
                  borderRadius: '6px',
                  backgroundColor: uploadResult.ml_compatibility?.is_rul_predictable ? '#ecfdf5' : '#fffbeb',
                  border: `1px solid ${uploadResult.ml_compatibility?.is_rul_predictable ? '#a7f3d0' : '#fde68a'}`,
                  color: uploadResult.ml_compatibility?.is_rul_predictable ? '#065f46' : '#92400e',
                  fontSize: '13px',
                  marginBottom: '14px'
                }}
              >
                <strong>ML Compatibility Status: {uploadResult.ml_compatibility?.status}</strong>
                <p style={{ marginTop: '4px', marginBottom: 0, fontSize: '12px' }}>
                  {uploadResult.ml_compatibility?.message}
                </p>
              </div>

              {/* Mapped Channels List */}
              {Object.keys(uploadResult.mapped_channels || {}).length > 0 && (
                <div style={{ fontSize: '12px', marginTop: '10px' }}>
                  <strong>Channel Mapping Resolution:</strong>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                    {Object.entries(uploadResult.mapped_channels).map(([col, canonical]) => (
                      <span
                        key={col}
                        style={{
                          backgroundColor: '#f1f5f9',
                          border: '1px solid #cbd5e1',
                          padding: '3px 8px',
                          borderRadius: '4px',
                          fontFamily: 'monospace'
                        }}
                      >
                        {col} → {canonical}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Section 4: Existing Prognostic Models & Database Summary */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '20px' }}>
        {/* ML Models */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Sparkles size={18} color="var(--status-ai)" />
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Active Prognostic Models</h3>
          </div>
          <div style={{ fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>RUL Regressor:</div>
              <strong className="mono">LightGBM (RMSE 13.41 cycles, R² 0.888)</strong>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>Anomaly Detector:</div>
              <strong className="mono">Isolation Forest (200 trees, 5% contamination)</strong>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>GenAI Reasoning:</div>
              <strong className="mono">Google Gemini 3.6 Flash</strong>
            </div>
          </div>
        </div>

        {/* Database & Stream */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px' }}>
            <Database size={18} color="var(--status-normal)" />
            <h3 style={{ fontSize: '15px', fontWeight: 600 }}>Storage & Telemetry Pipeline</h3>
          </div>
          <div style={{ fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>Active Database:</div>
              <strong className="mono">PostgreSQL / Supabase (with SQLite Fallback)</strong>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>Replay Tick Rate:</div>
              <strong className="mono">1,000 ms per cycle</strong>
            </div>
            <div>
              <div style={{ color: 'var(--text-muted)' }}>WebSocket Protocol:</div>
              <strong className="mono">ws://localhost:8000/api/v1/stream</strong>
            </div>
          </div>
        </div>
      </div>
    </>
  )}

      {/* Section 5: Security Audit Trail Ledger */}
      {activeTab === 'security' && (
        userRole !== 'ADMIN' ? (
          <div className="card" style={{ marginTop: '24px', borderLeft: '4px solid #dc2626', background: '#fef2f2' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <ShieldCheck size={26} color="#dc2626" />
              <div>
                <div style={{ fontSize: '15px', fontWeight: 700, color: '#991b1b' }}>
                  🔒 Security Audit Trail — Access Restricted (Admin Role Required)
                </div>
                <div style={{ fontSize: '12px', color: '#7f1d1d', marginTop: '4px', fontWeight: 500 }}>
                  Your current active session role is <strong>{userRole}</strong>. RBAC Security Audit Logs are restricted to <strong>ADMIN</strong> users only. Switch your role to <strong>ADMIN</strong> in the top navigation dropdown to view security event logs.
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="card" style={{ marginTop: '24px', borderLeft: '4px solid #ef4444' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px', flexWrap: 'wrap', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldCheck size={20} color="#ef4444" />
                <div>
                  <h3 style={{ fontSize: '15px', fontWeight: 600, margin: 0 }}>RBAC Security Audit Trail (Stage 11)</h3>
                  <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Immutable log of authorization events, rate-limiting triggers, and mutation access attempts.
                  </span>
                </div>
              </div>
              <button
                className="btn btn-secondary btn-sm"
                onClick={fetchSecurityLogs}
                disabled={loadingLogs}
              >
                {loadingLogs ? 'Refreshing...' : 'Refresh Logs'}
              </button>
            </div>

            {securityLogs.length === 0 ? (
              <div className="empty-state" style={{ padding: '24px' }}>
                <ShieldCheck size={32} color="var(--text-muted)" style={{ marginBottom: '8px' }} />
                <div className="empty-title">No Security Events Recorded</div>
                <div className="empty-desc">Security events and access decisions will appear here in real-time.</div>
              </div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Timestamp</th>
                      <th>Actor</th>
                      <th>Role</th>
                      <th>Action</th>
                      <th>Endpoint</th>
                      <th>Status</th>
                      <th>Client IP</th>
                    </tr>
                  </thead>
                  <tbody>
                    {securityLogs.map((evt) => (
                      <tr key={evt.id}>
                        <td className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          {evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : 'Recent'}
                        </td>
                        <td style={{ fontWeight: 600 }}>{evt.actor}</td>
                        <td>
                          <span className={`badge ${evt.role === 'ADMIN' ? 'badge-critical' : (evt.role === 'OPERATOR' ? 'badge-ai' : 'badge-normal')}`}>
                            {evt.role}
                          </span>
                        </td>
                        <td className="mono" style={{ fontSize: '12px' }}>{evt.action_attempted}</td>
                        <td className="mono" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>{evt.endpoint}</td>
                        <td>
                          <span className={`badge ${evt.status === 'GRANTED' ? 'badge-normal' : (evt.status === 'RATE_LIMITED' ? 'badge-warning' : 'badge-critical')}`}>
                            {evt.status}
                          </span>
                        </td>
                        <td className="mono" style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{evt.client_ip || '127.0.0.1'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
}

