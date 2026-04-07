import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '@/stores/auth';
import { LayoutDashboard, Package, Factory, Truck, BarChart3, Users, FileText, ShieldCheck, LogOut, Menu, X, } from 'lucide-react';
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
export default function Layout() {
    const user = useAuth(s => s.user);
    const logout = useAuth(s => s.logout);
    const navigate = useNavigate();
    const [collapsed, setCollapsed] = useState(false);
    const handleLogout = () => { logout(); navigate('/login'); };
    return (_jsxs("div", { className: "flex h-screen", children: [_jsxs("aside", { className: `${collapsed ? 'w-16' : 'w-56'} bg-[hsl(222.2,84%,4.9%)] text-white flex flex-col transition-all duration-200`, children: [_jsxs("div", { className: "h-14 flex items-center justify-between px-4 border-b border-white/10", children: [!collapsed && _jsx("span", { className: "font-bold text-sm", children: "FenLu V5" }), _jsx("button", { onClick: () => setCollapsed(!collapsed), className: "p-1 hover:bg-white/10 rounded", children: collapsed ? _jsx(Menu, { size: 18 }) : _jsx(X, { size: 18 }) })] }), _jsx("nav", { className: "flex-1 py-2 space-y-0.5 overflow-y-auto", children: nav.map(item => (_jsxs(NavLink, { to: item.to, end: item.to === '/', className: ({ isActive }) => `flex items-center gap-3 px-4 py-2.5 text-sm transition ${isActive ? 'bg-[hsl(221.2,83.2%,53.3%)] text-white' : 'text-white/70 hover:bg-white/5 hover:text-white'}`, children: [_jsx(item.icon, { size: 18 }), !collapsed && _jsx("span", { children: item.label })] }, item.to))) }), _jsxs("div", { className: "border-t border-white/10 p-3", children: [!collapsed && _jsx("p", { className: "text-xs text-white/50 mb-2 truncate", children: user?.full_name }), _jsxs("button", { onClick: handleLogout, className: "flex items-center gap-2 text-sm text-white/60 hover:text-white transition", children: [_jsx(LogOut, { size: 16 }), !collapsed && '退出'] })] })] }), _jsx("main", { className: "flex-1 overflow-auto bg-[hsl(210,40%,98%)]", children: _jsx(Outlet, {}) })] }));
}
