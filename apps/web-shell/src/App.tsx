import { BrowserRouter, Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect } from 'react';
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
import ECNList from '@/pages/plm/ECNList';
import CRMFunnel from '@/pages/plm/CRMFunnel';
// MFG
import MfgPage from '@/pages/MfgPage';
import WorkOrderList from '@/pages/mfg/WorkOrderList';
import QCInspectionList from '@/pages/mfg/QCInspectionList';
import EquipmentList from '@/pages/mfg/EquipmentList';
import SafetyHazardList from '@/pages/mfg/SafetyHazardList';
import JobTicketList from '@/pages/mfg/JobTicketList';
import EnergyPage from '@/pages/mfg/EnergyPage';
import APSPage from '@/pages/mfg/APSPage';
// SCM
import ScmPage from '@/pages/ScmPage';
import SupplierList from '@/pages/scm/SupplierList';
import WarehouseList from '@/pages/scm/WarehouseList';
import InventoryList from '@/pages/scm/InventoryList';
import StocktakeList from '@/pages/scm/StocktakeList';
import PurchaseOrderList from '@/pages/scm/PurchaseOrderList';
// MGMT
import MgmtPage from '@/pages/MgmtPage';
import GLAccountList from '@/pages/mgmt/GLAccountList';
import JournalList from '@/pages/mgmt/JournalList';
import APARList from '@/pages/mgmt/APARList';
import EmployeeList from '@/pages/mgmt/EmployeeList';
import AttendanceList from '@/pages/mgmt/AttendanceList';
import PayrollList from '@/pages/mgmt/PayrollList';
import ApprovalList from '@/pages/mgmt/ApprovalList';
import KPIPage from '@/pages/mgmt/KPIPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
});

function AuthGuard() {
  const user = useAuth(s => s.user);
  const loading = useAuth(s => s.loading);
  const loadUser = useAuth(s => s.loadUser);
  const location = useLocation();
  useEffect(() => { loadUser(); }, [loadUser]);
  if (loading) return <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}><p>Loading...</p></div>;
  if (!user) return <Navigate to="/login" state={{ from: location }} replace />;
  return <Outlet />;
}

function ShellLayout() {
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<AuthGuard />}>
            <Route element={<ShellLayout />}>
              <Route index element={<Dashboard />} />
              {/* PLM */}
              <Route path="plm" element={<PlmPage />} />
              <Route path="plm/products" element={<ProductList />} />
              <Route path="plm/products/:id" element={<ProductDetail />} />
              <Route path="plm/ecn" element={<ECNList />} />
              <Route path="plm/customers" element={<CustomerList />} />
              <Route path="plm/crm-funnel" element={<CRMFunnel />} />
              <Route path="plm/service-tickets" element={<ServiceTicketList />} />
              {/* MFG */}
              <Route path="mfg" element={<MfgPage />} />
              <Route path="mfg/work-orders" element={<WorkOrderList />} />
              <Route path="mfg/job-tickets" element={<JobTicketList />} />
              <Route path="mfg/qc" element={<QCInspectionList />} />
              <Route path="mfg/equipment" element={<EquipmentList />} />
              <Route path="mfg/safety" element={<SafetyHazardList />} />
              <Route path="mfg/energy" element={<EnergyPage />} />
              <Route path="mfg/aps" element={<APSPage />} />
              {/* SCM */}
              <Route path="scm" element={<ScmPage />} />
              <Route path="scm/suppliers" element={<SupplierList />} />
              <Route path="scm/purchase-orders" element={<PurchaseOrderList />} />
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
              <Route path="mgmt/hr/attendance" element={<AttendanceList />} />
              <Route path="mgmt/hr/payroll" element={<PayrollList />} />
              <Route path="mgmt/kpi" element={<KPIPage />} />
              <Route path="mgmt/approval" element={<MgmtPage />} />
              <Route path="mgmt/approval/list" element={<ApprovalList />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
