const BASE = '/api';

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = { ...((opts?.headers as Record<string, string>) || {}) };
  if (!opts?.body || typeof opts.body === 'string') headers['Content-Type'] = 'application/json';
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const res = await fetch(`${BASE}${path}`, { ...opts, headers });
  if (res.status === 401) {
    localStorage.removeItem('token');
    window.location.href = '/login';
    throw new Error('Unauthorized');
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    let msg = `HTTP ${res.status}`;
    if (body.detail) {
      if (typeof body.detail === 'string') msg = body.detail;
      else if (Array.isArray(body.detail)) msg = body.detail.map((e: { msg?: string; loc?: string[] }) => e.msg || JSON.stringify(e)).join('; ');
      else msg = JSON.stringify(body.detail);
    }
    throw new Error(msg);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
};

// --- Auth ---
export interface LoginPayload { tenant_code: string; username: string; password: string; }
export interface TokenResponse { access_token: string; refresh_token: string; token_type: string; }
export interface User { id: string; username: string; full_name: string; tenant_id: string; is_superuser: boolean; }

export const authApi = {
  login: (data: LoginPayload) => api.post<TokenResponse>('/auth/login', data),
  me: () => api.get<User>('/auth/me'),
};

// --- Dashboard ---
export interface DashboardData {
  today_revenue: number; weekly_output: number; weekly_oee: number;
  open_safety_hazards: number; energy_unit_consumption: number; cash_position: number;
  revenue_trend: { date: string; amount: number }[];
  oee_trend: { date: string; oee: number }[];
}
export interface KPI { code: string; name: string; unit: string; current_value: number; target_value: number; }

export const dashboardApi = { exec: () => api.get<DashboardData>('/mgmt/bi/dashboards/exec') };
export const kpiApi = { list: () => api.get<KPI[]>('/mgmt/bi/kpis') };

// --- PLM ---
export interface Product {
  id: string; code: string; name: string; category: string; unit: string;
  status: string; current_version: number; created_at: string;
}
export interface ProductVersion { id: string; version: number; description: string; created_at: string; }
export interface BOM { id: string; product_id: string; version: number; items: BOMItem[]; total_cost: number | null; }
export interface BOMItem { id: string; component_id: string; component_name?: string; quantity: number; unit_cost: number | null; }

export interface ECN {
  id: string; ecn_number: string; title: string; status: string;
  affected_product_id: string; description: string; created_at: string;
}
export interface Customer {
  id: string; code: string; name: string; kind: string; rating: string; industry: string;
  contact_name: string; contact_phone: string; is_online: boolean; created_at: string;
}
export interface ServiceTicket {
  id: string; ticket_number: string; customer_id: string; customer_name?: string;
  subject: string; status: string; priority: string; sla_hours: number;
  nps_score: number | null; created_at: string;
}

export const plmApi = {
  listProducts: async (skip = 0, limit = 20) => {
    const r = await api.get<{ items: Product[]; total: number } | Product[]>(`/plm/products?skip=${skip}&limit=${limit}`);
    if (Array.isArray(r)) return { items: r, total: r.length };
    return r as { items: Product[]; total: number };
  },
  getProduct: (id: string) => api.get<Product>(`/plm/products/${id}`),
  createProduct: (data: Partial<Product>) => api.post<Product>('/plm/products', data),
  createVersion: (productId: string, data: { description?: string }) =>
    api.post<ProductVersion>(`/plm/products/${productId}/versions`, data),
  getBom: (id: string) => api.get<BOM>(`/plm/bom/${id}`),
  createBom: (data: { product_id: string; version?: number }) => api.post<BOM>('/plm/bom', data),
  // ECN
  getEcn: (id: string) => api.get<ECN>(`/plm/ecn/${id}`),
  createEcn: (data: Partial<ECN>) => api.post<ECN>('/plm/ecn', data),
  transitionEcn: (id: string, action: string) => api.post<ECN>(`/plm/ecn/${id}/transition`, { action }),
  // Customers
  listCustomers: () => api.get<Customer[]>('/plm/customers'),
  getCustomer: (id: string) => api.get<Customer>(`/plm/customers/${id}`),
  createCustomer: (data: Partial<Customer>) => api.post<Customer>('/plm/customers', data),
  getCustomer360: (id: string) => api.get<Record<string, unknown>>(`/plm/customers/${id}/360`),
  // Service
  listTickets: () => api.get<ServiceTicket[]>('/plm/service/tickets'),
  createTicket: (data: Partial<ServiceTicket>) => api.post<ServiceTicket>('/plm/service/tickets', data),
  transitionTicket: (id: string, action: string) => api.post<ServiceTicket>(`/plm/service/tickets/${id}/transition`, { action }),
  closeTicket: (id: string, nps: number) => api.post<ServiceTicket>(`/plm/service/tickets/${id}/close`, { nps_score: nps }),
};

