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

function AuthGuard({ children }: { children: React.ReactNode }) {
  const user = useAuth(s => s.user);
  const loading = useAuth(s => s.loading);
  const loadUser = useAuth(s => s.loadUser);

  useEffect(() => { loadUser(); }, [loadUser]);

  if (loading) return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-[hsl(215.4,16.3%,46.9%)]">Loading...</div>
    </div>
  );
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<AuthGuard><Layout /></AuthGuard>}>
            <Route index element={<Dashboard />} />
            <Route path="plm" element={<PlmPage />} />
            <Route path="mfg" element={<MfgPage />} />
            <Route path="scm" element={<ScmPage />} />
            <Route path="mgmt/finance" element={<MgmtPage />} />
            <Route path="mgmt/hr" element={<MgmtPage />} />
            <Route path="mgmt/kpi" element={<MgmtPage />} />
            <Route path="mgmt/approval" element={<MgmtPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
