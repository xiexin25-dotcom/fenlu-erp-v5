import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { api } from '@/lib/api';
import PageHeader from '@/components/PageHeader';

interface KPIDef {
  id: string; code: string; name: string; category: string;
  unit: string; description: string;
}

// Simulated target/current for each KPI code (in a real system, these come from bi_kpi_data_points)
const kpiValues: Record<string, { current: number; target: number }> = {
  'ENG-001': { current: 0.42, target: 0.5 },
  'ENG-002': { current: 185000, target: 200000 },
  'ENG-003': { current: 3.2, target: 3.5 },
  'FIN-001': { current: 2850000, target: 3000000 },
  'FIN-002': { current: 32, target: 45 },
  'FIN-003': { current: 1520000, target: 2000000 },
  'FIN-004': { current: 680000, target: 500000 },
  'HR-001': { current: 96.5, target: 98 },
  'HR-002': { current: 12800, target: 15000 },
  'HR-003': { current: 2.1, target: 5 },
  'OPS-001': { current: 87.3, target: 90 },
  'OPS-002': { current: 94.2, target: 95 },
  'OPS-003': { current: 520, target: 600 },
  'OPS-004': { current: 93.8, target: 95 },
  'QUA-001': { current: 98.5, target: 99 },
  'QUA-002': { current: 0.3, target: 0.5 },
  'QUA-003': { current: 1.2, target: 2 },
  'SAF-001': { current: 2, target: 5 },
  'SAF-002': { current: 95, target: 100 },
  'SAF-003': { current: 128, target: 100 },
};

function fmt(v: number, unit: string): string {
  if (unit.includes('万元') || unit === '元') return `¥${v.toLocaleString('zh-CN', { maximumFractionDigits: 0 })}`;
  if (v >= 10000) return v.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
  if (v >= 100) return v.toFixed(0);
  if (v >= 1) return v.toFixed(1);
  return v.toFixed(2);
}

function KPICard({ kpi }: { kpi: KPIDef }) {
  const vals = kpiValues[kpi.code] || { current: 0, target: 1 };
  const { current, target } = vals;

  // For metrics where lower is better (离职率, 投诉率, 不良品率, 隐患数, 能耗)
  const lowerIsBetter = ['HR-003', 'QUA-002', 'QUA-003', 'SAF-001', 'ENG-001', 'ENG-003'].includes(kpi.code);

  let pct: number;
  if (lowerIsBetter) {
    pct = target > 0 ? Math.max(0, Math.min(100, Math.round((1 - (current - target) / target) * 100))) : 0;
  } else {
    pct = target > 0 ? Math.min(100, Math.round((current / target) * 100)) : 0;
  }

  const color = pct >= 90 ? 'var(--status-green-fg)' : pct >= 70 ? 'var(--status-amber-fg)' : 'var(--status-red-fg)';

  return (
    <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', padding: '20px' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[14px] font-medium" style={{ color: 'var(--fg)' }}>{kpi.name}</span>
        <span className="text-[11px] font-mono" style={{ color: 'var(--fg-tertiary)' }}>{kpi.code}</span>
      </div>
      <div className="flex items-end gap-2 mb-1">
        <span className="text-[24px] font-semibold" style={{ color }}>{fmt(current, kpi.unit)}</span>
        <span className="text-[13px] mb-1" style={{ color: 'var(--fg-tertiary)' }}>/ {fmt(target, kpi.unit)} {kpi.unit}</span>
      </div>
      <div className="h-[5px] rounded-full overflow-hidden mt-3" style={{ background: 'var(--divider)' }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color, transition: 'width 0.6s ease' }} />
      </div>
      <div className="flex items-center justify-between mt-1.5">
        <span className="text-[11px]" style={{ color: 'var(--fg-tertiary)' }}>{kpi.description}</span>
        <span className="text-[12px] font-medium" style={{ color }}>{pct}% 达成</span>
      </div>
    </div>
  );
}

export default function KPIPage() {
  const { data } = useQuery({ queryKey: ['kpis'], queryFn: () => api.get<KPIDef[]>('/mgmt/bi/kpis'), retry: false });

  const kpis = data || [];

  // Group by category
  const grouped = useMemo(() => {
    const m: Record<string, KPIDef[]> = {};
    for (const k of kpis) {
      const cat = k.category || 'other';
      if (!m[cat]) m[cat] = [];
      m[cat].push(k);
    }
    return m;
  }, [kpis]);

  const catLabels: Record<string, string> = {
    energy: '能耗管理', finance: '财务指标', hr: '人力资源',
    operations: '生产运营', quality: '质量管理', safety: '安全生产',
  };

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="KPI 看板" subtitle="20 项指标覆盖工信部 16 场景" icon={<BarChart3 size={22} strokeWidth={1.5} />} />
      {Object.entries(grouped).map(([cat, items]) => (
        <div key={cat} className="mb-8">
          <h3 className="text-[14px] font-semibold mb-3" style={{ color: 'var(--fg-secondary)' }}>{catLabels[cat] || cat}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map(k => <KPICard key={k.id} kpi={k} />)}
          </div>
        </div>
      ))}
    </div>
  );
}
