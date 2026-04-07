import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect } from 'react';
import { useAuth } from '@/stores/auth';
import Layout from '@/components/Layout';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import PlmPage from '@/pages/PlmPage';
import MfgPage from '@/pages/MfgPage';
import ScmPage from '@/pages/ScmPage';
import MgmtPage from '@/pages/MgmtPage';
const queryClient = new QueryClient({
    defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});
function AuthGuard({ children }) {
    const user = useAuth(s => s.user);
    const loading = useAuth(s => s.loading);
    const loadUser = useAuth(s => s.loadUser);
    useEffect(() => { loadUser(); }, [loadUser]);
    if (loading)
        return (_jsx("div", { className: "min-h-screen flex items-center justify-center", children: _jsx("div", { className: "text-[hsl(215.4,16.3%,46.9%)]", children: "Loading..." }) }));
    if (!user)
        return _jsx(Navigate, { to: "/login", replace: true });
    return _jsx(_Fragment, { children: children });
}
export function App() {
    return (_jsx(QueryClientProvider, { client: queryClient, children: _jsx(BrowserRouter, { children: _jsxs(Routes, { children: [_jsx(Route, { path: "/login", element: _jsx(Login, {}) }), _jsxs(Route, { element: _jsx(AuthGuard, { children: _jsx(Layout, {}) }), children: [_jsx(Route, { index: true, element: _jsx(Dashboard, {}) }), _jsx(Route, { path: "plm", element: _jsx(PlmPage, {}) }), _jsx(Route, { path: "mfg", element: _jsx(MfgPage, {}) }), _jsx(Route, { path: "scm", element: _jsx(ScmPage, {}) }), _jsx(Route, { path: "mgmt/finance", element: _jsx(MgmtPage, {}) }), _jsx(Route, { path: "mgmt/hr", element: _jsx(MgmtPage, {}) }), _jsx(Route, { path: "mgmt/kpi", element: _jsx(MgmtPage, {}) }), _jsx(Route, { path: "mgmt/approval", element: _jsx(MgmtPage, {}) })] })] }) }) }));
}
