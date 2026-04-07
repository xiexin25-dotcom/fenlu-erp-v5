import type { ReactNode } from 'react';
import { Plus } from 'lucide-react';

interface Props {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  actionLabel?: string;
  onAction?: () => void;
  children?: ReactNode;
}

export default function PageHeader({ title, subtitle, icon, actionLabel, onAction, children }: Props) {
  return (
    <div className="flex items-center justify-between mb-8">
      <div className="flex items-center gap-3">
        {icon && <div style={{ color: 'var(--fg-secondary)' }}>{icon}</div>}
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight" style={{ color: 'var(--fg)' }}>{title}</h1>
          {subtitle && <p className="text-[13px] mt-0.5" style={{ color: 'var(--fg-tertiary)' }}>{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-3">
        {children}
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className="flex items-center gap-1.5 px-4 py-2 text-[13px] font-medium rounded-lg text-white"
            style={{ background: 'var(--accent)' }}
            onMouseEnter={e => (e.currentTarget.style.background = 'var(--accent-hover)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'var(--accent)')}
          >
            <Plus size={15} strokeWidth={2} />
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
}
