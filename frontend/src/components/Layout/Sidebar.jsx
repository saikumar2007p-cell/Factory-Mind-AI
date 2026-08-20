import React from 'react';
import {
  LayoutDashboard,
  Cpu,
  AlertTriangle,
  BrainCircuit,
  Wrench,
  Activity,
  FileText,
  Settings,
  ShieldCheck,
  Layers,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  LogOut
} from 'lucide-react';

export default function Sidebar({ 
  activeTab, 
  onSelectTab, 
  fleetSummary,
  isCollapsed = false,
  onToggleCollapse,
  onLogout,
  userRole = 'ADMIN'
}) {
  const allNavItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'fleet', label: 'Fleet Intelligence', icon: Layers },
    { id: 'learning', label: 'Learning Intelligence', icon: TrendingUp },
    { id: 'machines', label: 'Machines', icon: Cpu, badge: fleetSummary?.total_machines || 100 },
    { id: 'alerts', label: 'Alerts', icon: AlertTriangle, badge: fleetSummary?.warning_count || 0, badgeType: 'warning' },
    { id: 'insights', label: 'AI Insights', icon: BrainCircuit },
    { id: 'maintenance', label: 'Maintenance', icon: Wrench },
    { id: 'production', label: 'Production', icon: Activity },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings, adminOnly: true },
  ];

  const navItems = allNavItems.filter(item => !item.adminOnly || userRole === 'ADMIN');

  return (
    <aside className={`app-sidebar ${isCollapsed ? 'collapsed' : ''}`}>
      {/* Brand Header with Collapse Toggle */}
      <div className="sidebar-brand">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div className="brand-icon-box" title="FactoryMind AI">
            <ShieldCheck size={20} />
          </div>
          {!isCollapsed && (
            <div>
              <div className="brand-title">FactoryMind AI</div>
              <div className="brand-subtitle">Turbofan Fleet Prognostics</div>
            </div>
          )}
        </div>

        <button
          className="sidebar-toggle-btn"
          onClick={onToggleCollapse}
          title={isCollapsed ? 'Expand Navigation Sidebar' : 'Collapse Navigation Sidebar'}
        >
          {isCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
        </button>
      </div>

      {/* Navigation List */}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={() => onSelectTab(item.id)}
              title={isCollapsed ? item.label : undefined}
            >
              <Icon size={18} />
              {!isCollapsed && (
                <>
                  <span className="nav-label" style={{ flex: 1 }}>{item.label}</span>
                  {item.badge !== undefined && item.badge > 0 && (
                    <span
                      style={{
                        fontSize: '11px',
                        padding: '2px 6px',
                        borderRadius: '9999px',
                        background: item.badgeType === 'warning' ? '#d97706' : 'rgba(255,255,255,0.15)',
                        color: '#ffffff',
                        fontWeight: '600'
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      {!isCollapsed && (
        <div className="sidebar-footer">
          <div className="fleet-health-indicator">
            {(() => {
              const total = fleetSummary?.total_machines || 100;
              const healthy = fleetSummary?.healthy_count ?? (total - (fleetSummary?.warning_count || 0) - (fleetSummary?.critical_count || 0));
              const pct = Math.max(0, Math.min(100, Math.round((healthy / total) * 100)));
              return (
                <>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                    <span style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', fontWeight: 600 }}>
                      Fleet Health
                    </span>
                    <span style={{ fontSize: '12px', color: '#ffffff', fontWeight: 700 }}>
                      {pct}%
                    </span>
                  </div>
                  <div className="progress-bar-bg" style={{ height: '4px', background: 'rgba(255,255,255,0.1)' }}>
                    <div
                      className={`progress-bar-fill ${pct >= 80 ? 'fill-normal' : (pct >= 50 ? 'fill-warning' : 'fill-critical')}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                  <div style={{ fontSize: '11px', color: '#64748b', marginTop: '6px' }}>
                    NASA C-MAPSS FD001 Active
                  </div>
                </>
              );
            })()}
          </div>

          {onLogout && (
            <button
              onClick={onLogout}
              style={{
                width: '100%',
                marginTop: '10px',
                padding: '8px 12px',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.25)',
                borderRadius: '8px',
                color: '#f87171',
                fontSize: '12px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                transition: 'all 0.15s ease'
              }}
              title="Sign Out of FactoryMind AI"
            >
              <LogOut size={14} />
              <span>Sign Out</span>
            </button>
          )}
        </div>
      )}
    </aside>
  );
}
