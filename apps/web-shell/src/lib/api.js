const BASE = '/api';
async function request(path, opts) {
    const token = localStorage.getItem('token');
    const headers = { 'Content-Type': 'application/json', ...(opts?.headers || {}) };
    if (token)
        headers['Authorization'] = `Bearer ${token}`;
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
    get: (path) => request(path),
    post: (path, body) => request(path, { method: 'POST', body: JSON.stringify(body) }),
    patch: (path, body) => request(path, { method: 'PATCH', body: JSON.stringify(body) }),
};
export const authApi = {
    login: (data) => api.post('/auth/login', data),
    me: () => api.get('/auth/me'),
};
export const dashboardApi = {
    exec: () => api.get('/mgmt/bi/dashboards/exec'),
};
export const kpiApi = {
    list: () => api.get('/mgmt/bi/kpis'),
};
