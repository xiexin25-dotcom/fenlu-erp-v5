import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/stores/auth';
export default function Login() {
    const navigate = useNavigate();
    const login = useAuth(s => s.login);
    const [tenant, setTenant] = useState('demo');
    const [username, setUsername] = useState('admin');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setLoading(true);
        try {
            await login(tenant, username, password);
            navigate('/');
        }
        catch (err) {
            setError(err instanceof Error ? err.message : 'Login failed');
        }
        finally {
            setLoading(false);
        }
    };
    return (_jsx("div", { className: "min-h-screen flex items-center justify-center bg-[hsl(210,40%,96.1%)]", children: _jsxs("div", { className: "w-full max-w-md bg-white rounded-xl shadow-lg p-8", children: [_jsxs("div", { className: "text-center mb-8", children: [_jsx("h1", { className: "text-2xl font-bold text-[hsl(222.2,84%,4.9%)]", children: "\u5206\u8DEF\u94FE\u5F0F\u5DE5\u4E1A\u4E92\u8054\u7F51" }), _jsx("p", { className: "text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1", children: "V5.0 \u7BA1\u7406\u7CFB\u7EDF" })] }), _jsxs("form", { onSubmit: handleSubmit, className: "space-y-4", children: [_jsxs("div", { children: [_jsx("label", { className: "block text-sm font-medium mb-1", children: "\u79DF\u6237\u7F16\u7801" }), _jsx("input", { type: "text", value: tenant, onChange: e => setTenant(e.target.value), className: "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)]", required: true })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-sm font-medium mb-1", children: "\u7528\u6237\u540D" }), _jsx("input", { type: "text", value: username, onChange: e => setUsername(e.target.value), className: "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)]", required: true })] }), _jsxs("div", { children: [_jsx("label", { className: "block text-sm font-medium mb-1", children: "\u5BC6\u7801" }), _jsx("input", { type: "password", value: password, onChange: e => setPassword(e.target.value), className: "w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)]", required: true })] }), error && _jsx("p", { className: "text-sm text-red-500", children: error }), _jsx("button", { type: "submit", disabled: loading, className: "w-full py-2.5 bg-[hsl(221.2,83.2%,53.3%)] text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition", children: loading ? '登录中...' : '登录' })] })] }) }));
}
