const BASE = '/api';

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const headers: Record<string, string> = { 'Content-Type': 'application/json', ...((opts?.headers as Record<string, string>) || {}) };
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

export interface LoginPayload { tenant_code: string; username: string; password: string; }
export interface TokenResponse { access_token: string; refresh_token: string; token_type: string; }
export interface User { id: string; username: string; full_name: string; tenant_id: string; is_superuser: boolean; }

export const authApi = {
  login: (data: LoginPayload) => api.post<TokenResponse>('/auth/login', data),
  me: () => api.get<User>('/auth/me'),
};

export interface DashboardData {
  today_revenue: number;
  weekly_output: number;
  weekly_oee: number;
  open_safety_hazards: number;
  energy_unit_consumption: number;
  cash_position: number;
  revenue_trend: { date: string; amount: number }[];
  oee_trend: { date: string; oee: number }[];
}

export const dashboardApi = {
  exec: () => api.get<DashboardData>('/mgmt/bi/dashboards/exec'),
};

export interface KPI { code: string; name: string; unit: string; current_value: number; target_value: number; }
export const kpiApi = {
  list: () => api.get<KPI[]>('/mgmt/bi/kpis'),
};
