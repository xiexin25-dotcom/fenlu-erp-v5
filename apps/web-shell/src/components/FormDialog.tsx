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
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-white rounded-xl shadow-xl w-full max-w-lg mx-4 max-h-[85vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[hsl(214.3,31.8%,91.4%)]">
          <h2 className="text-lg font-bold">{title}</h2>
          <button onClick={onClose} className="p-1 hover:bg-[hsl(210,40%,96.1%)] rounded transition"><X size={18} /></button>
        </div>
        <form onSubmit={handleSubmit}>
          <div className="px-6 py-4 space-y-4">
            {children}
            {error && <p className="text-sm text-red-500">{error}</p>}
          </div>
          <div className="flex justify-end gap-3 px-6 py-4 border-t border-[hsl(214.3,31.8%,91.4%)]">
            <button type="button" onClick={onClose} className="px-4 py-2 text-sm rounded-lg border hover:bg-[hsl(210,40%,96.1%)] transition">取消</button>
            <button type="submit" disabled={loading} className="px-4 py-2 text-sm bg-[hsl(221.2,83.2%,53.3%)] text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition">
              {loading ? '保存中...' : submitLabel}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function FormField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium mb-1">{label}</label>
      {children}
    </div>
  );
}

export function FormInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)] ${props.className || ''}`}
    />
  );
}

export function FormSelect({ children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select
      {...props}
      className={`w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-[hsl(221.2,83.2%,53.3%)] ${props.className || ''}`}
    >{children}</select>
  );
}
