import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, type ReactNode } from 'react';
import { useAuth } from '@/stores/auth';
import Layout from '@/components/Layout';
import Login from '@/pages/Login';
import Dashboard from '@/pages/Dashboard';
// PLM
import PlmPage from '@/pages/PlmPage';
import ProductList from '@/pages/plm/ProductList';
import ProductDetail from '@/pages/plm/ProductDetail';
import CustomerList from '@/pages/plm/CustomerList';
import ServiceTicketList from '@/pages/plm/ServiceTicketList';
// MFG
import MfgPage from '@/pages/MfgPage';
import WorkOrderList from '@/pages/mfg/WorkOrderList';
import QCInspectionList from '@/pages/mfg/QCInspectionList';
import EquipmentList from '@/pages/mfg/EquipmentList';
import SafetyHazardList from '@/pages/mfg/SafetyHazardList';
// SCM
import ScmPage from '@/pages/ScmPage';
import SupplierList from '@/pages/scm/SupplierList';
import WarehouseList from '@/pages/scm/WarehouseList';
import InventoryList from '@/pages/scm/InventoryList';
import StocktakeList from '@/pages/scm/StocktakeList';
// MGMT
import MgmtPage from '@/pages/MgmtPage';
import GLAccountList from '@/pages/mgmt/GLAccountList';
import JournalList from '@/pages/mgmt/JournalList';
import APARList from '@/pages/mgmt/APARList';
import EmployeeList from '@/pages/mgmt/EmployeeList';
import ApprovalList from '@/pages/mgmt/ApprovalList';

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
              <Route path="plm/customers" element={<CustomerList />} />
              <Route path="plm/service-tickets" element={<ServiceTicketList />} />
              {/* MFG */}
              <Route path="mfg" element={<MfgPage />} />
              <Route path="mfg/work-orders" element={<WorkOrderList />} />
              <Route path="mfg/qc" element={<QCInspectionList />} />
              <Route path="mfg/equipment" element={<EquipmentList />} />
              <Route path="mfg/safety" element={<SafetyHazardList />} />
              {/* SCM */}
              <Route path="scm" element={<ScmPage />} />
              <Route path="scm/suppliers" element={<SupplierList />} />
              <Route path="scm/warehouses" element={<WarehouseList />} />
              <Route path="scm/inventory" element={<InventoryList />} />
              <Route path="scm/stocktakes" element={<StocktakeList />} />
              {/* MGMT */}
              <Route path="mgmt/finance" element={<MgmtPage />} />
              <Route path="mgmt/finance/accounts" element={<GLAccountList />} />
              <Route path="mgmt/finance/journal" element={<JournalList />} />
              <Route path="mgmt/finance/apar" element={<APARList />} />
              <Route path="mgmt/hr" element={<MgmtPage />} />
              <Route path="mgmt/hr/employees" element={<EmployeeList />} />
              <Route path="mgmt/kpi" element={<MgmtPage />} />
              <Route path="mgmt/approval" element={<MgmtPage />} />
              <Route path="mgmt/approval/list" element={<ApprovalList />} />
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
