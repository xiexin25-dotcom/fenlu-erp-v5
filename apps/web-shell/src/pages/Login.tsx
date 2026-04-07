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
      setError(err instanceof Error ? err.message : '登录失败');
    } finally {
      setLoading(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    border: '1px solid var(--border-strong)',
    background: 'var(--bg-card)',
  };

  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--bg)' }}>
      <div className="w-full max-w-[380px] px-4">
        {/* Logo */}
        <div className="text-center mb-10">
          <div
            className="inline-flex items-center justify-center w-16 h-16 rounded mb-5"
            style={{ background: 'var(--accent)', boxShadow: '0 4px 16px rgba(0,113,227,0.3)' }}
          >
            <span className="text-white text-2xl font-bold">F</span>
          </div>
          <h1 className="text-[28px] font-semibold tracking-tight" style={{ color: 'var(--fg)' }}>分路链式</h1>
          <p className="text-[15px] mt-1" style={{ color: 'var(--fg-tertiary)' }}>工业互联网系统 V5.0</p>
        </div>

        {/* Form */}
        <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-lg)', border: '1px solid var(--border)' }}>
          <form onSubmit={handleSubmit} className="p-7 space-y-5">
            <div>
              <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--fg-secondary)' }}>租户编码</label>
              <input
                type="text" value={tenant} onChange={e => setTenant(e.target.value)}
                className="w-full px-3.5 py-2.5 text-[14px] rounded-lg outline-none"
                style={inputStyle}
                onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-light)'; }}
                onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-strong)'; e.currentTarget.style.boxShadow = 'none'; }}
                required
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--fg-secondary)' }}>用户名</label>
              <input
                type="text" value={username} onChange={e => setUsername(e.target.value)}
                className="w-full px-3.5 py-2.5 text-[14px] rounded-lg outline-none"
                style={inputStyle}
                onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-light)'; }}
                onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-strong)'; e.currentTarget.style.boxShadow = 'none'; }}
                required
              />
            </div>
            <div>
              <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--fg-secondary)' }}>密码</label>
              <input
                type="password" value={password} onChange={e => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 text-[14px] rounded-lg outline-none"
                style={inputStyle}
                onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-light)'; }}
                onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-strong)'; e.currentTarget.style.boxShadow = 'none'; }}
                required
              />
            </div>
            {error && <p className="text-[13px]" style={{ color: 'var(--status-red-fg)' }}>{error}</p>}
            <button
              type="submit" disabled={loading}
              className="w-full py-2.5 text-[15px] font-medium rounded-lg text-white disabled:opacity-50"
              style={{ background: 'var(--accent)' }}
              onMouseEnter={e => !loading && (e.currentTarget.style.background = 'var(--accent-hover)')}
              onMouseLeave={e => (e.currentTarget.style.background = 'var(--accent)')}
            >
              {loading ? '登录中...' : '登录'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
