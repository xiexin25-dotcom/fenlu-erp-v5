import { useState, type FormEvent } from 'react';
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

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(tenant, username, password);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[hsl(210,40%,96.1%)]">
      <div className="w-full max-w-md bg-white rounded-xl shadow-lg p-8">
        <div className="text-center mb-8">
          <h1 className="text-2xl font-bold text-[hsl(222.2,84%,4.9%)]">分路链式工业互联网</h1>
          <p className="text-sm text-[hsl(215.4,16.3%,46.9%)] mt-1">V5.0 管理系统</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">租户编码</label>
            <input
              type="text" value={tenant} onChange={e => setTenant(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)]"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">用户名</label>
            <input
              type="text" value={username} onChange={e => setUsername(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)]"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">密码</label>
            <input
              type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)]"
              required
            />
          </div>
          {error && <p className="text-sm text-red-500">{error}</p>}
          <button
            type="submit" disabled={loading}
            className="w-full py-2.5 bg-[hsl(221.2,83.2%,53.3%)] text-white rounded-lg font-medium hover:opacity-90 disabled:opacity-50 transition"
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
      </div>
    </div>
  );
}
