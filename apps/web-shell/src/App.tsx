import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '@/stores/auth';
import Layout from '@/components/Layout';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
import PlmPage from '@/pages/PlmPage';
import ProductList from '@/pages/plm/ProductList';
import ProductDetail from '@/pages/plm/ProductDetail';
import MfgPage from '@/pages/MfgPage';
import WorkOrderList from '@/pages/mfg/WorkOrderList';
import ScmPage from '@/pages/ScmPage';
import SupplierList from '@/pages/scm/SupplierList';
import MgmtPage from '@/pages/MgmtPage';
import GLAccountList from '@/pages/mgmt/GLAccountList';
import JournalList from '@/pages/mgmt/JournalList';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

function AuthGuard({ children }: { children: ReactNode }) {
  const user = useAuth(s => s.user);
  const loading = useAuth(s => s.loading);
  const loadUser = useAuth(s => s.loadUser);
  const location = useLocation();

  useEffect(() => { loadUser(); }, [loadUser]);

  if (loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <p>Loading...</p>
    </div>
  );
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/*" element={
        <AuthGuard>
          <Layout>
            <Routes>
              <Route index element={<Dashboard />} />
              {/* PLM */}
              <Route path="plm" element={<PlmPage />} />
              <Route path="plm/products" element={<ProductList />} />
              <Route path="plm/products/:id" element={<ProductDetail />} />
              {/* MFG */}
              <Route path="mfg" element={<MfgPage />} />
              <Route path="mfg/work-orders" element={<WorkOrderList />} />
              {/* SCM */}
              <Route path="scm" element={<ScmPage />} />
              <Route path="scm/suppliers" element={<SupplierList />} />
              {/* MGMT */}
              <Route path="mgmt/finance" element={<MgmtPage />} />
              <Route path="mgmt/finance/accounts" element={<GLAccountList />} />
              <Route path="mgmt/finance/journal" element={<JournalList />} />
              <Route path="mgmt/hr" element={<MgmtPage />} />
              <Route path="mgmt/kpi" element={<MgmtPage />} />
              <Route path="mgmt/approval" element={<MgmtPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Layout>
        </AuthGuard>
      } />
    </Routes>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
