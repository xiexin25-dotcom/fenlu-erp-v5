import { X } from 'lucide-react';
import { type ReactNode, type FormEvent, useState } from 'react';

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  onSubmit: () => Promise<void>;
  children: ReactNode;
  submitLabel?: string;
}

export default function FormDialog({ open, onClose, title, onSubmit, children, submitLabel = '保存' }: Props) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  if (!open) return null;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await onSubmit();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : '操作失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Frosted overlay */}
      <div
        className="absolute inset-0"
        onClick={onClose}
        style={{ background: 'rgba(0,0,0,0.2)', backdropFilter: 'blur(8px)', WebkitBackdropFilter: 'blur(8px)' }}
      />
      {/* Modal */}
      <div
        className="relative w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto"
        style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius-xl)', boxShadow: 'var(--shadow-xl)' }}
      >
        <div className="flex items-center justify-between px-7 py-5" style={{ borderBottom: '1px solid var(--divider)' }}>
          <h2 className="text-[17px] font-semibold" style={{ color: 'var(--fg)' }}>{title}</h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg"
            style={{ color: 'var(--fg-tertiary)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
          ><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="px-7 py-5 space-y-5">
            {children}
            {error && <p className="text-[13px]" style={{ color: 'var(--status-red-fg)' }}>{error}</p>}
          </div>
          <div className="flex justify-end gap-3 px-7 py-4" style={{ borderTop: '1px solid var(--divider)' }}>
            <button
              type="button" onClick={onClose}
              className="px-4 py-2 text-[13px] font-medium rounded-lg"
              style={{ color: 'var(--fg-secondary)', background: 'var(--bg-hover)' }}
            >取消</button>
            <button
              type="submit" disabled={loading}
              className="px-5 py-2 text-[13px] font-medium rounded-lg text-white disabled:opacity-50"
              style={{ background: 'var(--accent)' }}
            >{loading ? '保存中...' : submitLabel}</button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="block text-[13px] font-medium mb-1.5" style={{ color: 'var(--fg-secondary)' }}>{label}</label>
      {children}
    </div>
  );
}

export function FormInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full px-3.5 py-2.5 text-[14px] rounded-lg outline-none ${props.className || ''}`}
      style={{ border: '1px solid var(--border-strong)', background: 'var(--bg-card)', ...({} as React.CSSProperties) }}
      onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)'; e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-light)'; }}
      onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-strong)'; e.currentTarget.style.boxShadow = 'none'; }}
    />
  );
}

export function FormSelect({ children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full px-3.5 py-2.5 text-[14px] rounded-lg outline-none ${props.className || ''}`}
      style={{ border: '1px solid var(--border-strong)', background: 'var(--bg-card)' }}
    >{children}</select>
  );
}
