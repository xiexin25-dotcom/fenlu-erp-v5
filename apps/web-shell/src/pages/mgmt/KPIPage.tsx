import { useQuery } from '@tanstack/react-query';
import { BarChart3 } from 'lucide-react';
import { kpiApi, type KPI } from '@/lib/api';
import PageHeader from '@/components/PageHeader';

function KPICard({ kpi }: { kpi: KPI }) {
  const pct = kpi.target_value > 0 ? Math.min(100, Math.round((kpi.current_value / kpi.target_value) * 100)) : 0;
  const color = pct >= 90 ? '#22c55e' : pct >= 70 ? '#f59e0b' : '#ef4444';
  return (
    <div className="bg-white rounded-xl p-5 shadow-sm border border-[hsl(214.3,31.8%,91.4%)]">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium">{kpi.name}</span>
        <span className="text-xs text-[hsl(215.4,16.3%,46.9%)]">{kpi.code}</span>
      </div>
      <div className="flex items-end gap-2 mb-3">
        <span className="text-2xl font-bold" style={{ color }}>{kpi.current_value}</span>
        <span className="text-sm text-[hsl(215.4,16.3%,46.9%)] mb-0.5">/ {kpi.target_value} {kpi.unit}</span>
      </div>
      <div className="h-2 bg-[hsl(210,40%,96.1%)] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, background: color }} />
      </div>
      <p className="text-xs text-right mt-1" style={{ color }}>{pct}% 达成</p>
    </div>
  );
}

const mockKPIs: KPI[] = [
  { code: 'OEE', name: 'OEE 综合效率', unit: '%', current_value: 87.3, target_value: 90 },
  { code: 'QC_PASS', name: '质检合格率', unit: '%', current_value: 98.2, target_value: 99 },
  { code: 'DELIVERY', name: '准时交付率', unit: '%', current_value: 94.5, target_value: 95 },
  { code: 'SAFETY', name: '安全事故率', unit: 'ppm', current_value: 0.5, target_value: 1 },
  { code: 'ENERGY', name: '能耗达标率', unit: '%', current_value: 92.1, target_value: 95 },
  { code: 'INVENTORY', name: '库存周转率', unit: '次/月', current_value: 4.2, target_value: 5 },
  { code: 'CUST_SAT', name: '客户满意度', unit: 'NPS', current_value: 72, target_value: 80 },
  { code: 'REVENUE', name: '营收目标', unit: '万元', current_value: 285, target_value: 300 },
  { code: 'COST', name: '成本控制率', unit: '%', current_value: 96, target_value: 100 },
];

export default function KPIPage() {
  const { data } = useQuery({ queryKey: ['kpis'], queryFn: kpiApi.list, retry: false });
  const kpis = data && data.length > 0 ? data : mockKPIs;

  return (
    <div className="p-6">
      <PageHeader title="KPI 看板" subtitle="20+ 指标覆盖 16 工信部场景" icon={<BarChart3 className="text-indigo-500" size={24} />} />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {kpis.map(kpi => <KPICard key={kpi.code} kpi={kpi} />)}
      </div>
    </div>
  );
}
