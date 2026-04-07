import { NavLink, useNavigate } from 'react-router-dom';
import { type ReactNode } from 'react';
import { useAuth } from '@/stores/auth';
import {
  LayoutDashboard, Package, Factory, Truck, BarChart3,
  Users, FileText, ShieldCheck, LogOut, PanelLeftClose, PanelLeft,
} from 'lucide-react';
import { useState } from 'react';

const nav = [
  { to: '/', icon: LayoutDashboard, label: '驾驶舱' },
  { to: '/plm', icon: Package, label: '产品生命周期' },
  { to: '/mfg', icon: Factory, label: '生产制造' },
  { to: '/scm', icon: Truck, label: '供应链' },
  { to: '/mgmt/finance', icon: FileText, label: '财务管理' },
  { to: '/mgmt/hr', icon: Users, label: '人力资源' },
  { to: '/mgmt/kpi', icon: BarChart3, label: 'KPI 看板' },
  { to: '/mgmt/approval', icon: ShieldCheck, label: '审批中心' },
];

export default function Layout({ children }: { children?: ReactNode }) {
  const user = useAuth(s => s.user);
  const logout = useAuth(s => s.logout);
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => { logout(); navigate('/login'); };

  return (
    <div className="flex h-screen">
      {/* Sidebar — frosted glass */}
      <aside
        className={`${collapsed ? 'w-[68px]' : 'w-[220px]'} flex flex-col border-r shrink-0`}
        style={{
          background: 'var(--bg-sidebar)',
          backdropFilter: 'blur(20px) saturate(180%)',
          WebkitBackdropFilter: 'blur(20px) saturate(180%)',
          borderColor: 'var(--border)',
        }}
      >
        {/* Logo */}
        <div className="h-14 flex items-center justify-between px-4" style={{ borderBottom: '1px solid var(--divider)' }}>
          {!collapsed && <span className="text-[13px] font-semibold tracking-tight" style={{ color: 'var(--fg)' }}>FenLu V5</span>}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 rounded-lg"
            style={{ color: 'var(--fg-secondary)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          >
            {collapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
          </button>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-2 px-2 overflow-y-auto space-y-0.5">
          {nav.map(item => (
            <NavLink
              key={item.to} to={item.to} end={item.to === '/'}
              className="flex items-center gap-2.5 rounded-lg text-[13px] no-underline"
              style={({ isActive }) => ({
                padding: collapsed ? '8px' : '8px 10px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                color: isActive ? 'var(--accent)' : 'var(--fg-secondary)',
                background: isActive ? 'var(--accent-light)' : 'transparent',
                fontWeight: isActive ? 600 : 400,
              })}
              onMouseEnter={e => {
                if (!e.currentTarget.style.background?.includes('accent')) {
                  e.currentTarget.style.background = 'var(--bg-hover)';
                }
              }}
              onMouseLeave={e => {
                const isActive = e.currentTarget.getAttribute('aria-current');
                if (!isActive) e.currentTarget.style.background = 'transparent';
              }}
            >
              <item.icon size={18} strokeWidth={1.5} />
              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="px-3 py-3" style={{ borderTop: '1px solid var(--divider)' }}>
          {!collapsed && (
            <p className="text-[11px] mb-2 truncate px-1" style={{ color: 'var(--fg-tertiary)' }}>
              {user?.full_name}
            </p>
          )}
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 text-[13px] px-1 rounded-lg w-full"
            style={{ color: 'var(--fg-tertiary)' }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--status-red-fg)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--fg-tertiary)'; }}
          >
            <LogOut size={15} strokeWidth={1.5} />
            {!collapsed && '退出登录'}
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto" style={{ background: 'var(--bg)' }}>
        {children}
      </main>
    </div>
  );
}
