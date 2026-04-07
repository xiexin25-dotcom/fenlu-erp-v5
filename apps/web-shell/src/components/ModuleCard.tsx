import { useNavigate } from 'react-router-dom';
import { ChevronRight } from 'lucide-react';

interface Props {
  title: string;
  desc: string;
  path: string;
}

export default function ModuleCard({ title, desc, path }: Props) {
  const navigate = useNavigate();
  return (
    <div
      onClick={() => navigate(path)}
      className="cursor-pointer group"
      style={{
        background: 'var(--bg-card)',
        borderRadius: 'var(--radius)',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-sm)',
        padding: '20px 22px',
        transition: 'all 0.25s cubic-bezier(0.25, 0.1, 0.25, 1)',
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = 'var(--shadow-md)';
        e.currentTarget.style.transform = 'translateY(-2px)';
        e.currentTarget.style.borderColor = 'var(--border-strong)';
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = 'var(--shadow-sm)';
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.borderColor = 'var(--border)';
      }}
    >
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[15px] font-medium" style={{ color: 'var(--fg)' }}>{title}</h3>
          <p className="text-[13px] mt-1" style={{ color: 'var(--fg-tertiary)' }}>{desc}</p>
        </div>
        <ChevronRight
          size={16} strokeWidth={1.5}
          style={{ color: 'var(--fg-tertiary)', transition: 'transform 0.2s', transform: 'translateX(0)' }}
          className="group-hover:translate-x-0.5"
        />
      </div>
    </div>
  );
}