// --- MFG ---
export interface WorkOrder {
  id: string; order_number: string; product_id: string; product_name?: string;
  planned_quantity: number; completed_quantity: number; status: string;
  planned_start: string; planned_end: string; created_at: string;
}

export interface QCInspection {
  id: string; work_order_id: string; product_id: string; inspector: string;
  result: string; defect_count: number; sample_size: number; notes: string; created_at: string;
}
export interface Equipment {
  id: string; code: string; name: string; equipment_type: string; location: string;
  status: string; last_maintenance: string | null; created_at: string;
}
export interface SafetyHazard {
  id: string; title: string; description: string; severity: string;
  status: string; location: string; reporter: string; created_at: string;
}
export interface EnergyReading {
  id: string; meter_id: string; value: number; unit: string; timestamp: string;
}

export const mfgApi = {
  listWorkOrders: () => api.get<WorkOrder[]>('/mfg/work-orders'),
  getWorkOrder: (id: string) => api.get<WorkOrder>(`/mfg/work-orders/${id}`),
  createWorkOrder: (data: Partial<WorkOrder>) => api.post<WorkOrder>('/mfg/work-orders', data),
  transitionStatus: (id: string, status: string) =>
    api.patch<WorkOrder>(`/mfg/work-orders/${id}/status`, { status }),
  // QC
  listInspections: (params?: { work_order_id?: string }) => {
    const q = params?.work_order_id ? `?work_order_id=${params.work_order_id}` : '';
    return api.get<QCInspection[]>(`/mfg/qc/inspections${q}`);
  },
  createInspection: (data: Partial<QCInspection>) => api.post<QCInspection>('/mfg/qc/inspections', data),
  // Equipment
  listEquipment: () => api.get<Equipment[]>('/mfg/equipment'),
  createEquipment: (data: Partial<Equipment>) => api.post<Equipment>('/mfg/equipment', data),
  // Safety
  listHazards: (status?: string) => {
    const q = status ? `?status=${status}` : '';
    return api.get<SafetyHazard[]>(`/mfg/safety/hazards${q}`);
  },
  createHazard: (data: Partial<SafetyHazard>) => api.post<SafetyHazard>('/mfg/safety/hazards', data),
  transitionHazard: (id: string, action: string) =>
    api.patch<SafetyHazard>(`/mfg/safety/hazards/${id}/transition`, { action }),
};

// --- SCM ---
export interface Supplier {
  id: string; code: string; name: string; tier: string; contact_name: string;
  contact_phone: string; contact_email: string; is_active: boolean; created_at: string;
}
export interface SupplierRating { id: string; score: number; period: string; evaluator: string; comment: string; }

function tenantId() { return localStorage.getItem('tenant_id') || ''; }

export const scmApi = {
  listSuppliers: (params?: { tier?: string; search?: string; skip?: number; limit?: number }) => {
    const q = new URLSearchParams();
    q.set('tenant_id', tenantId());
    if (params?.tier) q.set('tier', params.tier);
    if (params?.search) q.set('search', params.search);
    q.set('skip', String(params?.skip ?? 0));
    q.set('limit', String(params?.limit ?? 20));
    return api.get<Supplier[]>(`/scm/suppliers?${q}`);
  },
  getSupplier: (id: string) => api.get<Supplier>(`/scm/suppliers/${id}`),
  createSupplier: (data: Partial<Supplier>) => api.post<Supplier>(`/scm/suppliers?tenant_id=${tenantId()}`, data),
  listRatings: (supplierId: string) => api.get<SupplierRating[]>(`/scm/suppliers/${supplierId}/ratings?tenant_id=${tenantId()}`),
  // Purchase Orders
  listPOs: () => api.get<PurchaseOrder[]>(`/scm/purchase-orders?tenant_id=${tenantId()}`),
  // Warehouses
  listWarehouses: () => api.get<Warehouse[]>(`/scm/warehouses?tenant_id=${tenantId()}&skip=0&limit=50`),
  createWarehouse: (data: Partial<Warehouse>) => api.post<Warehouse>(`/scm/warehouses?tenant_id=${tenantId()}`, data),
  // Inventory
  listInventory: (params?: { product_id?: string; warehouse_id?: string }) => {
    const q = new URLSearchParams();
    q.set('tenant_id', tenantId());
    if (params?.product_id) q.set('product_id', params.product_id);
    if (params?.warehouse_id) q.set('warehouse_id', params.warehouse_id);
    return api.get<InventoryItem[]>(`/scm/inventory?${q}`);
  },
  // Stocktake
  listStocktakes: () => api.get<Stocktake[]>(`/scm/stocktakes?tenant_id=${tenantId()}`),
  createStocktake: (data: Partial<Stocktake>) => api.post<Stocktake>(`/scm/stocktakes?tenant_id=${tenantId()}`, data),
};

