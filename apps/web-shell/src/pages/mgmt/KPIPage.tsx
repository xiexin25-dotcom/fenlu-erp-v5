import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { api } from '@/lib/api';
import PageHeader from '@/components/PageHeader';

interface KPIDef {
  id: string; code: string; name: string; category: string;
  unit: string; description: string;
}
interface KPIDataPoint { kpi_code: string; period: string; value: number; target: number | null; }

// Default targets for each KPI (used when API target is null)
const defaultTargets: Record<string, number> = {
  'ENG-001': 0.5, 'ENG-002': 200000, 'ENG-003': 3.5,
  'FIN-001': 3000000, 'FIN-002': 45, 'FIN-003': 2000000, 'FIN-004': 500000,
  'HR-001': 98, 'HR-002': 15000, 'HR-003': 5,
  'OPS-001': 90, 'OPS-002': 95, 'OPS-003': 600, 'OPS-004': 95,
  'QUA-001': 99, 'QUA-002': 0.5, 'QUA-003': 2,
  'SAF-001': 5, 'SAF-002': 100, 'SAF-003': 100,
};

const lowerIsBetter = new Set(['HR-003', 'QUA-002', 'QUA-003', 'SAF-001', 'ENG-001', 'ENG-003', 'FIN-002']);

function fmtValue(v: number, unit: string): string {
  if (unit.includes('元') && v >= 10000) return `${(v / 10000).toFixed(1)}万`;
  if (v >= 10000) return v.toLocaleString('zh-CN', { maximumFractionDigits: 0 });
  if (v >= 100) return v.toFixed(0);
  if (v >= 1) return v.toFixed(1);
  return v.toFixed(2);
}

function KPICard({ kpi, current, target }: { kpi: KPIDef; current: number; target: number }) {
  const isLower = lowerIsBetter.has(kpi.code);
  let pct: number;
  if (target <= 0) {
    pct = current > 0 ? 50 : 0;
  } else if (isLower) {
    pct = Math.max(0, Math.min(100, Math.round(((target - Math.max(0, current - target)) / target) * 100)));
  } else {
    pct = Math.min(100, Math.round((current / target) * 100));
  }

  const color = pct >= 90 ? 'var(--status-green-fg)' : pct >= 70 ? 'var(--status-amber-fg)' : 'var(--status-red-fg)';

  return (
    <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-sm)', padding: '20px' }}>
      <div className="flex items-center justify-between mb-3">
        <span className="text-[14px] font-medium" style={{ color: 'var(--fg)' }}>{kpi.name}</span>
        <span className="text-[11px] font-mono" style={{ color: 'var(--fg-tertiary)' }}>{kpi.code}</span>
      </div>
      <div className="flex items-end gap-2 mb-1">
        <span className="text-[24px] font-semibold" style={{ color }}>{fmtValue(current, kpi.unit)}</span>
        <span className="text-[13px] mb-1" style={{ color: 'var(--fg-tertiary)' }}>/ {fmtValue(target, kpi.unit)} {kpi.unit}</span>
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
  const { data: kpis } = useQuery({ queryKey: ['kpis'], queryFn: () => api.get<KPIDef[]>('/mgmt/bi/kpis'), retry: false });

  // Load data points for all KPIs
  const codes = useMemo(() => (kpis || []).map(k => k.code), [kpis]);
  const { data: allPoints } = useQuery({
    queryKey: ['kpi-data', codes],
    queryFn: async () => {
      const results: Record<string, KPIDataPoint> = {};
      for (const code of codes) {
        try {
          const points = await api.get<KPIDataPoint[]>(`/mgmt/bi/kpi/${code}/data`);
          if (points.length > 0) results[code] = points[0]; // latest
        } catch { /* ignore */ }
      }
      return results;
    },
    enabled: codes.length > 0,
  });

  // Group by category
  const grouped = useMemo(() => {
    const m: Record<string, KPIDef[]> = {};
    for (const k of kpis || []) {
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
      <PageHeader title="KPI 看板" subtitle="20 项指标覆盖工信部 16 场景 · 数据来自实时聚合" icon={<BarChart3 size={22} strokeWidth={1.5} />} />
      {Object.entries(grouped).map(([cat, items]) => (
        <div key={cat} className="mb-8">
          <h3 className="text-[14px] font-semibold mb-3" style={{ color: 'var(--fg-secondary)' }}>{catLabels[cat] || cat}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {items.map(k => {
              const pt = allPoints?.[k.code];
              const current = pt ? (typeof pt.value === 'string' ? parseFloat(pt.value as unknown as string) : pt.value) : 0;
              const target = pt?.target ? (typeof pt.target === 'string' ? parseFloat(pt.target as unknown as string) : pt.target) : (defaultTargets[k.code] || 100);
              return <KPICard key={k.id} kpi={k} current={current} target={target} />;
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
