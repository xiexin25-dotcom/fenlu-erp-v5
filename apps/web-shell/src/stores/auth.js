import { create } from 'zustand';
import { authApi } from '@/lib/api';
export const useAuth = create((set) => ({
    user: null,
    loading: true,
    login: async (tenant_code, username, password) => {
        const res = await authApi.login({ tenant_code, username, password });
        localStorage.setItem('token', res.access_token);
        const user = await authApi.me();
        set({ user });
    },
    logout: () => {
        localStorage.removeItem('token');
        set({ user: null });
    },
    loadUser: async () => {
        const token = localStorage.getItem('token');
        if (!token) {
            set({ loading: false });
            return;
        }
        try {
            const user = await authApi.me();
            set({ user, loading: false });
        }
        catch {
            localStorage.removeItem('token');
            set({ user: null, loading: false });
        }
    },
}));
