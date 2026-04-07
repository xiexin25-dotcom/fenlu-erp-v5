import { useQuery } from '@tanstack/react-query';
import { TrendingUp } from 'lucide-react';
import { api } from '@/lib/api';
import PageHeader from '@/components/PageHeader';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const stageOrder = ['new', 'contacted', 'qualified', 'converted', 'qualification', 'proposal', 'negotiation', 'closed_won', 'closed_lost'];
const stageLabels: Record<string, string> = {
  new: '新线索', contacted: '已联系', qualified: '已验证', converted: '已转化',
  qualification: '需求确认', proposal: '方案报价', negotiation: '商务谈判',
  closed_won: '已成交', closed_lost: '已流失', disqualified: '已淘汰',
};
const COLORS = ['#94a3b8', '#60a5fa', '#38bdf8', '#818cf8', '#a78bfa', '#6366f1', '#8b5cf6', '#22c55e', '#ef4444'];

interface FunnelRaw {
  leads?: Record<string, number>;
  opportunities?: Record<string, number>;
}

function parseFunnel(raw: FunnelRaw): { label: string; count: number }[] {
  const merged: Record<string, number> = {};
  if (raw.leads) {
    for (const [k, v] of Object.entries(raw.leads)) merged[k] = (merged[k] || 0) + v;
  }
  if (raw.opportunities) {
    for (const [k, v] of Object.entries(raw.opportunities)) merged[k] = (merged[k] || 0) + v;
  }
  // Sort by stage order
  return Object.entries(merged)
    .sort((a, b) => {
      const ia = stageOrder.indexOf(a[0]);
      const ib = stageOrder.indexOf(b[0]);
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
    })
    .map(([stage, count]) => ({ label: stageLabels[stage] || stage, count }));
}

export default function CRMFunnel() {
  const { data } = useQuery({
    queryKey: ['crm-funnel'],
    queryFn: () => api.get<FunnelRaw>('/plm/crm/funnel'),
    retry: false,
  });

  const chartData = data ? parseFunnel(data) : [];

  return (
    <div className="p-8 max-w-[1200px] mx-auto">
      <PageHeader title="商机漏斗" subtitle="CRM Funnel" icon={<TrendingUp size={22} strokeWidth={1.5} />} />
      <div style={{ background: 'var(--bg-card)', borderRadius: 'var(--radius)', boxShadow: 'var(--shadow-sm)', border: '1px solid var(--border)' }} className="p-6">
        {chartData.length > 0 ? (
          <>
            {/* Summary cards */}
            <div className="flex gap-4 mb-6">
              {chartData.map((d, i) => (
                <div key={d.label} className="flex-1 text-center py-3" style={{ background: 'var(--bg-hover)', borderRadius: 'var(--radius-sm)' }}>
                  <div className="text-[20px] font-semibold" style={{ color: COLORS[i % COLORS.length] }}>{d.count}</div>
                  <div className="text-[12px]" style={{ color: 'var(--fg-tertiary)' }}>{d.label}</div>
                </div>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData} margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--divider)" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 12, fill: 'var(--fg-secondary)' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 12, fill: 'var(--fg-tertiary)' }} axisLine={false} tickLine={false} />
                <Tooltip formatter={(v) => [`${v} 条`, '数量']} contentStyle={{ borderRadius: 6, border: '1px solid var(--border)', fontSize: 12 }} />
                <Bar dataKey="count" radius={[4, 4, 0, 0]} barSize={40}>
                  {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </>
        ) : (
          <div className="text-center py-16" style={{ color: 'var(--fg-tertiary)' }}>
            <p className="text-[16px] mb-2">暂无商机数据</p>
            <p className="text-[13px]">通过 API 创建 Lead/Opportunity 后，漏斗图将自动更新</p>
          </div>
        )}
      </div>
    </div>
  );
}
