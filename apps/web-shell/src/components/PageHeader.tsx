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
    <div className="flex items-center justify-between mb-6">
      <div className="flex items-center gap-3">
        {icon}
        <div>
          <h1 className="text-xl font-bold">{title}</h1>
          {subtitle && <p className="text-sm text-[hsl(215.4,16.3%,46.9%)]">{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-3">
        {children}
        {actionLabel && onAction && (
          <button
            onClick={onAction}
            className="flex items-center gap-1.5 px-4 py-2 bg-[hsl(221.2,83.2%,53.3%)] text-white text-sm rounded-lg hover:opacity-90 transition"
          >
            <Plus size={16} />
            {actionLabel}
          </button>
        )}
      </div>
    </div>
  );
}