export interface PurchaseOrder {
  id: string; po_number: string; supplier_id: string; supplier_name?: string;
  status: string; total_amount: number; created_at: string;
}
export interface Warehouse {
  id: string; code: string; name: string; address: string; is_active: boolean;
}
export interface InventoryItem {
  id: string; product_id: string; product_name?: string; warehouse_id: string;
  warehouse_name?: string; quantity: number; batch_no: string;
}
export interface Stocktake {
  id: string; stocktake_number: string; warehouse_id: string; warehouse_name?: string;
  status: string; created_at: string;
}

// --- MGMT Finance ---
export interface GLAccount {
  id: string; code: string; name: string; account_type: string; level: number;
  parent_id: string | null; is_active: boolean;
}
export interface JournalEntry {
  id: string; entry_number: string; date: string; description: string;
  status: string; total_debit: number; total_credit: number; created_at: string;
  lines: JournalLine[];
}
export interface JournalLine {
  id: string; account_id: string; account_code?: string; account_name?: string;
  debit_amount: number; credit_amount: number; description: string;
}

export const mgmtApi = {
  listAccounts: () => api.get<GLAccount[]>('/mgmt/finance/accounts'),
  createAccount: (data: Partial<GLAccount>) => api.post<GLAccount>('/mgmt/finance/accounts', data),
  listJournals: () => api.get<JournalEntry[]>('/mgmt/finance/journal'),
  getJournal: (id: string) => api.get<JournalEntry>(`/mgmt/finance/journal/${id}`),
  createJournal: (data: { date: string; description: string; lines: Partial<JournalLine>[] }) =>
    api.post<JournalEntry>('/mgmt/finance/journal', data),
  postJournal: (id: string) => api.post<JournalEntry>(`/mgmt/finance/journal/${id}/post`),
  // AP/AR
  listAP: (status?: string) => api.get<APRecord[]>(`/mgmt/finance/ap${status ? `?status=${status}` : ''}`),
  listAR: (status?: string) => api.get<ARRecord[]>(`/mgmt/finance/ar${status ? `?status=${status}` : ''}`),
  // HR
  listEmployees: () => api.get<Employee[]>('/mgmt/hr/employees'),
  createEmployee: (data: Partial<Employee>) => api.post<Employee>('/mgmt/hr/employees', data),
  listAttendance: (params?: { employee_id?: string }) => {
    const q = params?.employee_id ? `?employee_id=${params.employee_id}` : '';
    return api.get<Attendance[]>(`/mgmt/hr/attendance${q}`);
  },
  // Approval
  listApprovals: (status?: string) => api.get<ApprovalInstance[]>(`/mgmt/approval${status ? `?status=${status}` : ''}`),
  listPendingApprovals: () => api.get<ApprovalInstance[]>('/mgmt/approval/pending'),
};

export interface APRecord {
  id: string; supplier_name: string; amount: number; status: string;
  due_date: string; paid_amount: number; created_at: string;
}
export interface ARRecord {
  id: string; customer_name: string; amount: number; status: string;
  due_date: string; received_amount: number; created_at: string;
}
export interface Employee {
  id: string; employee_no: string; name: string; department: string;
  position: string; is_active: boolean; hire_date: string;
}
export interface Attendance {
  id: string; employee_id: string; employee_name?: string;
  date: string; check_in: string; check_out: string; status: string; overtime_hours: number;
}
export interface ApprovalInstance {
  id: string; business_type: string; business_id: string;
  status: string; current_step: number; total_steps: number;
  submitted_by: string; created_at: string;
}
