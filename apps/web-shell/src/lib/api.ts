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
    throw new Error(body.detail || `HTTP ${res.status}`);
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

export const plmApi = {
  listProducts: (skip = 0, limit = 20) => api.get<Product[]>(`/plm/products?skip=${skip}&limit=${limit}`),
  getProduct: (id: string) => api.get<Product>(`/plm/products/${id}`),
  createProduct: (data: Partial<Product>) => api.post<Product>('/plm/products', data),
  createVersion: (productId: string, data: { description?: string }) =>
    api.post<ProductVersion>(`/plm/products/${productId}/versions`, data),
  getBom: (id: string) => api.get<BOM>(`/plm/bom/${id}`),
  createBom: (data: { product_id: string; version?: number }) => api.post<BOM>('/plm/bom', data),
};

// --- MFG ---
export interface WorkOrder {
  id: string; order_number: string; product_id: string; product_name?: string;
  planned_quantity: number; completed_quantity: number; status: string;
  planned_start: string; planned_end: string; created_at: string;
}

export const mfgApi = {
  listWorkOrders: () => api.get<WorkOrder[]>('/mfg/work-orders'),
  getWorkOrder: (id: string) => api.get<WorkOrder>(`/mfg/work-orders/${id}`),
  createWorkOrder: (data: Partial<WorkOrder>) => api.post<WorkOrder>('/mfg/work-orders', data),
  transitionStatus: (id: string, status: string) =>
    api.patch<WorkOrder>(`/mfg/work-orders/${id}/status`, { status }),
};

// --- SCM ---
export interface Supplier {
  id: string; code: string; name: string; tier: string; contact_name: string;
  contact_phone: string; contact_email: string; is_active: boolean; created_at: string;
}
export interface SupplierRating { id: string; score: number; period: string; evaluator: string; comment: string; }

export const scmApi = {
  listSuppliers: (params?: { tier?: string; search?: string; skip?: number; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.tier) q.set('tier', params.tier);
    if (params?.search) q.set('search', params.search);
    q.set('skip', String(params?.skip ?? 0));
    q.set('limit', String(params?.limit ?? 20));
    return api.get<Supplier[]>(`/scm/suppliers?${q}`);
  },
  getSupplier: (id: string) => api.get<Supplier>(`/scm/suppliers/${id}`),
  createSupplier: (data: Partial<Supplier>) => api.post<Supplier>('/scm/suppliers', data),
  listRatings: (supplierId: string) => api.get<SupplierRating[]>(`/scm/suppliers/${supplierId}/ratings`),
};

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
};
